# Frontend Component Catalog

## Purpose
This catalog defines reusable frontend components for the Flux admin rebuild. Components should be small, stateless where practical, and shared across views.

## Shell Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| AppShell | `flux/static/admin/js/components/app-shell.js` | Overall layout, sidebar, topbar, main content region |
| SidebarNav | `flux/static/admin/js/components/sidebar.js` | Primary navigation and active route state |
| Topbar | `flux/static/admin/js/components/topbar.js` | Route title, selected context, refresh and operation summary |
| ToastStack | `flux/static/admin/js/components/toast-stack.js` | Short-lived success and failure messages |
| OperationPanel | `flux/static/admin/js/components/operation-panel.js` | Long-running backend action feedback |

## Navigation Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| Tabs | `flux/static/admin/js/components/tabs.js` | View-local navigation inside workbenches and details |
| Toolbar | `flux/static/admin/js/components/toolbar.js` | Action groups, refresh controls, row actions |
| FilterBar | `flux/static/admin/js/components/filter-bar.js` | Search, filters, sort controls |
| BreadcrumbContext | `flux/static/admin/js/components/breadcrumb-context.js` | Pipeline/platform context when nested views exist |

## Data Display Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| DataTable | `flux/static/admin/js/components/data-table.js` | Tables with loading, empty, error, and row action states |
| MetricCard | `flux/static/admin/js/components/metric-card.js` | Compact numeric summaries |
| StatusPill | `flux/static/admin/js/components/status-pill.js` | Semantic statuses such as healthy, warning, failed, pending |
| StageFlow | `flux/static/admin/js/components/stage-flow.js` | Pipeline stage progress from source to publish |
| ActivityList | `flux/static/admin/js/components/activity-list.js` | Recent event and operation log display |
| CapabilityMatrix | `flux/static/admin/js/components/capability-matrix.js` | Plugin/platform capability display |

## Interaction Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| Modal | `flux/static/admin/js/components/modal.js` | Focused preview, confirmation, or edit windows |
| ConfirmDialog | `flux/static/admin/js/components/confirm-dialog.js` | Destructive or high-impact action confirmation |
| PreviewMedia | `flux/static/admin/js/components/preview-media.js` | Video/image/content preview with unavailable states |
| ActionButton | `flux/static/admin/js/components/action-button.js` | Button with busy, disabled, and error states |
| SegmentedControl | `flux/static/admin/js/components/segmented-control.js` | Small option sets such as platform/status filters |

## Form Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| FormField | `flux/static/admin/js/components/form-field.js` | Label, control, hint, error message |
| Toggle | `flux/static/admin/js/components/toggle.js` | Boolean settings |
| SelectField | `flux/static/admin/js/components/select-field.js` | Single and multi-option settings |
| TextAreaField | `flux/static/admin/js/components/textarea-field.js` | Captions, templates, notes |
| SettingsGroup | `flux/static/admin/js/components/settings-group.js` | Grouped system or pipeline settings |

## State Components
| Component | Planned File | Responsibility |
|-----------|--------------|----------------|
| LoadingState | `flux/static/admin/js/components/loading-state.js` | Skeleton or compact spinner state |
| EmptyState | `flux/static/admin/js/components/empty-state.js` | No data state with optional action |
| ErrorState | `flux/static/admin/js/components/error-state.js` | Recoverable error display with retry |
| BackendPending | `flux/static/admin/js/components/backend-pending.js` | Honest placeholder for planned backend capability |
| StaleDataNotice | `flux/static/admin/js/components/stale-data-notice.js` | Shows last successful refresh after a failed refresh |

## Component Contracts
All components should follow these rules:
- Accept plain data objects and return HTML strings or DOM nodes.
- Escape untrusted text through a shared helper.
- Keep event wiring in the view or action layer unless the component is purely local.
- Support at least one clear loading, empty, or error state when data-backed.
- Avoid fetching data directly.
- Avoid reading or mutating global state directly.

## Styling Contracts
- Component classes use a predictable prefix such as `fx-`.
- Semantic color classes use tokens from `css/vars.css`.
- Component spacing uses shared tokens, not one-off pixel decisions.
- Buttons use icon buttons where the action is common and text buttons where clarity matters.
- Text must fit on mobile without overlap.

## Testing Expectations
Before a component is considered ready:
- Render it with normal data.
- Render it with missing or empty data.
- Render it while loading.
- Render it with an error.
- Verify keyboard focus for interactive controls.
- Verify mobile layout in the in-app browser.
