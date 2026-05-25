# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`dashboard_sohome` é um módulo Odoo 18 que adiciona dashboards interativos baseados em queries SQL. Os dashboards rodam em uma página standalone (`/sohome/dashboard`) completamente fora do framework OWL do Odoo — o frontend é Vanilla JS puro com Chart.js via CDN.

**Depende de:** `base`, `web` (Odoo 18)

## Infraestrutura

| | Staging | Produção |
|---|---|---|
| **Container Odoo** | `odoo18-staging` | `odoo18` |
| **Banco de dados** | `sohome_staging` | `sohome` |
| **Container DB** | `odoo18-db` | `odoo18-db` |
| **Porta HTTP** | `8091` | padrão |
| **Servidor** | `root@191.252.100.229` | `root@191.252.100.229` |
| **Docker Compose** | `/opt/odoo18` | `/opt/odoo18` |

## Instalação e desenvolvimento

### Instalar / atualizar no staging (via SSH)
```bash
# Atualizar staging manualmente (sem passar pelo CI)
ssh root@191.252.100.229 "
  cd /home/github-runner/staging-addons/dashboard_sohome && git pull origin main &&
  docker exec odoo18-staging odoo -c /etc/odoo/odoo.conf \
    -d sohome_staging --stop-after-init --update dashboard_sohome --workers 0 --http-port 8091 &&
  cd /opt/odoo18 && docker compose up -d odoo-staging --force-recreate
"
```

### Ver logs em tempo real
```bash
# Staging
ssh root@191.252.100.229 "docker logs odoo18-staging -f 2>&1 | grep -i 'dashboard_sohome\|sohome'"

# Produção
ssh root@191.252.100.229 "docker logs odoo18 -f 2>&1 | grep -i 'dashboard_sohome\|sohome'"
```

### Query rápida no banco (via container odoo18-db)
```bash
# Staging
ssh root@191.252.100.229 "docker exec odoo18-db psql -U odoo -d sohome_staging -c 'SELECT ...'"

# Produção
ssh root@191.252.100.229 "docker exec odoo18-db psql -U odoo -d sohome -c 'SELECT ...'"
```

### Ver versão do código no servidor
```bash
ssh root@191.252.100.229 "cd /home/github-runner/staging-addons/dashboard_sohome && git log --oneline -3"
```

### Carregar os dashboards de exemplo (seed)
```bash
# Staging
ssh root@191.252.100.229 "docker exec -i odoo18-staging odoo shell -d sohome_staging" < scripts/seed_dashboards.py

# Local (se o container estiver acessível)
docker exec -i odoo18-staging odoo shell -d sohome_staging < scripts/seed_dashboards.py
```
O script é idempotente: remove dashboards com o mesmo nome antes de recriar.

### Testar a query de um widget no backend
No formulário Odoo do widget, use o botão **"🧪 Testar"**. Ele chama `action_test_query()` no modelo e exibe colunas + contagem de linhas em uma notificação.

### Acessar o dashboard
```
# Staging
http://191.252.100.229:8091/sohome/dashboard

# Produção
http://191.252.100.229/sohome/dashboard
http://191.252.100.229/sohome/dashboard?board_id=<id>
```

## Arquitetura

### Fluxo de dados
```
Odoo backend (Python)
  ↓  JSON-RPC (Odoo wire format: {jsonrpc, method, params})
DashboardController (controllers/main.py)
  ↓  POST /sohome/api/*
SoHomeDashboard class (static/src/js/dashboard.js)
  ↓  dados {columns, rows}
Chart.js 4.x (via CDN)  /  renderização de tabela  /  KPI numérico
```

### Modelos Odoo

**`dashboard.board`** — Container de widgets
- `widget_ids` → One2many para `dashboard.widget`
- `action_view_dashboard()` → redireciona para `/sohome/dashboard?board_id=<id>`

