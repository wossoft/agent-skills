# Page patterns

Most admin and business pages are a list, a detail view, a form, a settings page, or a dashboard. Public website pages (landing, article, hub, comparison) are in [site-patterns.md](site-patterns.md) and use the same mechanism. A pattern page states only its parameters and its differences from the standard; the pattern supplies the layout tree, the node ids, and the default states.

## Using a pattern

````markdown
---
title: 订单列表
pattern: list
status: draft
---

# 订单列表

## Purpose
...

## Pattern
```yaml
<parameters of the pattern>
```

## Changes            (optional)
```yaml
<operations on the expanded tree>
```

## Overlays / States / Interactions / Data / Open questions
Only what differs from the pattern defaults and app conventions.
````

A page has either `Pattern` (+ optional `Changes`) or a full `Layout`, never both. Overlays may also use a pattern: `create-order: { pattern: form, type: Dialog, ... }`. Defining an overlay in `Overlays` with the same id as one the pattern supplies (`create`, `edit`) replaces the default; only the keys given are overridden.

**Choose a full Layout instead** when the page does not resemble any pattern, or when `Changes` would touch more than about a third of the expanded tree. A pattern bent out of shape is harder to read than a plain tree.

## Shorthand shared by patterns

- **Columns and fields:** `标签: field` or `标签: { field, component, format, required, ... }`. When the component is omitted, infer it from the API type (string → `Input`, long text → `Textarea`, enum → `Select`, boolean → `Switch`, date → `DatePicker`, reference → `Combobox`); if types are unknown, use `Input` and mark it `# assumed`.
- **Endpoints:** `data` is the read endpoint. Write endpoints default to REST conventions on the same resource (`POST` create, `PUT /{id}` update, `DELETE /{id}` delete). State an endpoint explicitly only when it differs.
- **Permissions:** `permission: Orders` implies `Orders.Create`, `Orders.Update`, `Orders.Delete` for the matching actions. Unauthorized actions follow the app's permission convention.

## Changes operations

Changes is a YAML list of operations addressed by the expanded tree's node ids:

| Operation | Effect |
| --- | --- |
| `before(#id): [nodes]` / `after(#id): [nodes]` | Insert sibling nodes |
| `append(#id): [nodes]` | Add children at the end |
| `replace(#id): [nodes]` | Replace the node |
| `set(#id): { props }` | Merge props into the node |
| `remove(#id)` | Delete the node |

```yaml
- before(#filters):
    - Grid#stats: { cols: 4, data: GET /api/orders/stats, children: [...] }
- set(#table): { responsive: { sm: { hint: 只保留订单号、金额、状态 } } }
- remove(#bulk-bar)
```

---

## list

Find, filter, and act on records of one resource.

```yaml
resource: 订单                  # display name used in titles, buttons, and messages
data: GET /api/orders
permission: Orders             # optional
search: 订单号 / 客户名          # optional; placeholder of the keyword search
filters:                        # optional; tabs for one enum, controls for the rest
  - 状态: { field: status, as: tabs, options: [全部, 待支付, 已支付, 已发货, 已取消] }
  - 创建时间: { field: createdAt, component: DatePicker, mode: range }
columns:
  - 订单号: code
  - 金额: { field: amount, format: currency, align: right, sortable: true }
create: dialog                  # dialog | sheet | page | none   (default: dialog)
open: page                      # page | sheet | none — what clicking a row does (default: page)
rowMenu: [edit, delete]         # built-ins: edit, delete; or custom `文本 -> action`
bulk: [delete, export]          # optional; enables row selection
export: true                    # optional; adds an export button
pagination: server              # server | client | none   (default: server)
```

Expands to:

```text
Slot#actions   Button#export?  Button#create?
Stack#page
  Section#header      title = resource, description = total count
  Row#filters         Tabs for `as: tabs` filter, then Input#search and other filter controls
  DataTable#table     columns + row menu column; selection when `bulk`
  Row#bulk-bar        visible when selection is not empty; one button per bulk action
Overlays              #create (when create: dialog | sheet), #edit (when rowMenu has edit and create is not page)
```

