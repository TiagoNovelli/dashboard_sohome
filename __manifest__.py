{
    'name': 'SoHome Dashboards',
    'version': '18.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Dashboards personalizados com SQL',
    'description': """
        Crie dashboards bonitos e interativos usando queries SQL.
        Suporta gráficos de barras, linhas, pizza, donut, KPIs e tabelas.
        Interface minimalista e moderna sem dependências do framework Odoo.
    """,
    'author': 'SoHome',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        # Widgets primeiro (board_views referencia o modelo widget via type="object")
        'views/dashboard_widget_views.xml',
        'views/dashboard_board_views.xml',
        # Menus por último (dependem das actions acima)
        'views/menus.xml',
        'templates/index.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
}
