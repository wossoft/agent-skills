---
blueprint: 订单后台
library: shadcn
icons: lucide
---

# 订单后台

## Navigation

```yaml
- 仪表盘: { icon: LayoutDashboard, to: / }
- 订单:
    icon: ShoppingCart
    children:
      - 订单列表: { to: /orders }
- 设置: { icon: Settings, to: /settings }
```

## Shared components

```yaml
"@UserMenu":
  - DropdownMenu:
      trigger: Avatar
      items: [个人设置 -> navigate(/settings), 退出登录 -> call(POST /api/logout)]

"@OrderStatusBadge":
  - Badge: { hint: 待支付=outline，已支付=secondary，已发货=default，已取消=destructive }
```

## Conventions

- loading：首次加载用 `Skeleton` 占位；后续刷新保留旧数据并在区块右上角显示 `Spinner`。
- empty：使用 `Empty`，附带该页最主要的创建操作（若有权限）。
- error：区块内 `Alert` (destructive) + 重试按钮；提交失败用 `Sonner` toast。
- permission：无权限的操作直接隐藏，不做禁用态。
- overlay：含表单的弹层默认 `dismiss: { outside: false, dirty: confirm }`；`sm` 断点下 `Dialog` 改为 `Drawer`。
