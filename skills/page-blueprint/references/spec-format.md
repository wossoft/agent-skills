# Blueprint format

Keys, ids, component names, and action names are in English. Visible text (titles, labels, placeholders, column names) uses the product's language.

## Directory = route tree

The blueprint directory mirrors the app's routes, following App Router conventions:

```text
blueprint/
  app.md                  # library, menu, conventions, shared composites
  _layout.md              # root layout (shell) wrapping every page below it
  (auth)/                 # route group: organizes files, not part of the URL
    _layout.md
    login/page.md         # /login
  orders/
    page.md               # /orders
    _overlays/
      create.md           # overlay too large to keep inside a page
    [id]/
      page.md             # /orders/[id]
      edit/page.md        # /orders/[id]/edit
```

| Entry | Meaning |
| --- | --- |
| `page.md` | A routable page. Its route is its directory path. |
| `_layout.md` | Frame shared by every page in this directory and below. Layouts nest. |
| `[param]/` | Dynamic segment. |
| `(group)/` | Grouping only; omitted from the route. Use for sections with a different layout. |
| `_overlays/` | Overlays shared by pages in this directory and below. |

- The route path **is** the page id: `navigate(/orders/[id], id=row.id)`. Relative paths (`./[id]`, `..`) resolve against the current page's route. A target is valid when the matching `page.md` exists.
- The directory expresses nesting, not navigation. The sidebar menu lives in `app.md` because its grouping and order need not follow the URL.
- Do not hand-maintain a page inventory or flow diagram. When one is wanted, generate it from the tree and the `navigate()` / `open()` actions.
- A one- or two-page request may use a single `blueprint.md` containing the same sections.

## app.md

````markdown
---
blueprint: <app name>
library: shadcn            # shadcn | antd | mui | ...; node types use this library's names
icons: lucide              # optional
breakpoints: { sm: 640, md: 768, lg: 1024 }   # optional; defaults to the library/Tailwind defaults
---

# <App name>

## Navigation
```yaml
- 仪表盘: { icon: LayoutDashboard, to: / }
- 订单:
    icon: ShoppingCart
    children:
      - 订单列表: { to: /orders }
```

## Shared components
Project-owned composites, referenced in pages as `@Name`.

```yaml
"@UserMenu":
  - DropdownMenu: { trigger: Avatar, items: [个人设置, 退出登录] }
```

## Conventions
App-wide defaults for loading, empty, error, permission-denied, toast, and overlay behavior, so pages only record exceptions.
````

## _layout.md

````markdown
---
layout: app-shell
---

```yaml
- Sidebar#nav: { collapsible: icon, items: $navigation }
- Stack#frame:
    children:
      - Row#topbar: { sticky: true, children: [SidebarTrigger, Breadcrumb, Slot#actions, "@UserMenu"] }
      - Slot#outlet
```
````

`Slot#outlet` receives the page or the next nested layout. Other named slots (`Slot#actions`) are filled by pages.

## page.md

````markdown
---
title: 订单列表
status: draft              # draft | reviewed | implemented
presentation: page         # optional; see "Routed overlays"
pattern: list              # optional; see patterns.md — replaces the Layout section with Pattern + Changes
---

# 订单列表

## Purpose
One or two sentences: who uses this page and what they accomplish.

## Wireframe            (optional)
```text
ASCII sketch for humans only.
```

## Layout               (or `## Pattern` + `## Changes` when `pattern` is set)
```yaml
<node tree; see grammar below>
```

## Overlays
Overlays opened only from this page; see "Overlays".

## States
Page- or component-level loading / empty / error / permission / disabled states not covered by app conventions.

## Interactions
| trigger | condition | result |
| --- | --- | --- |

## Data
Sources, query parameters, field meanings, validation rules, and permissions.

## Open questions
Assumptions to confirm.
````

In `Layout`, a top-level `Slot#<name>` node fills that slot of the enclosing layout; all other top-level nodes fill `outlet`.

## Layout grammar

A layout is a YAML list of **nodes**. A node is a single-key map:

```yaml
- Type#id: <value>
```

