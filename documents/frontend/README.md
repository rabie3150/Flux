# Frontend Documentation

## Overview
The Flux frontend is a web-based operator console designed for mobile and desktop access via SSH port-forwarding. It is a static, no-build admin surface served by FastAPI at `/admin`.

## Documentation Index
- [Frontend Rebuild Plan](frontend-rebuild-plan.md) - Planning contract for the next admin frontend rebuild.
- [Stitch Design Adoption Plan](stitch-design-adoption.md) - Mapping from downloaded Stitch screens to the Flux rebuild.
- [View Map](view-map.md) - Screens, windows, flows, and required states.
- [Component Catalog](component-catalog.md) - Planned reusable frontend components and contracts.
- [State And API Contracts](state-and-api-contracts.md) - State shape, API client rules, current endpoints, and future contracts.
- [UI Components](ui-components.md) - Technical details of the current admin panel implementation.

## Tech Stack
- **Framework:** Vanilla JavaScript
- **Styling:** Vanilla CSS
- **Delivery:** Static files served via FastAPI

## Planning Boundary
The conception archive is frozen and remains the product reference. Planning documents in this folder translate those concepts into the active frontend engineering plan before implementation.
