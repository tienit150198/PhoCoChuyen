# Courier city art upgrade

User wants people, trees and city prettier and more realistic in the local courier preview. Build on the existing first-person renderer and free analog joystick. No deployment.

Art direction: warm Vietnamese neighbourhood, softened plaster and muted shop fronts, dimensional windows/awnings/balconies, recognisable people with limbs/faces/clothes and natural walking, layered irregular foliage, shadows and depth. More believable proportions and materials rather than photographic textures. Preserve streets, destination gates, joystick, map/help, traffic and economy.

- [x] Isolated sprite module: shaded people, trees, scooter riders, deterministic variations, bounded detail and reduced-motion compatibility. Worker owns delivery_sprites.js and its new tests.
- [x] Isolated architecture module: richer house and landmark facades in projected coordinates, near-distance details only. Worker owns delivery_architecture.js and its new tests.
- [x] Root integrates render helpers, refines light/ground/sky and culling. No gameplay changes.
- [x] Root verifies actual desktop/mobile scenes, drive/control/traffic regressions, frame cost, reviews code, and refreshes muted local preview.

Modules expose Canvas drawing functions only, no DOM, state mutation, network or random per-frame allocations. Root owns delivery_drive.js, documents and integration; workers must not alter it.
