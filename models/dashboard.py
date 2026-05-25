import re
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_DANGEROUS_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
    r'\bTRUNCATE\b', r'\bCREATE\b', r'\bALTER\b', r'\bGRANT\b',
    r'\bREVOKE\b', r'\bEXECUTE\b', r'\bEXEC\b', r'\bSELECT\s+INTO\b',
    r'\bCOPY\b', r'\bCAST\s*\(.*?AS\s+TEXT\s*\)',
]


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
    filter_ids = fields.One2many('dashboard.filter', 'board_id', string='Filtros')

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

    def action_open_widgets(self):
        """Abre a lista de widgets filtrada por este dashboard."""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Widgets — {self.name}',
            'res_model': 'dashboard.widget',
            'view_mode': 'list,form',
            'domain': [('board_id', '=', self.id)],
            'context': {'default_board_id': self.id},
        }


class DashboardFilter(models.Model):
    """Filtro reutilizável de um dashboard. Substitui {{param_key}} nas queries SQL."""
    _name = 'dashboard.filter'
    _description = 'Filtro de Dashboard'
    _order = 'sequence, name'

    board_id = fields.Many2one(
        'dashboard.board', string='Dashboard',
        required=True, ondelete='cascade',
    )
    name = fields.Char(
        string='Nome', required=True,
        help='Nome visível na barra de filtros. Ex: Data Inicial',
    )
    param_key = fields.Char(
        string='Chave', required=True,
        help=(
            'Identificador usado na query SQL entre chaves duplas: {{date_from}}.\n'
            'Use apenas letras, números e underscore. Sem espaços.'
        ),
    )
    filter_type = fields.Selection([
        ('date', '📅 Data'),
        ('char', '🔤 Texto'),
        ('integer', '🔢 Inteiro'),
    ], string='Tipo', default='date', required=True)
    default_value = fields.Char(
        string='Valor Padrão',
        help='Valor aplicado quando o usuário não preenche o filtro. Para datas use YYYY-MM-DD.',
    )
    sequence = fields.Integer(default=10)

    @api.constrains('param_key')
    def _check_param_key(self):
        for rec in self:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', rec.param_key):
                raise UserError(
                    f"Chave «{rec.param_key}» inválida. "
                    "Use apenas letras, números e underscore (sem espaços)."
                )


class DashboardWidget(models.Model):
    _name = 'dashboard.widget'
    _description = 'Widget de Dashboard'
    _order = 'sequence, name'

    name = fields.Char(string='Título', required=True)
    board_id = fields.Many2one(
        'dashboard.board', string='Dashboard',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequência', default=10)
    description = fields.Char(string='Subtítulo / Descrição')
    icon = fields.Char(string='Ícone', default='📈', help='Emoji para o widget')

    sql_query = fields.Text(
        string='Query SQL',
        required=True,
        help=(
            'Apenas SELECT é permitido.\n'
            'Para gráficos: col 1 = label, col 2 = valor.\n'
            'Para KPI: retorne 1 linha com 1 valor.\n'
            '\n'
            'Variáveis built-in:\n'
            '  {{uid}}       → ID do usuário logado (restringe dados ao próprio usuário)\n'
            '  {{user_name}} → Nome do usuário logado\n'
            '\n'
            'Filtros do dashboard: use {{chave}} conforme definido na aba Filtros do dashboard.'
        ),
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

    prefix = fields.Char(string='Prefixo', help='Texto antes do valor (ex: R$, €, $)')
    suffix = fields.Char(string='Sufixo', help='Texto após o valor (ex: %, un, kg)')
    refresh_interval = fields.Integer(
        string='Auto-Refresh (segundos)',
        default=0,
        help='0 = desativado. Mínimo 30 segundos se ativado.',
    )

    # ─── Link ao modelo Odoo (só para KPI / number) ───────────────────────────
    odoo_model = fields.Char(
        string='Modelo Odoo',
        help=(
            'Nome técnico do modelo Odoo para abrir ao clicar no KPI.\n'
            'Ex: sale.order, product.template, account.move\n'
            'Deixe vazio para não exibir o link.'
        ),
    )
    odoo_domain = fields.Char(
        string='Domain (filtro)',
        default='[]',
        help=(
            'Domain Odoo serializado que será aplicado na list view.\n'
            'Ex: [["state","in",["draft","sent"]]]\n'
            'Deixe [] para abrir sem filtro.'
        ),
    )

    # ─── SQL helpers ──────────────────────────────────────────────────────────
    def _validate_sql(self, query):
        """Valida que a query é segura. Aceita templates com {{key}} e %(key)s."""
        if not query:
            raise UserError("A query SQL não pode estar vazia.")

        # Strip template variables before validation
        cleaned = re.sub(r'\{\{\w+\}\}', 'NULL', query)
        cleaned = re.sub(r'%\(\w+\)s', 'NULL', cleaned)

        # Remove comentários
        cleaned = re.sub(r'--[^\n]*', '', cleaned)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned_upper = cleaned.strip().upper()

        if not cleaned_upper.startswith('SELECT'):
            raise UserError("Apenas queries SELECT são permitidas.")

        for pattern in _DANGEROUS_KEYWORDS:
            if re.search(pattern, cleaned_upper):
                readable = re.sub(r'\\[bs]|\\s\+', ' ', pattern).replace(r'\b', '').strip()
                raise UserError(f"Operação não permitida detectada: {readable}")

        return True

    def _apply_filters(self, query, filter_params):
        """
        Substitui variáveis {{key}} na query.

        Built-ins ({{uid}}, {{user_name}}) são valores controlados pelo servidor.
        Filtros do usuário usam parameterized queries (psycopg2) para evitar injection.

        Retorna (sql, params_dict_or_None).
        """
        result = query
        params = {}

        # Built-in: uid é sempre inteiro — substituição direta é segura
        result = result.replace('{{uid}}', str(self.env.uid))

        # Built-in: user_name via parameterized para segurança
        if '{{user_name}}' in result:
            result = result.replace('{{user_name}}', '%(builtin_user_name)s')
            params['builtin_user_name'] = self.env.user.name

        # Filtros do dashboard (valores vindos do usuário → sempre parameterized)
        if filter_params:
            for key, value in filter_params.items():
                if re.match(r'^[a-zA-Z_]\w*$', key):
                    placeholder = '{{' + key + '}}'
                    if placeholder in result:
                        pg_key = f'fp_{key}'  # prefixo para evitar conflito com built-ins
                        result = result.replace(placeholder, f'%({pg_key})s')
                        params[pg_key] = value or None

        # Variáveis restantes não fornecidas → NULL (com aviso)
        for key in re.findall(r'\{\{(\w+)\}\}', result):
            _logger.warning(
                "Widget '%s': parâmetro {{%s}} não fornecido → substituído por NULL.",
                self.name, key,
            )
            result = result.replace('{{' + key + '}}', 'NULL')

        return result, (params if params else None)

    def execute_query(self, filter_params=None):
        """Executa a query e retorna os dados."""
        sql, params = self._apply_filters(self.sql_query, filter_params or {})
        self._validate_sql(sql)
        try:
            self.env.cr.execute(sql, params)  # noqa: S608
            columns = [desc[0] for desc in self.env.cr.description] if self.env.cr.description else []
            rows = self.env.cr.fetchmany(5000)
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
