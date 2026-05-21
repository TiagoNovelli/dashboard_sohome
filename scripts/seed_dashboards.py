# ══════════════════════════════════════════════════════════════════════════════
#  SoHome — Seed: Pipeline de Cotações + Qualidade de Cadastro
#  Execute via:  docker exec -i odoo18-staging odoo shell -d sohome_staging
# ══════════════════════════════════════════════════════════════════════════════

# ─── Limpa dashboards com o mesmo nome (idempotente) ─────────────────────────
for nome in ('Pipeline de Cotações', 'Qualidade de Cadastro'):
    antigo = env['dashboard.board'].search([('name', '=', nome)])
    if antigo:
        antigo.unlink()
        print(f'  ↻ Dashboard "{nome}" anterior removido.')

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD 1 — Pipeline de Cotações
# ══════════════════════════════════════════════════════════════════════════════
b1 = env['dashboard.board'].create({
    'name': 'Pipeline de Cotações',
    'description': 'Funil de vendas e acompanhamento de cotações',
    'icon': '📋',
    'sequence': 1,
})

widgets_pipeline = [
    # ── Row 1: 4 KPIs ──────────────────────────────────────────────────────
    {
        'name': 'Cotações Abertas',
        'description': 'Rascunhos + Enviadas',
        'icon': '📋',
        'chart_type': 'number',
        'color_scheme': 'violet',
        'size': '1',
        'sequence': 10,
        'sql_query': """
SELECT COUNT(*)
FROM sale_order
WHERE state IN ('draft','sent')
""",
    },
    {
        'name': 'Valor do Pipeline',
        'description': 'Total em aberto (R$)',
        'icon': '💰',
        'chart_type': 'number',
        'color_scheme': 'green',
        'size': '1',
        'prefix': 'R$ ',
        'sequence': 20,
        'sql_query': """
SELECT ROUND(COALESCE(SUM(amount_total), 0)::numeric, 2)
FROM sale_order
WHERE state IN ('draft','sent')
""",
    },
    {
        'name': 'Ticket Médio',
        'description': 'Valor médio das cotações abertas',
        'icon': '🎯',
        'chart_type': 'number',
        'color_scheme': 'blue',
        'size': '1',
        'prefix': 'R$ ',
        'sequence': 30,
        'sql_query': """
SELECT ROUND(COALESCE(AVG(amount_total), 0)::numeric, 2)
FROM sale_order
WHERE state IN ('draft','sent')
""",
    },
    {
        'name': 'Conversão (30 dias)',
        'description': '% cotações viradas em pedido',
        'icon': '📈',
        'chart_type': 'number',
        'color_scheme': 'cyan',
        'size': '1',
        'suffix': '%',
        'sequence': 40,
        'sql_query': """
SELECT ROUND(
    COUNT(*) FILTER (WHERE state = 'sale') * 100.0
    / NULLIF(COUNT(*), 0),
1)
FROM sale_order
WHERE state != 'cancel'
  AND create_date >= NOW() - INTERVAL '30 days'
""",
    },
    # ── Row 2: Donut de status + Área de cotações/mês ─────────────────────
    {
        'name': 'Cotações por Status',
        'description': 'Distribuição atual do funil',
        'icon': '🍩',
        'chart_type': 'donut',
        'color_scheme': 'violet',
        'size': '2',
        'sequence': 50,
        'sql_query': """
SELECT
    CASE state
        WHEN 'draft'  THEN 'Rascunho'
        WHEN 'sent'   THEN 'Enviada'
        WHEN 'sale'   THEN 'Confirmada'
        WHEN 'cancel' THEN 'Cancelada'
        ELSE state
    END AS status,
    COUNT(*) AS total
FROM sale_order
GROUP BY state
ORDER BY total DESC
""",
    },
    {
        'name': 'Cotações por Mês',
        'description': 'Últimos 12 meses',
        'icon': '📈',
        'chart_type': 'area',
        'color_scheme': 'blue',
        'size': '2',
        'sequence': 60,
        'sql_query': """
SELECT
    TO_CHAR(date_order, 'MM/YY') AS mes,
    COUNT(*) AS cotacoes
FROM sale_order
WHERE state IN ('draft','sent','sale')
  AND date_order >= NOW() - INTERVAL '12 months'
GROUP BY TO_CHAR(date_order, 'MM/YY'),
         DATE_TRUNC('month', date_order)
ORDER BY DATE_TRUNC('month', date_order)
""",
    },
    # ── Row 3: Valor/mês + Top clientes ───────────────────────────────────
    {
        'name': 'Valor por Mês (R$)',
        'description': 'Últimos 12 meses',
        'icon': '💵',
        'chart_type': 'bar',
        'color_scheme': 'green',
        'size': '2',
        'sequence': 70,
        'sql_query': """
SELECT
    TO_CHAR(date_order, 'MM/YY') AS mes,
    ROUND(SUM(amount_total)::numeric, 0) AS valor
FROM sale_order
WHERE state IN ('draft','sent','sale')
  AND date_order >= NOW() - INTERVAL '12 months'
GROUP BY TO_CHAR(date_order, 'MM/YY'),
         DATE_TRUNC('month', date_order)
ORDER BY DATE_TRUNC('month', date_order)
""",
    },
    {
        'name': 'Top 10 Clientes',
        'description': 'Por número de cotações',
        'icon': '👥',
        'chart_type': 'bar_horizontal',
        'color_scheme': 'amber',
        'size': '2',
        'sequence': 80,
        'sql_query': """
SELECT
    rp.name AS cliente,
    COUNT(*) AS cotacoes
FROM sale_order so
JOIN res_partner rp ON rp.id = so.partner_id
WHERE so.state IN ('draft','sent','sale')
GROUP BY rp.name
ORDER BY cotacoes DESC
LIMIT 10
""",
    },
    # ── Row 4: Vendedores + Tempo médio ───────────────────────────────────
    {
        'name': 'Cotações por Vendedor',
        'description': 'Abertas por representante',
        'icon': '🧑‍💼',
        'chart_type': 'bar',
        'color_scheme': 'rose',
        'size': '2',
        'sequence': 90,
        'sql_query': """
SELECT
    rp.name AS vendedor,
    COUNT(*) AS cotacoes
FROM sale_order so
JOIN res_users ru    ON ru.id = so.user_id
JOIN res_partner rp ON rp.id = ru.partner_id
WHERE so.state IN ('draft','sent')
GROUP BY rp.name
ORDER BY cotacoes DESC
LIMIT 15
""",
    },
    {
        'name': 'Dias Médios em Aberto',
        'description': 'Por vendedor (cotações abertas)',
        'icon': '⏱️',
        'chart_type': 'bar_horizontal',
        'color_scheme': 'slate',
        'size': '2',
        'sequence': 100,
        'sql_query': """
SELECT
    rp.name AS vendedor,
    ROUND(AVG(NOW()::date - so.date_order::date)) AS dias_aberto
FROM sale_order so
JOIN res_users ru    ON ru.id = so.user_id
JOIN res_partner rp ON rp.id = ru.partner_id
WHERE so.state IN ('draft','sent')
GROUP BY rp.name
ORDER BY dias_aberto DESC
LIMIT 15
""",
    },
    # ── Row 5: Tabela completa ─────────────────────────────────────────────
    {
        'name': 'Cotações Abertas — Detalhamento',
        'description': 'Lista completa ordenada por valor',
        'icon': '📄',
        'chart_type': 'table',
        'color_scheme': 'slate',
        'size': '4',
        'sequence': 110,
        'sql_query': """
SELECT
    so.name                                             AS "Número",
    rp.name                                             AS "Cliente",
    TO_CHAR(so.date_order, 'DD/MM/YYYY')                AS "Data",
    CASE so.state
        WHEN 'draft' THEN 'Rascunho'
        WHEN 'sent'  THEN 'Enviada'
        WHEN 'sale'  THEN 'Confirmada'
        ELSE so.state
    END                                                 AS "Status",
    ru_p.name                                           AS "Vendedor",
    (NOW()::date - so.date_order::date) || ' dias'      AS "Em Aberto",
    'R$ ' || TO_CHAR(so.amount_total, 'FM999G999G990D00') AS "Valor"
FROM sale_order so
JOIN res_partner rp  ON rp.id = so.partner_id
JOIN res_users ru    ON ru.id = so.user_id
JOIN res_partner ru_p ON ru_p.id = ru.partner_id
WHERE so.state IN ('draft','sent')
ORDER BY so.amount_total DESC
LIMIT 100
""",
    },
]

