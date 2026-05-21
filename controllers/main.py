import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class DashboardController(http.Controller):

    @http.route('/sohome/dashboard', auth='user', methods=['GET'], csrf=False)
    def dashboard_index(self, board_id=None, **kwargs):
        """Renderiza a página principal do dashboard."""
        boards = request.env['dashboard.board'].search([])
        active_board = None
        if board_id:
            try:
                active_board = int(board_id)
            except (ValueError, TypeError):
                active_board = None
        if not active_board and boards:
            active_board = boards[0].id

        return request.render('dashboard_sohome.dashboard_page', {
            'boards': boards,
            'active_board_id': active_board,
            'user_name': request.env.user.name,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/sohome/api/boards', auth='user', type='json', methods=['POST'])
    def api_get_boards(self, **kwargs):
        """Retorna todos os dashboards com seus widgets."""
        boards = request.env['dashboard.board'].search([])
        result = []
        for board in boards:
            widgets = []
            for w in board.widget_ids.sorted('sequence'):
                widgets.append({
                    'id': w.id,
                    'name': w.name,
                    'description': w.description or '',
                    'icon': w.icon or '📈',
                    'chart_type': w.chart_type,
                    'color_scheme': w.color_scheme,
                    'size': w.size,
                    'prefix': w.prefix or '',
                    'suffix': w.suffix or '',
                    'refresh_interval': w.refresh_interval,
                })
            result.append({
                'id': board.id,
                'name': board.name,
                'description': board.description or '',
                'icon': board.icon or '📊',
                'widget_count': board.widget_count,
                'widgets': widgets,
            })
        return {'boards': result}

    @http.route('/sohome/api/widget/<int:widget_id>/data', auth='user', type='json', methods=['POST'])
    def api_widget_data(self, widget_id, **kwargs):
        """Executa a query do widget e retorna os dados."""
        widget = request.env['dashboard.widget'].browse(widget_id)
        if not widget.exists():
            return {'error': 'Widget não encontrado', 'data': None}
        try:
            data = widget.execute_query()
            return {
                'success': True,
                'columns': data['columns'],
                'rows': data['rows'],
                'row_count': data['row_count'],
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @http.route('/sohome/api/board/create', auth='user', type='json', methods=['POST'])
    def api_create_board(self, name, description='', icon='📊', **kwargs):
        """Cria um novo dashboard."""
        board = request.env['dashboard.board'].create({
            'name': name,
            'description': description,
            'icon': icon,
        })
        return {'success': True, 'id': board.id, 'name': board.name}

    @http.route('/sohome/api/board/<int:board_id>/delete', auth='user', type='json', methods=['POST'])
    def api_delete_board(self, board_id, **kwargs):
        """Remove um dashboard."""
        board = request.env['dashboard.board'].browse(board_id)
        if not board.exists():
            return {'success': False, 'error': 'Dashboard não encontrado'}
        board.unlink()
        return {'success': True}

    @http.route('/sohome/api/widget/create', auth='user', type='json', methods=['POST'])
    def api_create_widget(self, board_id, name, sql_query, chart_type='number',
                          color_scheme='violet', size='2', description='',
                          icon='📈', prefix='', suffix='', refresh_interval=0, **kwargs):
        """Cria um novo widget."""
        try:
            widget = request.env['dashboard.widget'].create({
                'board_id': board_id,
                'name': name,
                'description': description,
                'icon': icon,
                'sql_query': sql_query,
                'chart_type': chart_type,
                'color_scheme': color_scheme,
                'size': size,
                'prefix': prefix,
                'suffix': suffix,
                'refresh_interval': refresh_interval,
            })
            return {
                'success': True,
                'id': widget.id,
                'name': widget.name,
                'chart_type': widget.chart_type,
                'color_scheme': widget.color_scheme,
                'size': widget.size,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/sohome/api/widget/<int:widget_id>/update', auth='user', type='json', methods=['POST'])
    def api_update_widget(self, widget_id, **kwargs):
        """Atualiza um widget existente."""
        widget = request.env['dashboard.widget'].browse(widget_id)
        if not widget.exists():
            return {'success': False, 'error': 'Widget não encontrado'}
        allowed_fields = [
            'name', 'description', 'icon', 'sql_query', 'chart_type',
            'color_scheme', 'size', 'prefix', 'suffix', 'refresh_interval', 'sequence'
        ]
        vals = {k: v for k, v in kwargs.items() if k in allowed_fields}
        try:
            widget.write(vals)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/sohome/api/widget/<int:widget_id>/delete', auth='user', type='json', methods=['POST'])
    def api_delete_widget(self, widget_id, **kwargs):
        """Remove um widget."""
        widget = request.env['dashboard.widget'].browse(widget_id)
        if not widget.exists():
            return {'success': False, 'error': 'Widget não encontrado'}
        widget.unlink()
        return {'success': True}
