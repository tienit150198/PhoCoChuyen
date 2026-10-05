# Shipper map and driving experience implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development to execute this local-only enhancement under the user's existing implementation authorization.

**Goal:** Make the existing first-person courier ride easier to navigate and visibly improve its neighbourhood and route map.

**Architecture:** Preserve the server's road grid, trip commands, signal receipts and economy. Add deterministic presentation of neighbourhood districts, a road-following navigation trace, readable driving HUD and a larger map view. All scenery remains client presentation, without new rewards or penalty rules.

**Tech Stack:** Existing vanilla JavaScript, Canvas2D first-person renderer, SVG route planner, Python/Node regression tests.

## Design

Extend the current first-person renderer rather than replace it with a top-down driving game or add a new 3D dependency. The street view retains its traffic and crossings. The navigation map gains district colours, block footprints, route line, start/destination markers and a north marker. A stopped rider can expand the map, then resume using the same controls. A visible help panel explains steering, gas/brake and slowing down at the marked destination. Turn cues report direction and distance along the road; arrival messages are never replaced by a premature turn instruction. No new audio is enabled.

## Tasks

- [x] Driving: add pure road-following route/navigation helpers with tests, enhanced mini/expanded map, readable live guidance and help; improve scene details without blocking streets or breaking all-pairs route reachability.
- [x] Planner map: replace bare grid presentation with detailed district blocks, landmarks, numbered route stops and consistent route colours; preserve planning/action semantics and escaping.
- [x] Integrate responsive CSS and translations; preserve user's muted local game.
- [x] Run courier driving/traffic regressions and JS checks. Review actual mobile/desktop first-person scene and route map; fix overlap or obscured controls.
- [x] Keep local server running and deliver local preview. Do not deploy.

## Ownership

Driving worker: public/js/careers/delivery_drive.js, optional new delivery_navigation.js and driving tests.
Planner worker: public/js/careers/delivery.js, new delivery_map.js and planner rendering tests.
Root: public/css/careers/delivery.css, translations, preview fixtures, integration and review. Existing unrelated local UX/story edits must remain intact.