for w in widgets_pipeline:
    w['board_id'] = b1.id
    env['dashboard.widget'].create(w)

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD 2 — Qualidade de Cadastro
# ══════════════════════════════════════════════════════════════════════════════
b2 = env['dashboard.board'].create({
    'name': 'Qualidade de Cadastro',
    'description': 'Produtos com foto e descrição de cotação',
    'icon': '📦',
    'sequence': 2,
})

# Macro auxiliar para o check de foto (usa ir_attachment no Odoo 18)
_SEM_FOTO = """NOT EXISTS (
    SELECT 1 FROM ir_attachment ia
    WHERE ia.res_model = 'product.template'
      AND ia.res_field = 'image_1920'
      AND ia.res_id = pt.id
)"""

_COM_FOTO = """EXISTS (
    SELECT 1 FROM ir_attachment ia
    WHERE ia.res_model = 'product.template'
      AND ia.res_field = 'image_1920'
      AND ia.res_id = pt.id
)"""

_SEM_DESC = "(pt.description_sale IS NULL OR TRIM(pt.description_sale::text) = '')"
_COM_DESC = "(pt.description_sale IS NOT NULL AND TRIM(pt.description_sale::text) != '')"

widgets_cadastro = [
    # ── Row 1: 4 KPIs ──────────────────────────────────────────────────────
    {
        'name': 'Produtos sem Foto',
        'description': 'Produtos ativos sem imagem',
        'icon': '🖼️',
        'chart_type': 'number',
        'color_scheme': 'rose',
        'size': '1',
        'sequence': 10,
        'sql_query': f"""
SELECT COUNT(*)
FROM product_template pt
WHERE pt.active = true
  AND {_SEM_FOTO}
""",
    },
    {
        'name': 'Sem Descrição de Cotação',
        'description': 'Produtos sem description_sale',
        'icon': '📝',
        'chart_type': 'number',
        'color_scheme': 'amber',
        'size': '1',
        'sequence': 20,
        'sql_query': f"""
SELECT COUNT(*)
FROM product_template pt
WHERE pt.active = true
  AND {_SEM_DESC}
""",
    },
    {
        'name': 'Total de Produtos Ativos',
        'description': 'Base completa de produtos',
        'icon': '📦',
        'chart_type': 'number',
        'color_scheme': 'slate',
        'size': '1',
        'sequence': 30,
        'sql_query': """
SELECT COUNT(*)
FROM product_template
WHERE active = true
""",
    },
    {
        'name': 'Cadastro Completo',
        'description': '% com foto e descrição',
        'icon': '✅',
        'chart_type': 'number',
        'color_scheme': 'green',
        'size': '1',
        'suffix': '%',
        'sequence': 40,
        'sql_query': f"""
SELECT ROUND(
    COUNT(*) FILTER (WHERE {_COM_FOTO} AND {_COM_DESC})
    * 100.0 / NULLIF(COUNT(*), 0),
1)
FROM product_template pt
WHERE pt.active = true
""",
    },
    # ── Row 2: Donut de status + Sem foto por categoria ───────────────────
    {
        'name': 'Status do Cadastro',
        'description': 'Distribuição por completude',
        'icon': '🍩',
        'chart_type': 'donut',
        'color_scheme': 'violet',
        'size': '2',
        'sequence': 50,
        'sql_query': f"""
SELECT status, COUNT(*) AS total FROM (
    SELECT CASE
        WHEN {_COM_FOTO} AND {_COM_DESC}
            THEN 'Completo'
        WHEN {_SEM_FOTO} AND {_SEM_DESC}
            THEN 'Falta Foto e Descrição'
        WHEN {_SEM_FOTO}
            THEN 'Falta Foto'
        ELSE 'Falta Descrição'
    END AS status
    FROM product_template pt
    WHERE pt.active = true
) t
GROUP BY status
ORDER BY total DESC
""",
    },
    {
        'name': 'Sem Foto por Categoria',
        'description': 'Top categorias com produtos sem imagem',
        'icon': '📊',
        'chart_type': 'bar_horizontal',
        'color_scheme': 'rose',
        'size': '2',
        'sequence': 60,
        'sql_query': f"""
SELECT
    COALESCE(pc.complete_name, 'Sem Categoria') AS categoria,
    COUNT(*) AS sem_foto
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND {_SEM_FOTO}
GROUP BY pc.complete_name
ORDER BY sem_foto DESC
LIMIT 15
""",
    },
    # ── Row 3: Sem descrição por categoria + evolução por mês ─────────────
    {
        'name': 'Sem Descrição por Categoria',
        'description': 'Top categorias sem description_sale',
        'icon': '📊',
        'chart_type': 'bar_horizontal',
        'color_scheme': 'amber',
        'size': '2',
        'sequence': 70,
        'sql_query': f"""
SELECT
    COALESCE(pc.complete_name, 'Sem Categoria') AS categoria,
    COUNT(*) AS sem_descricao
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND {_SEM_DESC}
GROUP BY pc.complete_name
ORDER BY sem_descricao DESC
LIMIT 15
""",
    },
    {
        'name': 'Evolução de Cadastros (6 meses)',
        'description': 'Novos produtos criados por mês',
        'icon': '📈',
        'chart_type': 'area',
        'color_scheme': 'green',
        'size': '2',
        'sequence': 80,
        'sql_query': """
SELECT
    TO_CHAR(write_date, 'MM/YY') AS mes,
    COUNT(*) AS novos_produtos
FROM product_template
WHERE active = true
  AND write_date >= NOW() - INTERVAL '6 months'
GROUP BY TO_CHAR(write_date, 'MM/YY'),
         DATE_TRUNC('month', write_date)
ORDER BY DATE_TRUNC('month', write_date)
""",
    },
    # ── Row 4: Tabelas de lista ────────────────────────────────────────────
    {
        'name': 'Lista — Produtos sem Foto',
        'description': 'Produtos que precisam de imagem',
        'icon': '🖼️',
        'chart_type': 'table',
        'color_scheme': 'rose',
        'size': '2',
        'sequence': 90,
        'sql_query': f"""
SELECT
    COALESCE(pt.default_code, '—') AS "Ref.",
    pt.name::text                  AS "Produto",
    COALESCE(pc.complete_name, '—') AS "Categoria",
    CASE WHEN {_COM_DESC} THEN 'Sim ✅' ELSE 'Não ❌' END AS "Tem Descrição"
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND {_SEM_FOTO}
ORDER BY pt.name
LIMIT 200
""",
    },
    {
        'name': 'Lista — Sem Descrição de Cotação',
        'description': 'Produtos que precisam de description_sale',
        'icon': '📝',
        'chart_type': 'table',
        'color_scheme': 'amber',
        'size': '2',
        'sequence': 100,
        'sql_query': f"""
SELECT
    COALESCE(pt.default_code, '—')  AS "Ref.",
    pt.name::text                   AS "Produto",
    COALESCE(pc.complete_name, '—') AS "Categoria",
    CASE WHEN {_COM_FOTO} THEN 'Sim ✅' ELSE 'Não ❌' END AS "Tem Foto"
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND {_SEM_DESC}
ORDER BY pt.name
LIMIT 200
""",
    },
]

for w in widgets_cadastro:
    w['board_id'] = b2.id
    env['dashboard.widget'].create(w)

# ─── Commit e resultado ───────────────────────────────────────────────────────
env.cr.commit()
print("\n" + "=" * 60)
print(f"  ✅  '{b1.name}'  →  {len(widgets_pipeline)} widgets  (ID {b1.id})")
print(f"  ✅  '{b2.name}'  →  {len(widgets_cadastro)} widgets  (ID {b2.id})")
print("=" * 60 + "\n")
quit()
