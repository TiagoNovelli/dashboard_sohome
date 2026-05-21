# SoHome Dashboards — Exemplos de Widgets & Queries SQL

> Referência rápida de todos os widgets criados nos dashboards de exemplo.  
> Copie as queries no editor SQL ao criar novos widgets.

---

## Tipos de Widget disponíveis

| Valor | Descrição | Colunas esperadas na query |
|-------|-----------|---------------------------|
| `number` | KPI / Número grande | 1 linha · 1 coluna (o valor) |
| `bar` | Barras verticais | col 1 = label · col 2 = valor |
| `bar_horizontal` | Barras horizontais | col 1 = label · col 2 = valor |
| `line` | Linhas | col 1 = label · col 2 = valor |
| `area` | Área preenchida | col 1 = label · col 2 = valor |
| `pie` | Pizza | col 1 = label · col 2 = valor |
| `donut` | Donut | col 1 = label · col 2 = valor |
| `table` | Tabela completa | qualquer nº de colunas |

## Esquemas de cor disponíveis

`violet` · `blue` · `cyan` · `green` · `amber` · `rose` · `slate`

## Tamanhos de widget (grid de 4 colunas)

| Valor | Largura |
|-------|---------|
| `1` | 1/4 da tela |
| `2` | 1/2 da tela |
| `3` | 3/4 da tela |
| `4` | Largura total |

---

## 📋 Dashboard — Pipeline de Cotações

### 1. Cotações Abertas
```
Tipo:  number
Cor:   violet
Tam:   1/4
```
```sql
SELECT COUNT(*)
FROM sale_order
WHERE state IN ('draft','sent')
```

---

### 2. Valor do Pipeline
```
Tipo:    number
Cor:     green
Tam:     1/4
Prefixo: R$
```
```sql
SELECT ROUND(COALESCE(SUM(amount_total), 0)::numeric, 2)
FROM sale_order
WHERE state IN ('draft','sent')
```

---

### 3. Ticket Médio
```
Tipo:    number
Cor:     blue
Tam:     1/4
Prefixo: R$
```
```sql
SELECT ROUND(COALESCE(AVG(amount_total), 0)::numeric, 2)
FROM sale_order
WHERE state IN ('draft','sent')
```

---

### 4. Taxa de Conversão (30 dias)
```
Tipo:   number
Cor:    cyan
Tam:    1/4
Sufixo: %
```
```sql
SELECT ROUND(
    COUNT(*) FILTER (WHERE state = 'sale') * 100.0
    / NULLIF(COUNT(*), 0),
1)
FROM sale_order
WHERE state != 'cancel'
  AND create_date >= NOW() - INTERVAL '30 days'
```

---

### 5. Cotações por Status
```
Tipo: donut
Cor:  violet
Tam:  1/2
```
```sql
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
```

---

### 6. Cotações por Mês
```
Tipo: area
Cor:  blue
Tam:  1/2
```
```sql
SELECT
    TO_CHAR(date_order, 'MM/YY') AS mes,
    COUNT(*) AS cotacoes
FROM sale_order
WHERE state IN ('draft','sent','sale')
  AND date_order >= NOW() - INTERVAL '12 months'
GROUP BY TO_CHAR(date_order, 'MM/YY'),
         DATE_TRUNC('month', date_order)
ORDER BY DATE_TRUNC('month', date_order)
```

---

### 7. Valor por Mês (R$)
```
Tipo: bar
Cor:  green
Tam:  1/2
```
```sql
SELECT
    TO_CHAR(date_order, 'MM/YY') AS mes,
    ROUND(SUM(amount_total)::numeric, 0) AS valor
FROM sale_order
WHERE state IN ('draft','sent','sale')
  AND date_order >= NOW() - INTERVAL '12 months'
GROUP BY TO_CHAR(date_order, 'MM/YY'),
         DATE_TRUNC('month', date_order)
ORDER BY DATE_TRUNC('month', date_order)
```

---

### 8. Top 10 Clientes
```
Tipo: bar_horizontal
Cor:  amber
Tam:  1/2
```
```sql
SELECT
    rp.name AS cliente,
    COUNT(*) AS cotacoes
FROM sale_order so
JOIN res_partner rp ON rp.id = so.partner_id
WHERE so.state IN ('draft','sent','sale')
GROUP BY rp.name
ORDER BY cotacoes DESC
LIMIT 10
```

---

### 9. Cotações por Vendedor
```
Tipo: bar
Cor:  rose
Tam:  1/2
```
```sql
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
```

---

### 10. Dias Médios em Aberto por Vendedor
```
Tipo: bar_horizontal
Cor:  slate
Tam:  1/2
```
```sql
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
```

---

### 11. Cotações Abertas — Detalhamento
```
Tipo: table
Cor:  slate
Tam:  4/4 (largura total)
```
```sql
SELECT
    so.name                                               AS "Número",
    rp.name                                               AS "Cliente",
    TO_CHAR(so.date_order, 'DD/MM/YYYY')                  AS "Data",
    CASE so.state
        WHEN 'draft' THEN 'Rascunho'
        WHEN 'sent'  THEN 'Enviada'
        WHEN 'sale'  THEN 'Confirmada'
        ELSE so.state
    END                                                   AS "Status",
    ru_p.name                                             AS "Vendedor",
    (NOW()::date - so.date_order::date) || ' dias'        AS "Em Aberto",
    'R$ ' || TO_CHAR(so.amount_total, 'FM999G999G990D00') AS "Valor"
FROM sale_order so
JOIN res_partner rp   ON rp.id = so.partner_id
JOIN res_users ru     ON ru.id = so.user_id
JOIN res_partner ru_p ON ru_p.id = ru.partner_id
WHERE so.state IN ('draft','sent')
ORDER BY so.amount_total DESC
LIMIT 100
```

---

## 📦 Dashboard — Qualidade de Cadastro

> **Nota Odoo 18:** imagens de produto são armazenadas em `ir_attachment`, não
> como coluna direta em `product_template`. Use o padrão `EXISTS / NOT EXISTS`
> abaixo para verificar presença de foto.

```sql
-- ✅ Produto TEM foto
EXISTS (
    SELECT 1 FROM ir_attachment ia
    WHERE ia.res_model = 'product.template'
      AND ia.res_field = 'image_1920'
      AND ia.res_id = pt.id
)

-- ❌ Produto NÃO TEM foto
NOT EXISTS (
    SELECT 1 FROM ir_attachment ia
    WHERE ia.res_model = 'product.template'
      AND ia.res_field = 'image_1920'
      AND ia.res_id = pt.id
)
```

---

### 1. Produtos sem Foto
```
Tipo: number
Cor:  rose
Tam:  1/4
```
```sql
SELECT COUNT(*)
FROM product_template pt
WHERE pt.active = true
  AND NOT EXISTS (
      SELECT 1 FROM ir_attachment ia
      WHERE ia.res_model = 'product.template'
        AND ia.res_field = 'image_1920'
        AND ia.res_id = pt.id
  )
```

---

### 2. Sem Descrição de Cotação
```
Tipo: number
Cor:  amber
Tam:  1/4
```
```sql
SELECT COUNT(*)
FROM product_template pt
WHERE pt.active = true
  AND (pt.description_sale IS NULL OR TRIM(pt.description_sale::text) = '')
```

---

### 3. Total de Produtos Ativos
```
Tipo: number
Cor:  slate
Tam:  1/4
```
```sql
SELECT COUNT(*)
FROM product_template
WHERE active = true
```

---

### 4. Cadastro Completo (%)
```
Tipo:   number
Cor:    green
Tam:    1/4
Sufixo: %
```
```sql
SELECT ROUND(
    COUNT(*) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM ir_attachment ia
            WHERE ia.res_model = 'product.template'
              AND ia.res_field = 'image_1920'
              AND ia.res_id = pt.id
        )
        AND pt.description_sale IS NOT NULL
        AND TRIM(pt.description_sale::text) != ''
    ) * 100.0 / NULLIF(COUNT(*), 0),
1)
FROM product_template pt
WHERE pt.active = true
```

---

### 5. Status do Cadastro
```
Tipo: donut
Cor:  violet
Tam:  1/2
```
```sql
SELECT status, COUNT(*) AS total
FROM (
    SELECT
        CASE
            WHEN EXISTS (
                    SELECT 1 FROM ir_attachment ia
                    WHERE ia.res_model = 'product.template'
                      AND ia.res_field = 'image_1920'
                      AND ia.res_id = pt.id
                 )
                 AND pt.description_sale IS NOT NULL
                 AND TRIM(pt.description_sale::text) != ''
                THEN 'Completo'
            WHEN NOT EXISTS (
                    SELECT 1 FROM ir_attachment ia
                    WHERE ia.res_model = 'product.template'
                      AND ia.res_field = 'image_1920'
                      AND ia.res_id = pt.id
                 )
                 AND (pt.description_sale IS NULL OR TRIM(pt.description_sale::text) = '')
                THEN 'Falta Foto e Descrição'
            WHEN NOT EXISTS (
                    SELECT 1 FROM ir_attachment ia
                    WHERE ia.res_model = 'product.template'
                      AND ia.res_field = 'image_1920'
                      AND ia.res_id = pt.id
                 )
                THEN 'Falta Foto'
            ELSE 'Falta Descrição'
        END AS status
    FROM product_template pt
    WHERE pt.active = true
) t
GROUP BY status
ORDER BY total DESC
```

---

### 6. Sem Foto por Categoria
```
Tipo: bar_horizontal
Cor:  rose
Tam:  1/2
```
```sql
SELECT
    COALESCE(pc.complete_name, 'Sem Categoria') AS categoria,
    COUNT(*) AS sem_foto
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND NOT EXISTS (
      SELECT 1 FROM ir_attachment ia
      WHERE ia.res_model = 'product.template'
        AND ia.res_field = 'image_1920'
        AND ia.res_id = pt.id
  )
GROUP BY pc.complete_name
ORDER BY sem_foto DESC
LIMIT 15
```

---

### 7. Sem Descrição por Categoria
```
Tipo: bar_horizontal
Cor:  amber
Tam:  1/2
```
```sql
SELECT
    COALESCE(pc.complete_name, 'Sem Categoria') AS categoria,
    COUNT(*) AS sem_descricao
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND (pt.description_sale IS NULL OR TRIM(pt.description_sale::text) = '')
GROUP BY pc.complete_name
ORDER BY sem_descricao DESC
LIMIT 15
```

---

### 8. Evolução de Cadastros (6 meses)
```
Tipo: area
Cor:  green
Tam:  1/2
```
```sql
SELECT
    TO_CHAR(write_date, 'MM/YY') AS mes,
    COUNT(*) AS novos_produtos
FROM product_template
WHERE active = true
  AND write_date >= NOW() - INTERVAL '6 months'
GROUP BY TO_CHAR(write_date, 'MM/YY'),
         DATE_TRUNC('month', write_date)
ORDER BY DATE_TRUNC('month', write_date)
```

---

### 9. Lista — Produtos sem Foto
```
Tipo: table
Cor:  rose
Tam:  1/2
```
```sql
SELECT
    COALESCE(pt.default_code, '—')  AS "Ref.",
    pt.name::text                   AS "Produto",
    COALESCE(pc.complete_name, '—') AS "Categoria",
    CASE
        WHEN pt.description_sale IS NOT NULL
             AND TRIM(pt.description_sale::text) != ''
            THEN 'Sim ✅'
        ELSE 'Não ❌'
    END AS "Tem Descrição"
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND NOT EXISTS (
      SELECT 1 FROM ir_attachment ia
      WHERE ia.res_model = 'product.template'
        AND ia.res_field = 'image_1920'
        AND ia.res_id = pt.id
  )
ORDER BY pt.name
LIMIT 200
```

---

### 10. Lista — Sem Descrição de Cotação
```
Tipo: table
Cor:  amber
Tam:  1/2
```
```sql
SELECT
    COALESCE(pt.default_code, '—')  AS "Ref.",
    pt.name::text                   AS "Produto",
    COALESCE(pc.complete_name, '—') AS "Categoria",
    CASE
        WHEN EXISTS (
            SELECT 1 FROM ir_attachment ia
            WHERE ia.res_model = 'product.template'
              AND ia.res_field = 'image_1920'
              AND ia.res_id = pt.id
        ) THEN 'Sim ✅'
        ELSE 'Não ❌'
    END AS "Tem Foto"
FROM product_template pt
LEFT JOIN product_category pc ON pc.id = pt.categ_id
WHERE pt.active = true
  AND (pt.description_sale IS NULL OR TRIM(pt.description_sale::text) = '')
ORDER BY pt.name
LIMIT 200
```

---

## 💡 Queries úteis de referência

### Qualquer modelo — contar registros por mês
```sql
SELECT
    TO_CHAR(create_date, 'MM/YY') AS mes,
    COUNT(*) AS total
FROM <tabela>
WHERE create_date >= NOW() - INTERVAL '12 months'
GROUP BY TO_CHAR(create_date, 'MM/YY'),
         DATE_TRUNC('month', create_date)
ORDER BY DATE_TRUNC('month', create_date)
```

### Top N com JOIN para nome legível
```sql
SELECT
    rp.name AS nome,
    COUNT(*) AS total
FROM <tabela> t
JOIN res_partner rp ON rp.id = t.partner_id
GROUP BY rp.name
ORDER BY total DESC
LIMIT 10
```

### KPI com variação percentual (mês atual vs mês anterior)
```sql
SELECT
    ROUND(
        (atual - anterior) * 100.0 / NULLIF(anterior, 0),
    1) AS variacao_pct
FROM (
    SELECT
        COUNT(*) FILTER (
            WHERE DATE_TRUNC('month', create_date) = DATE_TRUNC('month', NOW())
        ) AS atual,
        COUNT(*) FILTER (
            WHERE DATE_TRUNC('month', create_date) = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
        ) AS anterior
    FROM <tabela>
) t
```

### Verificar imagem de produto (Odoo 16+)
```sql
-- Produtos COM foto
SELECT pt.name
FROM product_template pt
WHERE pt.active = true
  AND EXISTS (
      SELECT 1 FROM ir_attachment ia
      WHERE ia.res_model = 'product.template'
        AND ia.res_field = 'image_1920'
        AND ia.res_id = pt.id
  )

-- Produtos SEM foto
SELECT pt.name
FROM product_template pt
WHERE pt.active = true
  AND NOT EXISTS (
      SELECT 1 FROM ir_attachment ia
      WHERE ia.res_model = 'product.template'
        AND ia.res_field = 'image_1920'
        AND ia.res_id = pt.id
  )
```

### Tabelas Odoo mais usadas em relatórios

| Tabela | Modelo Odoo | Descrição |
|--------|-------------|-----------|
| `sale_order` | `sale.order` | Cotações e pedidos de venda |
| `sale_order_line` | `sale.order.line` | Itens de cotação/pedido |
| `product_template` | `product.template` | Produtos (ficha mestre) |
| `product_product` | `product.product` | Variantes de produto |
| `product_category` | `product.category` | Categorias de produto |
| `res_partner` | `res.partner` | Clientes, fornecedores, contatos |
| `res_users` | `res.users` | Usuários do sistema |
| `account_move` | `account.move` | Faturas e lançamentos |
| `account_move_line` | `account.move.line` | Itens de fatura |
| `stock_move` | `stock.move` | Movimentos de estoque |
| `purchase_order` | `purchase.order` | Pedidos de compra |
| `ir_attachment` | `ir.attachment` | Arquivos anexados (inclui imagens) |
