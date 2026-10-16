---
layout: app-shell
---

# 应用外框

```yaml
- Sidebar#nav: { collapsible: icon, items: $navigation }
- Stack#frame:
    children:
      - Row#topbar:
          sticky: true
          justify: between
          children: [SidebarTrigger, Breadcrumb, Slot#actions, "@UserMenu"]
      - Slot#outlet
```
