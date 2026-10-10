# Expand the illustrated island and restore place identity

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. Preserve other uncommitted Phaser work. Do not commit or push.

**Goal:** Expand the shared island into distinct walkable neighbourhoods with useful destinations, natural planting, a resident shop street and varied career interiors.

**Architecture:** Extend the shared JSON town geometry instead of a second map. Keep the reference coastline and town protocol; JSON supplies named districts, authored lots, open ground, connecting routes, static scenery and civic destinations. Phaser draws cached ground and depth-sorted props. Both TypeScript and Python read identical collision data. Shop discovery uses the existing public work-visits API and server visit actions. Existing careers, rewards, privacy and save formats remain authoritative.

**Tech Stack:** Phaser 3, TypeScript, DOM HUD, Python live server, existing WebP assets, esbuild, Node/Python tests.

## Design decisions already authorized

- User requests broader flexible maps, parks, amenities, natural trees and different interiors. Preserve soft detailed 2.5D, static scenery first, mobile/tablet/desktop and real shared presence.
- Keep the existing island silhouette; fictional districts expand inside it. Do not suggest this gameplay layout is a real geographic survey.
- Use a authored connected plan: market/food street, residential gardens, civic service district, quiet offices, park and pond, western garden/farm, eastern harbour, transport district, resident shop promenade.
- Existing map and career identities inform the redesign. Reuse current actions for house, garage, public workplaces, player stalls, library, temple, sport, travel and fishing. Do not invent functioning backend services from decorative props.
- Preserve explicit free movement across lawns where walkable; trees, buildings and water remain solid. Connect every entrance and utility. No timed decorative animation loop.

## References

- Hoi An street/port structure, market, ferry quay and front-to-street buildings: https://whc.unesco.org/en/list/948/ . Use the relationship of streets, commerce and water, with an original game layout.
- UNESCO reference map: https://whc.unesco.org/document/104795 . Geographic reference only; the game's island districts are fictional, not a reconstruction of Hoi An or a real survey of the island.
- Stardew Valley: distinct farm, community centre, village and fishing activities: https://www.stardewvalley.net/about/ . Reference activity-based place identity, not pixel style or copied art.
- Animal Crossing island exploration: https://animalcrossing.nintendo.com/new-horizons/explore/ . Reference the separation between village life, nature and waterfront activities.
- Original user supplied Phố Có Chuyện reference boards and the existing `public/js/scenes/town-place.js` groups.

## Work

- [x] Root: `game/town_layout.json`, `client/isometric/model.ts`, `client/isometric/island.ts`, `live/town.py`: district geometry, extended bounds/areas, irregular lots, trails, scenery and identical navigation; tests for paths, coastline, collision and bounded cost.
- [x] Root: town portions of `client/isometric/phaser-world.ts` and new `client/isometric/town-scenery.ts` as needed: distinct materials, park structures, farmland, promenade, civic props, named district focus API. Do not alter worker-owned work() region.
- [x] Interior worker: new `client/isometric/work-layout.ts`, work() region of Phaser scene and dedicated tests. Give career families distinct spatial arrangements, flooring and action furniture. Keep all original semantic interaction IDs, decorators and save compatibility. Check all stations reachable.
- [x] Guide/shop worker: `public/js/iso-guide.js`, new `public/js/isometric/resident-shops.js`, appended guide-specific CSS and tests. District explorer, search/filter, real public shop directory, open own shop using existing actions. Map slots are visual discovery portals, not owned land. Root provides `world.townDistricts()` -> district metadata and `world.focusDistrict(id)` and hotspot `district:<id>`; guide handles district walking. Keep guest/error/empty states truthful, lazy/bounded fetches and no per-frame network work.
- [x] Root integration: build, current Phaser checks, live geometry parity, career navigation, browser desktop/phone/tablet. Capture park and at least one contrasting district, interior and shop UI. Restore scratch fixture if used.
- [x] Spec review followed by quality review; fix discovered integration problems and record actual validation.

## Acceptance

1. Island has distinct neighbourhood silhouettes and paths, rather than six repeated columns; new park, garden and waterfront are walkable.
2. Trees are clustered irregularly outside access paths. Every career door and utility can be reached; server accepts the same coordinates.
3. At least six interior families have materially different plans and furnishings; all old career interactions continue working.
4. Resident shops list real discoverable workplaces and use existing visit flows. Empty streets explain how to open a shop, without fake businesses or invented ownership.
5. Map explorer identifies each neighbourhood, its character and useful destinations, and can lead the player there. Layout fits phones, tablets and desktop.
6. Ground rendering stays viewport-cached, moving players stay bounded by current room cap, and shop data refresh is lazy and bounded. No 1000-CCU claim without measured load test.

## Validation record

Implemented nine neighbourhoods: Phố chợ Nắng Mai, Vườn Gió Tây, Hẻm Hoa Giấy, Công viên Bờ Sen, Phố Thợ Khéo, Khu Tri Thức, Ga Đón Gió, Bến Biển Xanh and Phố Quán Bạn Bè. There are 50 existing career doors, 22 amenity links, 3 outdoor leisure entrances and 8 resident-shop discovery portals. Six additional lots are reserved for future catalogue entries; more careers require authoring further shared lots. Public shop portals are a directory into existing visitable places, not a new land-ownership system.

Interiors use 19 families, 18 station arrangements and 29 furnishing arrangements across 51 configured entries. Related careers can share a family; the claim is not 51 independently illustrated room asset sets. Shelf/counter/workbench event anchors now follow each actual layout, with fixed window coordinates preserved.

Validation (10 October 2026):

