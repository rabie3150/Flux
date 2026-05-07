# Stitch Design Adoption Plan

## Purpose
This document maps the downloaded Stitch designs into the Flux frontend rebuild plan. The Stitch files are visual references and layout references. They should not be copied directly into production because the generated HTML is standalone, CDN-heavy, and not wired to the Flux API/state model.

## Source Package
Local source:

```text
C:\Users\Rabie\Downloads\stitch_clean_minimalist_design\
```

Included artifacts:

| Stitch Folder | Files | Flux View Mapping |
|---------------|-------|-------------------|
| `flux_dashboard` | `code.html`, `screen.png` | Dashboard |
| `pipeline_detail_quran_daily` | `code.html`, `screen.png` | Pipeline Workbench: Overview |
| `ingredient_library_quran_daily` | `code.html`, `screen.png` | Pipeline Workbench: Ingredients |
| `production_queue_quran_daily` | `code.html`, `screen.png` | Pipeline Workbench: Production |
| `platform_workers` | `code.html`, `screen.png` | Workers |
| `post_log` | `code.html`, `screen.png` | Posts |
| `system_settings` | `code.html`, `screen.png` | System |
| `kinetic_minimalist` | `DESIGN.md` | Design token reference |

## Design System Takeaways
Use the Stitch design as the base visual direction:

- Light neutral canvas.
- White content panels.
- Compact left sidebar.
- Top utility/search bar.
- Electric blue primary actions.
- Slate text and icons.
- High-contrast status colors.
- 8px spacing rhythm.
- 8px to 12px radii.
- Minimal depth through borders and soft shadows.

Adjustments for Flux implementation:

- Remove negative letter spacing from typography.
- Keep large cards tighter than Stitch where the app needs higher information density.
- Add explicit backend operation feedback to every screen that triggers API work.
- Add pipeline and platform context more consistently than the generated screens do.
- Use actual Flux navigation labels: Dashboard, Pipelines, Workers, Posts, System, Plugins, Activity.
- Keep Plugins and Activity as first-class views, even though Stitch did not generate dedicated screens for them.

## What To Keep
From the Stitch designs:

- App shell layout: fixed left sidebar, top utility bar, wide content canvas.
- Dashboard composition: status cards, pipeline summary, worker summary, recent activity.
- Pipeline detail concept: breadcrumb, title, status pill, run controls, tabs, stage flow.
- Ingredient library cards: media preview cards with approval state and bulk toolbar.
- Production queue table: status tabs, metrics, failed/processing/ready states, pagination.
- Worker cards: platform identity, status, last post, next scheduled action.
- Post log filters and table structure.
- System settings tabs and split configuration panels.

## What To Rewrite
Do not directly paste Stitch `code.html` into `flux/static/admin/index.html`.

Rewrite these parts into Flux modules:

| Stitch Pattern | Flux Implementation |
|----------------|---------------------|
| Tailwind CDN classes | CSS tokens and component classes in `flux/static/admin/css/` |
| Standalone HTML pages | Routed views under `flux/static/admin/js/views/` |
| Static sample rows | API-backed state from `state/store.js` and `api/endpoints.js` |
| Inline static icons | Shared icon/component helpers |
| Per-screen sidebars | One shared `AppShell` and `SidebarNav` |
| Per-screen search bars | Shared `Topbar` with per-view controls |
| Fake actions | Real actions with operation progress and backend-pending states |

## Missing Concepts To Add
The Stitch package is good visually, but it does not fully satisfy the conception archive alone. The rebuild still needs:

- Plugin management view.
- Activity/event stream view.
- Backend-pending states for unavailable routes.
- Loading, empty, error, and stale states for every API-backed region.
- Operation panel for render, fetch, approve, reject, identify, assign worker, and settings save calls.
- Worker detail view with schedule, captions, pipelines, and logs.
- Pipeline settings tab with source, platform, caption, schedule, and approval policy.
- Mobile/narrow viewport behavior.

## Implementation Mapping
The rebuild should absorb Stitch in this order:

1. Design tokens: convert `kinetic_minimalist/DESIGN.md` into `css/vars.css`, then tune for Flux constraints.
2. App shell: implement the shared sidebar/topbar based on the Stitch layout.
3. Dashboard: rebuild from `flux_dashboard`, wired to `/api/health`, `/api/system/dashboard`, and `/api/system/activity`.
4. Pipeline workbench overview: rebuild from `pipeline_detail_quran_daily`, wired to pipeline detail/stats/activity APIs.
5. Ingredients tab: rebuild from `ingredient_library_quran_daily`, wired to ingredient list, preview, approve, and reject APIs.
6. Production tab: rebuild from `production_queue_quran_daily`, wired to production list, stream, and identify APIs.
7. Workers: rebuild from `platform_workers`, wired to worker list and assignment APIs.
8. Posts: rebuild from `post_log`, initially with backend-pending UI until post endpoints exist.
9. System: rebuild from `system_settings`, wired to health/settings APIs and backend-pending diagnostics.
10. Plugins and Activity: design directly from the same visual system because Stitch did not generate them.

## Production Acceptance Rules
Before any Stitch-inspired screen is accepted:

- It must use the Flux app shell, not a copied standalone page shell.
- It must use shared components from `components/`.
- It must render from state selectors, not hardcoded rows.
- It must have loading, empty, error, and stale states.
- It must show operation feedback for backend actions.
- It must pass `node --check`.
- It must pass the Flux frontend review/audit with no frontend warnings.
- It must be visually checked in the in-app browser on desktop and mobile widths.