Defaults:

- Filters, search, sort, and page are mirrored in the URL query; changing a filter resets to page 1; search is debounced.
- Loading uses skeleton rows; refetching keeps the current rows visible.
- Empty with no filters shows `Empty` with the create action; empty with filters shows "no matching results" with a reset-filters action.
- `create` / `edit` overlays use the `form` pattern with the columns' fields unless `fields` is given; on success `refresh(#table) -> toast`.
- `delete` and bulk delete use `confirm(...) -> call(DELETE ...) -> refresh(#table) -> toast`.
- `open: page` navigates to `./[id]`; `open: sheet` opens the `[id]` page as a routed overlay over this list.

## detail

Read one record and act on it.

```yaml
resource: 订单
data: GET /api/orders/{id}
permission: Orders
title: "订单 {code}"            # header text
status: { field: status, render: "@OrderStatusBadge" }   # optional badge next to the title
sections:
  - 基本信息: [客户: customer.name, 下单时间: createdAt, 备注: remark]
  - 收货信息: [收货人: receiver.name, 地址: receiver.address]
related:                        # optional tables of child records
  - 商品: { data: items, columns: [商品: name, 单价: price, 数量: qty] }
actions: [edit, delete]         # built-ins: edit, delete; or custom `文本 -> action`
edit: sheet                     # sheet | dialog | page   (default: sheet)
tabs: false                     # true puts sections and related tables in Tabs
```

Expands to:

```text
Slot#actions   one Button per action (destructive last)
Stack#page
  Section#header      title + status badge
  Section#<n>         one per section: label/value Grid (2 columns, 1 on sm)
  Section#<related>   one Table per related entry
Overlays              #edit (unless edit: page)
```

Defaults: Breadcrumb links back to the parent list. Not found shows `Empty` with a back link. `delete` confirms, calls `DELETE`, then navigates to the parent list with a toast. Successful edit refreshes `#page`.

## form

Create or edit one record, as a page or inside an overlay.

```yaml
resource: 订单
mode: create                    # create | edit (edit loads `data` first)
data: GET /api/orders/{id}      # edit only
submit: POST /api/orders        # defaults by mode
sections:                       # or a flat `fields:` list
  - 客户信息:
      - 客户: { field: customerId, component: Combobox, options: "GET /api/customers?q", required: true }
  - 其他:
      - 备注: { field: remark, component: Textarea, max: 200 }
after: navigate(../[id], id=result.id)   # page default: back to parent; overlay default: close(saved, result.id)
```

Expands to `Form#form` with one `Section` per section, a footer `Row#footer` with cancel and submit buttons, and field-level validation messages. Defaults: submit is disabled while submitting; server validation errors map to fields, other errors toast; leaving or closing with unsaved changes asks for confirmation.

## settings

Several independent groups of preferences.

```yaml
nav: tabs                       # tabs | side (side uses a left list on lg, tabs on sm)
groups:
  - 个人资料: { data: GET /api/profile, save: PUT /api/profile, fields: [姓名: name, 头像: avatar] }
  - 通知: { data: GET /api/notify-settings, save: PUT /api/notify-settings, fields: [邮件通知: { field: email, component: Switch }] }
```

Each group is a `Card` holding a `form`. Each group saves independently with its own button and toast; switches may save immediately when `autosave: true`.

## dashboard

Overview of key numbers and recent activity.

```yaml
stats:                          # Card per metric; optional action to a filtered list
  - 待发货: { value: unshipped, action: "navigate(/orders, status=paid)" }
  - 今日成交额: { value: todayAmount, format: currency }
data: GET /api/dashboard
charts:
  - 近 30 天成交额: { type: line, x: date, y: amount }
lists:
  - 最新订单: { data: "GET /api/orders?limit=5", columns: [订单号: code, 金额: amount], more: /orders }
```

Expands to `Grid#stats` (4 columns, 2 on md, 1 on sm), `Grid#charts` (2 columns, 1 on md), and `Grid#lists`. Each block loads and fails independently.
