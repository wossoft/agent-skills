---
title: 订单详情
status: draft
presentation: { type: Sheet, side: right, size: lg, over: /orders }
---

# 订单详情

## Purpose

查看单个订单的商品、金额与物流，并执行发货。从列表进入时以右侧抽屉展示；直接访问链接时为完整页面。

## Layout

```yaml
- Slot#actions:
    children:
      - Button#ship:
          text: 发货
          visible: order.status == paid && permission(Orders.Ship)
          action: open(#ship-order, id=order.id)

- Stack#page:
    data: GET /api/orders/{id}
    children:
      - Section#summary:
          title: "订单 {order.code}"
          actions: ["@OrderStatusBadge"]
          children:
            - Grid: { cols: 2, responsive: { sm: { cols: 1 } }, children: [Text: 客户, Text: 下单时间, Text: 收货地址, Text: 备注] }
      - Section#items:
          title: 商品
          children:
            - Table#items:
                columns: [商品, 单价, 数量, 小计]
      - Section#logistics:
          title: 物流
          visible: order.shipment != null
          children:
            - Item: { hint: 承运商、运单号、最近一条轨迹 }
```

## Overlays

```yaml
ship-order:
  type: Dialog
  title: 发货
  size: sm
  params: [id]
  children:
    - Form#ship-form:
        submit: call(POST /api/orders/{id}/ship) -> close(shipped)
        fields:
          - 承运商: { component: Select, field: carrier, options: GET /api/carriers, required: true }
          - 运单号: { component: Input, field: trackingNo, required: true }
  footer:
    - Button: { text: 取消, variant: ghost, action: close() }
    - Button#ship-submit: { text: 确认发货, action: submit(#ship-form) }
  onClose:
    shipped: refresh(#page) -> toast(已发货)
    cancel: none
```

## Open questions

- 发货后是否需要同时刷新底层列表 `/orders` 的 `DataTable#orders`？当前假设关闭抽屉时刷新。
