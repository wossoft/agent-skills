# Component vocabulary

Use the names of the library declared in `app.md`. For shadcn/ui, check the installed `components/ui` and the current official registry before relying on a component; the registry changes over time.

## shadcn/ui (default)

| Purpose | Components |
| --- | --- |
| App frame | `Sidebar`, `SidebarTrigger`, `NavigationMenu`, `Menubar`, `Breadcrumb`, `Resizable`, `ScrollArea`, `Separator` |
| Actions | `Button`, `ButtonGroup`, `Toggle`, `ToggleGroup`, `DropdownMenu`, `ContextMenu`, `Command` |
| Containers | `Card`, `Tabs`, `Accordion`, `Collapsible`, `AspectRatio`, `Item` |
| Overlays | `Dialog`, `AlertDialog`, `Sheet`, `Drawer`, `Popover`, `HoverCard`, `Tooltip` |
| Forms | `Form`, `Field`, `Label`, `Input`, `InputGroup`, `InputOTP`, `Textarea`, `Select`, `NativeSelect`, `Combobox`, `Checkbox`, `RadioGroup`, `Switch`, `Slider`, `Calendar`, `DatePicker` |
| Data display | `Table`, `DataTable`, `Chart`, `Badge`, `Avatar`, `Kbd`, `Carousel`, `Pagination` |
| Feedback | `Alert`, `Sonner` (toast), `Progress`, `Skeleton`, `Spinner`, `Empty` |

Notes:

- `DataTable`, `DatePicker`, and `Combobox` are composition recipes (TanStack Table, Popover + Calendar, Popover + Command), not single primitives. Implement them as project components outside `components/ui`.
- shadcn **blocks** (for example sidebar, login, and dashboard blocks) may be referenced as a starting point with `hint: based on block <name>`; the layout tree still states the final structure.
- Prefer `Sheet` for side editing panels, `Dialog` for short focused tasks, `AlertDialog` for destructive confirmation, and `Drawer` for mobile bottom panels.

## Other libraries

Set `library:` in `app.md` and use that library's names directly. Common equivalents:

| shadcn/ui | Ant Design | MUI |
| --- | --- | --- |
| `Sidebar` | `Layout.Sider` + `Menu` | `Drawer` (permanent) + `List` |
| `Card` | `Card` | `Card` |
| `DataTable` | `Table` | `DataGrid` (MUI X) |
| `Dialog` | `Modal` | `Dialog` |
| `Sheet` | `Drawer` | `Drawer` |
| `AlertDialog` | `Modal.confirm` / `Popconfirm` | `Dialog` |
| `Select` | `Select` | `Select` |
| `Combobox` | `Select` (`showSearch`) / `AutoComplete` | `Autocomplete` |
| `DatePicker` | `DatePicker` | `DatePicker` (MUI X) |
| `Tabs` | `Tabs` | `Tabs` |
| `Sonner` | `message` / `notification` | `Snackbar` |
| `Empty` | `Empty` | — (compose) |
| `Skeleton` | `Skeleton` | `Skeleton` |
| `Form` + `Field` | `Form` + `Form.Item` | `FormControl` + `TextField` |

When migrating a blueprint between libraries, translate node types through this table and flag nodes without a clean equivalent instead of approximating silently.