- `Type` is a library component (`Button`, `DataTable`, `Card`), a layout primitive (below), or a shared composite (`"@UserMenu"` — quote it in YAML).
- `#id` is optional for static decoration and required for anything interactive, data-bearing, or referenced elsewhere.
- `<value>` is either a scalar (the node's text or label) or a map of props. `children` (a node list) is the only reserved prop.
- A bare string list item (`- Separator`) is a node with no props.
- Keep every block valid YAML. Quote values containing `{}`, `?`, `: `, or ` #`, and use `{name}` inside quoted text for interpolated data (`"共 {total} 笔"`).

### Layout primitives

| Primitive | Meaning | Common props |
| --- | --- | --- |
| `Stack` | Vertical flow | `gap`, `align` |
| `Row` | Horizontal flow | `gap`, `justify` (`start` / `between` / `end`), `align`, `wrap` |
| `Grid` | Equal or weighted columns | `cols` (number or ratio such as `"2:1"`), `gap` |
| `Split` | Fixed side panel + flexible content | `side` (`left` / `right`), `size` (`sm` / `md` / `lg`) |
| `Section` | Titled content group | `title`, `description`, `actions` |
| `Slot` | Placeholder filled by a page or nested layout | — |
| `Text` | Plain inline text that is not a library component | — |

Size words (`xs`, `sm`, `md`, `lg`, `xl`) are relative and map to the library's spacing scale. Use them instead of pixels.

### Behavior props

| Prop | Meaning | Example |
| --- | --- | --- |
| `action` | What happens on activation | `navigate(/orders/[id], id=row.id)` |
| `data` | Source of displayed data | `GET /api/orders?status&q&page` |
| `bind` | Field or state this input controls | `filters.status` |
| `visible` / `disabled` | Condition | `permission(Orders.Create)`, `selection.empty` |
| `responsive` | Overrides per breakpoint (mobile-first) | `{ md: { cols: 2 }, sm: { cols: 1 } }` |
| `hint` | Free text for anything the grammar cannot express | `首列固定` |

### Actions

| Action | Meaning |
| --- | --- |
| `navigate(/route, params?)` | Route to another page |
| `open(#overlay, params?)` | Show an overlay |
| `close(outcome?, data?)` | Close the current overlay with an outcome (default `cancel`) |
| `submit(#form)` | Validate and submit a form |
| `call(METHOD /path)` | Invoke an API; follow with `then:` / `error:` when it matters |
| `refresh(#node)` | Reload a data-bearing node |
| `toast(text)` | Feedback message |
| `set(state, value)` | Change local UI state (tab, filter, selection) |
| `confirm(text) -> <action>` | Require confirmation (AlertDialog) first |

Chain actions with `->`. Params use `name=value`. When a flow is more than a short chain, describe it in the Interactions table instead.

### Data components

Tables, lists, and forms put their structure in props:

```yaml
- DataTable#orders:
    data: GET /api/orders
    columns:
      - 订单号: { field: code, link: "navigate(/orders/[id], id=row.id)" }
      - 客户: customer.name
      - 金额: { field: amount, format: currency, align: right }
      - 状态: { field: status, render: Badge }
      - 操作: { render: DropdownMenu, items: [编辑, 取消订单] }
    selection: multiple
    pagination: server
    empty: { text: 暂无订单, action: open(#create-order) }

- Form#profile:
    submit: call(PUT /api/profile) -> toast(已保存)
    fields:
      - 姓名: { component: Input, field: name, required: true }
      - 角色: { component: Select, field: role, options: GET /api/roles }
      - 简介: { component: Textarea, field: bio, max: 200 }
```

## Overlays

Dialogs, sheets, and drawers are defined once and opened by id. Decide first whether the overlay needs its own URL.

### Local overlays

Defined in the page's `Overlays` section, or as `_overlays/<id>.md` when large or shared. `open(#id)` resolves to the page's own overlays first, then `_overlays/` in the same directory and its ancestors.

```yaml
create-order:
  type: Dialog                 # Dialog | Sheet | Drawer | AlertDialog
  title: 新建订单
  size: md                     # sm | md | lg | xl | full
  side: right                  # Sheet / Drawer only
  params: ["customerId?"]      # inputs passed by open(); `?` marks optional
  data: GET /api/...           # optional; loaded when opened
  dismiss: { outside: false, dirty: confirm }   # close on outside click/Esc; confirm when the form is dirty
  responsive: { sm: { type: Drawer } }
  url: "?create=1"             # optional; mirror open state in the query string
  children:
    - Form#create-form:
        submit: call(POST /api/orders) -> close(created, result.id)
        fields: []
  footer:
    - Button: { text: 取消, variant: ghost, action: close() }
    - Button#create-submit: { text: 创建, action: submit(#create-form) }
  onClose:                     # what the opener does for each outcome
    created: refresh(#orders) -> toast(已创建)
    cancel: none
```

Every overlay must answer: type and placement, trigger, inputs, content, how it closes (outcomes), what the opener does after each outcome, and dismissal rules. `onClose` is the item most often missing; include it whenever the overlay changes data.

- Overlays may open other overlays (a Sheet that asks for delete confirmation). Inner outcomes are handled by the overlay that opened them.
- `confirm(text) -> <action>` is shorthand for a plain AlertDialog; define a full overlay only when the confirmation has content or inputs.
- `Popover`, `DropdownMenu`, `HoverCard`, and `Tooltip` are written inline on the trigger node, not as overlays.

### Routed overlays

When an overlay must be linkable (detail opened as a Sheet over a list, but rendered as a full page when visited directly), make it a real `page.md` and declare its presentation:

```markdown
---
title: 订单详情
presentation: { type: Sheet, side: right, size: lg, over: /orders }
---
```

`navigate()` to such a page from `over` shows the overlay; direct entry renders the page normally. Implement with the framework's mechanism (for example intercepting routes or a query-param modal), chosen in the implementation step.