**`dashboard.widget`** — Widget individual com query SQL
- `sql_query` → validado em `_validate_sql()`: apenas `SELECT`, bloqueia keywords perigosas via regex
- `execute_query()` → executa via `env.cr.execute()`, limite de 5000 linhas
- `chart_type` → determina como o JS renderiza: `number`, `bar`, `bar_horizontal`, `line`, `area`, `pie`, `donut`, `table`
- `size` (1–4) → largura no grid de 4 colunas CSS
- `color_scheme` → chave para `COLOR_PALETTES` no JS

### API REST (controllers/main.py)
Todos os endpoints aceitam POST e retornam JSON-RPC:

| Endpoint | Função |
|---|---|
| `GET /sohome/dashboard` | Renderiza a página HTML |
| `POST /sohome/api/boards` | Lista todos os boards com widgets (sem SQL) |
| `POST /sohome/api/widget/<id>/data` | Executa a query e retorna `{columns, rows}` |
| `POST /sohome/api/widget/create` | Cria widget |
| `POST /sohome/api/widget/<id>/update` | Atualiza campos permitidos (allowlist explícita) |
| `POST /sohome/api/widget/<id>/delete` | Remove widget |
| `POST /sohome/api/board/create` | Cria board |
| `POST /sohome/api/board/<id>/delete` | Remove board |

> **Nota:** `/api/boards` não retorna `sql_query` por design — a SQL só é transmitida ao salvar/editar o widget.

### Frontend (static/src/js/dashboard.js)

Classe `SoHomeDashboard` instanciada como `window.app` no DOMContentLoaded.

- **Tema:** `localStorage('sohome-theme')` → atributo `data-theme` no `<html>`. Anti-flash inline no `<head>` do template aplica o tema antes do CSS renderizar.
- **Cache de dados:** `this.widgetDataCache` armazena `{columns, rows, meta}` por widget — usado para recriar gráficos no toggle de tema sem nova chamada à API.
- **Charts:** `this.charts` mapeia `widgetId → Chart instance`. Destruídos ao trocar de board ou re-renderizar.
- **Auto-refresh:** `this.refreshTimers` com `setInterval`; mínimo 30 s; limpos ao trocar de board.
- **Config global:** `window.__SOHOME__` injetado pelo template Odoo com `csrf_token`, `active_board_id`, `user_name`.

### Template (templates/index.xml)

Página HTML completa — **não usa OWL nem assets do Odoo**. Carregado via `request.render('dashboard_sohome.dashboard_page', {...})`. Usa `t-out` (não `t-esc`) para os valores injetados.

## Convenções importantes

### Validação de SQL
`_validate_sql()` no modelo é chamada tanto em `@api.constrains` (ao salvar) quanto antes de executar. Regex com `\b` para word boundaries. O comentário `# noqa: S608` em `execute_query()` suprime o aviso de bandit sobre SQL dinâmico — é intencional.

### Queries para gráficos (bar, line, area, pie, donut)
- Coluna 1 = label (string)
- Coluna 2 = valor numérico

### Queries para KPI (number)
- Retorna 1 linha, 1 coluna (o valor)
- Coluna 2 opcional = label exibido abaixo do número

### Queries para tabela (table)
- Qualquer número de colunas
- Limite de 200 linhas no SAMPLES.md, mas o backend aceita até 5000

### Imagens de produto no Odoo 18+
Imagens **não** estão em colunas diretas de `product_template`. Use `ir_attachment`:
```sql
EXISTS (
    SELECT 1 FROM ir_attachment ia
    WHERE ia.res_model = 'product.template'
      AND ia.res_field = 'image_1920'
      AND ia.res_id = pt.id
)
```

### Tabelas Odoo mais usadas em widgets
`sale_order`, `sale_order_line`, `product_template`, `product_product`, `product_category`, `res_partner`, `res_users`, `account_move`, `account_move_line`, `stock_move`, `purchase_order`, `ir_attachment`

## Backlog (TODO.md)
- Filtros dinâmicos nos widgets via parâmetros `{{date_from}}`, `{{date_to}}`
- Controle de acesso por usuário/grupo por dashboard
- Link "Ver no Odoo" para abrir list view do modelo filtrado diretamente do widget
- Modo híbrido ORM + SQL (widgets simples via ORM, complexos via SQL puro)