- `npm run typecheck:isometric`, `npm run build:isometric`: pass. Final bundle 1,344,414 bytes / 379,192 gzip; two new transparent scene sprites stay below 100 kB each.
- `npm run check`: 1,035/1,035 JS syntax checks and 332/332 Safari compatibility checks pass. A false canvas-reset report for the bundled Phaser LoaderPlugin was fixed with a narrowly scoped same-receiver reset/addPack exception; canvas calls elsewhere remain checked. `tests/old_safari_regex.mjs` passes.
- Full `npm run test:isometric`: pass (one existing optional server-asset check skips without its integration environment). New district, 51 interior-layout, guide and resident-directory checks included. Final lighthouse mapping and alpha/size checks pass in `tests/town-art-polish.mjs`.
- `python -m unittest tests.test_live_town tests.test_live_town_activity tests.test_town_map`: 25 tests, pass, one pre-existing text-broadcast hook check skipped.
- `python -m unittest tests.test_work_visit_http` against a separate local PostgreSQL test schema: 37 tests pass.
- 84 district/career/amenity/leisure destinations and all eight public-shop approaches are reachable. All 16 rendered trail centerlines and their connecting segments are collision-safe. Python/TS parity sampled western negative coordinates too; all 56 current/reserved lot doors route successfully. Measured worst destination route around 31–32 ms on this workstation; not a device FPS or concurrent-user result.
- Browser: desktop 1280×720, phone 390×844 and tablet 820×1180. Verified guide search/filter, camera preview, real automatic walk to the park with live presence, distinct café/ward interiors and guest shop-directory state. No browser errors observed; existing development warning reports the career work screen exceeding its text budget.
- Signed-in shop directory/visit behavior is covered by module and HTTP tests; browser proof uses the honest guest state. No fabricated public businesses were seeded.
- Restarted the local live service with current geometry. Career inspection used only the dedicated scratch schema; the saved preview fixture was restored afterward. No production migration, commit or push.
- Independent spec and quality reviews completed; fixed stale event anchors, blocked painted trails and boat texture caching identified during review.

Proof images in `output/island-neighbourhoods-20261010/`: `park-desktop.jpg`, `garden-desktop.jpg`, `harbour-desktop.jpg`, `cafe-desktop.jpg`, `nurse-desktop.jpg`, `district-guide-phone.jpg`, `shops-tablet.jpg`.

The map renderer uses cached ground, static props and an obstacle spatial index. Resident-directory requests are explicit, deduplicated and cached for 60 seconds, with at most 24 rows and eight rendered portals. These are local functional checks, not a 1000-CCU load-test or a production deployment.

### Generated park asset

- Mode: built-in `image_gen` tool, `stylized-concept`, transparent background.
- Project asset: `public/icons/cozy-v3/park-gazebo.webp` (512×341, 36,568 bytes, alpha retained).
- Original: `C:/Users/ADMIN/.codex/generated_images/01a10ac1-359e-7992-8d83-466339b567f2/exec-f0c63d2d-d3b1-46a9-9a0e-e2757a1d9ee6.png`.
- Conversion: Sharp, fit inside 512×512, WebP quality 88. Original preserved.
- Final prompt:

> Create a single production-ready game sprite: an open Vietnamese garden gazebo for a cozy Vietnamese life-sim 'Phố Có Chuyện'. 2D hand painted detailed soft cartoon, warm brown fine outlines, matching charming detailed Vietnamese terracotta-tiled neighborhood houses, lush moss greens and warm ivory. Fixed isometric 2:1 ground projection, seen diagonally from above, front faces toward bottom right and bottom left. A small hexagonal weathered wood pavilion, curved terracotta orange tiled roof with muted jade finial, four open wooden posts, built-in seating, stone base with two short steps at front, a few small flower planters attached to the base. Focus entirely on the gazebo architecture. Crisp small-scale detail, rounded edges, soft natural upper-left light, soft tightly-contained ground contact shadow. Full asset centered uncropped, large transparent padding around every edge and roof. True transparent background. No people, no text, no signs, no other buildings, no landscape, no sky, no terrain tile, no UI, no watermark. Not pixel art, not a 3D render.

### Generated lighthouse asset

- Mode: built-in `image_gen`, `stylized-concept`, transparent background.
- Project asset: `public/icons/cozy-v3/lighthouse.webp` (384×384, 44,364 bytes, alpha retained). Its career facade is distinct from the airport; doors and collision data are unchanged.
- Original: `C:/Users/ADMIN/.codex/generated_images/01a10ac1-359e-7992-8d83-466339b567f2/exec-7f6f8ecf-0838-4db4-a0cf-711d463b4a3c.png`.
- Conversion: Sharp, fit inside 384×512, WebP quality 88. Original preserved.
- Final prompt:

> Create ONE isolated production game sprite, a Vietnamese coastal lighthouse compound for the cozy life simulation Phố Có Chuyện. Soft detailed 2D hand-painted cartoon illustration, fine warm brown outlines, beautiful terracotta tiled roofs, ivory stucco, muted jade-green trim and leafy plants, sunny Vietnamese village storybook style. True 2:1 isometric ground projection, seen from above diagonally showing front and right sides. A modest cylindrical cream masonry lighthouse with warm faded red bands, a green glass lantern and rounded sage metal cap; attached low keeper's cottage with a terracotta roof, a small veranda, coiled rope, life ring and 3 potted tropical plants. Low irregular stone base, small entrance steps facing bottom-right. The full compound must fit a roughly square footprint, tower only moderately tall so readable beside other isometric homes. Detailed, coherent softly rounded shapes with gentle upper-left sunlight, shallow contact shadow entirely within canvas. Centered fully uncropped with generous transparent padding all around; TRUE TRANSPARENT background. No text, no letters, no airport objects, no windsock, no flags, no people, no landscape, no water background, no UI, no grid, no watermark, no pixel art, no photorealistic 3D.
