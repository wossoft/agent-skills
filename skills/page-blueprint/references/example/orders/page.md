---
title: 订单列表
pattern: list
status: draft
---

# 订单列表

## Purpose

运营人员按状态、时间和关键字查找订单，打开详情处理，或批量导出。

## Pattern

```yaml
resource: 订单
data: GET /api/orders
permission: Orders
search: 订单号 / 客户名
filters:
  - 状态: { field: status, as: tabs, options: [全部, 待支付, 已支付, 已发货, 已取消] }
  - 创建时间: { field: createdAt, component: DatePicker, mode: range }
columns:
  - 订单号: code
  - 客户: customer.name
  - 金额: { field: amount, format: currency, align: right, sortable: true }
  - 状态: { field: status, render: "@OrderStatusBadge" }
  - 创建时间: { field: createdAt, format: datetime, sortable: true }
create: dialog
open: sheet
rowMenu:
  - edit
  - 取消订单 -> confirm(确认取消该订单？) -> call(POST /api/orders/{id}/cancel) -> refresh(#table) -> toast(已取消)
bulk: [export]
export: true
```

## Changes

```yaml
- before(#filters):
    - Grid#stats:
        cols: 4
        responsive: { md: { cols: 2 }, sm: { cols: 1 } }
        data: GET /api/orders/stats
        children:
          - Card#stat-unpaid: { title: 待支付, value: stats.unpaid, action: set(filters.status, unpaid) }
          - Card#stat-unshipped: { title: 待发货, value: stats.unshipped, action: set(filters.status, paid) }
          - Card#stat-today: { title: 今日成交额, value: stats.todayAmount, format: currency }
          - Card#stat-refund: { title: 退款中, value: stats.refunding }
- set(#table): { responsive: { sm: { hint: 只保留订单号、金额、状态三列 } } }
```

## Overlays

The pattern's default `#create` and `#edit` would reuse the columns as fields, which is wrong here, so both are overridden.

```yaml
create:
  pattern: form
  type: Dialog
  size: md
  fields:
    - 客户: { field: customerId, component: Combobox, options: "GET /api/customers?q", required: true }
    - 备注: { field: remark, component: Textarea, max: 200 }
  onClose:
    saved: refresh(#table) -> toast(已创建) -> navigate(./[id], id=result)

edit:
  pattern: form
  type: Sheet
  side: right
  size: lg
  mode: edit
  data: GET /api/orders/{id}
  fields:
    - 收货人: { field: receiver.name, required: true }
    - 收货地址: { field: receiver.address, component: Textarea, required: true }
    - 备注: { field: remark, component: Textarea, max: 200 }
```

## States

- `Grid#stats` 加载失败时仅隐藏统计区，不阻塞列表。

## Data

- 金额单位为分，展示时格式化为元。（assumed）
- 「取消订单」仅对待支付、已支付订单显示，需要 `Orders.Cancel` 权限。

## Open questions

- 导出是同步下载还是异步任务？当前假设为异步任务。
- 「今日成交额」是否包含已退款订单？
