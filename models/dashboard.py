import re
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DashboardBoard(models.Model):
    _name = 'dashboard.board'
    _description = 'Dashboard'
    _order = 'sequence, name'

    name = fields.Char(string='Nome', required=True)
    description = fields.Char(string='Descrição')
    sequence = fields.Integer(string='Sequência', default=10)
    active = fields.Boolean(string='Ativo', default=True)
    icon = fields.Char(string='Ícone', default='📊', help='Emoji para representar o dashboard')
    widget_ids = fields.One2many('dashboard.widget', 'board_id', string='Widgets')
    widget_count = fields.Integer(compute='_compute_widget_count', string='Nº de Widgets')

    @api.depends('widget_ids')
    def _compute_widget_count(self):
        for rec in self:
            rec.widget_count = len(rec.widget_ids)

    def action_view_dashboard(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sohome/dashboard?board_id={self.id}',
            'target': 'self',
        }


class DashboardWidget(models.Model):
    _name = 'dashboard.widget'
    _description = 'Widget de Dashboard'
    _order = 'sequence, name'

    name = fields.Char(string='Título', required=True)
    board_id = fields.Many2one(
        'dashboard.board', string='Dashboard',
        required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequência', default=10)
    description = fields.Char(string='Subtítulo / Descrição')
    icon = fields.Char(string='Ícone', default='📈', help='Emoji para o widget')

    sql_query = fields.Text(
        string='Query SQL',
        required=True,
        help='Apenas SELECT é permitido. Para gráficos: primeira coluna = label, segunda coluna = valor. '
             'Para KPI: retorne uma linha com um valor.'
    )

    chart_type = fields.Selection([
        ('number', '🔢 KPI / Número'),
        ('bar', '📊 Barras'),
        ('bar_horizontal', '📉 Barras Horizontais'),
        ('line', '📈 Linhas'),
        ('area', '🏔️ Área'),
        ('pie', '🥧 Pizza'),
        ('donut', '🍩 Donut'),
        ('table', '📋 Tabela'),
    ], string='Tipo de Gráfico', required=True, default='number')

    color_scheme = fields.Selection([
        ('violet', 'Violeta'),
        ('blue', 'Azul'),
        ('cyan', 'Ciano'),
        ('green', 'Verde'),
        ('amber', 'Âmbar'),
        ('rose', 'Rosa'),
        ('slate', 'Cinza'),
    ], string='Cor', default='violet')

    size = fields.Selection([
        ('1', '1/4 da Largura'),
        ('2', '1/2 da Largura'),
        ('3', '3/4 da Largura'),
        ('4', 'Largura Total'),
    ], string='Tamanho', default='2')

    prefix = fields.Char(
        string='Prefixo',
        help='Texto antes do valor (ex: R$, €, $)'
    )
    suffix = fields.Char(
        string='Sufixo',
        help='Texto após o valor (ex: %, un, kg)'
    )
    refresh_interval = fields.Integer(
        string='Auto-Refresh (segundos)',
        default=0,
        help='0 = desativado. Mínimo 30 segundos se ativado.'
    )

    def _validate_sql(self, query):
        """Valida que a query é segura para executar."""
        if not query:
            raise UserError("A query SQL não pode estar vazia.")

        cleaned = query.strip()
        # Remove comentários de linha
        cleaned_no_comments = re.sub(r'--[^\n]*', '', cleaned)
        # Remove comentários de bloco
        cleaned_no_comments = re.sub(r'/\*.*?\*/', '', cleaned_no_comments, flags=re.DOTALL)
        cleaned_upper = cleaned_no_comments.strip().upper()

        if not cleaned_upper.startswith('SELECT'):
            raise UserError("Apenas queries SELECT são permitidas.")

        # Bloqueia keywords perigosas
        dangerous_keywords = [
            r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
            r'\bTRUNCATE\b', r'\bCREATE\b', r'\bALTER\b', r'\bGRANT\b',
            r'\bREVOKE\b', r'\bEXECUTE\b', r'\bEXEC\b', r'\bSELECT\s+INTO\b',
            r'\bCOPY\b', r'\bCAST\s*\(.*?AS\s+TEXT\s*\)',
        ]
        for pattern in dangerous_keywords:
            if re.search(pattern, cleaned_upper):
                keyword = pattern.replace(r'\b', '').replace('\\s+INTO', ' INTO')
                raise UserError(f"Operação não permitida detectada na query: {keyword}")

        return True

    def execute_query(self):
        """Executa a query e retorna os dados."""
        self._validate_sql(self.sql_query)
        try:
            self.env.cr.execute(self.sql_query)  # noqa: S608
            columns = [desc[0] for desc in self.env.cr.description] if self.env.cr.description else []
            rows = self.env.cr.fetchmany(5000)  # limite de 5000 linhas
            return {
                'columns': columns,
                'rows': [list(row) for row in rows],
                'row_count': len(rows),
            }
        except Exception as e:
            _logger.error("Erro ao executar query do widget %s: %s", self.name, str(e))
            raise UserError(f"Erro ao executar a query: {str(e)}")

    @api.constrains('sql_query')
    def _check_sql_query(self):
        for rec in self:
            if rec.sql_query:
                rec._validate_sql(rec.sql_query)

    def action_test_query(self):
        """Ação para testar a query no backend."""
        result = self.execute_query()
        message = (
            f"✅ Query executada com sucesso!\n"
            f"Colunas: {', '.join(result['columns'])}\n"
            f"Linhas retornadas: {result['row_count']}"
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Teste de Query',
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }
