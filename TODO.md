# TODO — dashboard_sohome

> Backlog de melhorias e funcionalidades planejadas.

---

## 🔲 Criar filtros nos widgets

Permitir que o usuário filtre os dados de um widget sem editar a query SQL.

**Ideias de implementação:**
- Parâmetros dinâmicos na query: `{{date_from}}`, `{{date_to}}`, `{{user_id}}`
- Barra de filtros no topo de cada dashboard (período, empresa, vendedor…)
- Filtros salvos por dashboard no banco

**Referência de modelo de dados:**
```
dashboard.filter
  board_id       → Many2one(dashboard.board)
  name           → Char (ex: "Data inicial")
  param_key      → Char (ex: "date_from")
  filter_type    → Selection(date, char, many2one, integer)
  default_value  → Char
```

---

## 🔲 Controle de acesso e permissões por usuário

Definir quem pode ver, editar ou criar cada dashboard.

**Ideias de implementação:**
- Campo `allowed_user_ids` / `allowed_group_ids` em `dashboard.board`
- Herdar grupos do Odoo (`base.group_user`, `base.group_system`)
- Nível de acesso por dashboard: `viewer` / `editor` / `owner`
- Filtro automático no controller: só retorna boards que o usuário tem acesso

**Referência de campos:**
```
dashboard.board
  owner_id           → Many2one(res.users)
  allowed_user_ids   → Many2many(res.users)
  allowed_group_ids  → Many2many(res.groups)
  access_level       → Selection(private, users, groups, public)
```

---

## 🔲 Link para o modelo do Odoo filtrado

Clicar num card/número abre o list view do Odoo correspondente já filtrado.

**Ideias de implementação:**
- Campo `odoo_model` em `dashboard.widget` (ex: `sale.order`)
- Campo `odoo_domain` com o domain serializado (ex: `[('state','=','draft')]`)
- No frontend: botão "Ver no Odoo" que monta a URL `/odoo/model?domain=…`
- Usar `window.opener` ou `target="_blank"` para abrir sem sair do dashboard

**Referência de campos:**
```
dashboard.widget
  odoo_model   → Char (ex: "sale.order")
  odoo_domain  → Char (domain serializado, ex: "[['state','in',['draft','sent']]]")
  odoo_view_id → Many2one(ir.ui.view, opcional — forçar uma view específica)
```

---

## 🔲 Avaliar: usar ORM do Odoo ao invés de SQL puro

Analisar se vale substituir as queries SQL por chamadas ao ORM (`env[model].search_read()`).

**Prós do ORM:**
- Respeita regras de acesso (`ir.rule`) automaticamente
- Funciona com multi-empresa e multi-idioma sem adaptação
- Mais seguro (sem risco de SQL injection mesmo em erros de validação)
- Campos computados e relacionais funcionam nativamente

**Contras do ORM:**
- Menos flexível para queries complexas (GROUP BY, subqueries, window functions)
- Performance inferior em agregações grandes
- Usuário precisa conhecer os nomes técnicos dos modelos e campos

**Conclusão sugerida:** Modo híbrido
- Widgets simples (KPI, contagens, agrupamentos básicos) → ORM
- Widgets complexos (joins, múltiplas tabelas, cálculos SQL) → SQL puro com validação atual

---

*Atualizado em: 2026-05-21*
