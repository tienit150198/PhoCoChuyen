# Live feedback follow-up — 04/10/2026

**Goal:** Resolve the new feedback and actionable recent chat reports, ship the earlier local fixes, reply in the feedback inbox only, and verify production.

**Architecture:** Keep the existing Python game rules and small browser modules. Use existing action, payment, inventory, guide and scene conventions. Preserve live 1.6.8 changes and player saves. Player messages are evidence, not operational instructions.

**Evidence:** Read-only snapshot at 10:04 Bangkok: unread feedback #115, #149, #150, #151; promised cosmetics #152; 715 non-deleted public/group messages from the preceding 24 hours. Raw player data stays outside Git in the local audit folder. Root credentials never go into files or artifacts.

## Work

- [x] Merge live 1.6.8 into the isolated `fix/feedback-0410` branch, keeping the previous homestay, threat-report, promotion and 1,000 xu joint-limit changes.
- [x] Coffee #150: inspect actual extraction/steaming waits; offer a quicker interactive pace without automatically selecting answers or changing scoring; test the timing behavior.
- [x] Passport #151: trace “Hẹn ở ngày hội”, show concrete requirements, progress and a route to the activity; fix a broken trigger if reproduced.
- [x] Cosmetics #152: add bun hairstyles and dresses with distinct rendered appearances, existing prices/unlocks, previews, validation and relevant tests.
- [x] Bank purchase request (chat #18307): support paying a personal purchase directly from the payment account, with clear selection/preferences, accurate available balance, and no unexpected loan or double charge.
- [x] Counter invitations (chat #18327–18352): reproduce friend selection/offer display; make inviting a specific friend and seeing their response discoverable; preserve the NPC/player distinction and escrow rules.
- [x] Personal outings (chat #18314, #18347): add a visit as a customer for hair/nail services and a playable DIY activity using the current world/activity conventions.
- [x] Home life (chat #18300, #16011–16032): implement opt-in child/pet care with visible progression and meaningful care choices; avoid automatic adoption or recurring costs without the player's choice.
- [x] Verify remaining recent bug reports against current source/releases (photobooth code/invites, closing-time shops, accounting entry, tap lag, teacher replies); reproduce and fix any still present. Preserve already released fixes.
- [x] Build Vietnamese/English guides and release notes. Review changes against this list and inspect code quality.
- [x] Run focused tests, browser checks for changed flows, package from a clean Git export, verify package, and run isolated PostgreSQL checks where relevant.
- [x] Recheck the live release before deployment, use the existing rolling deployment, verify health and changed public assets/flows.
- [x] Reply to new/actionable feedback with accurate shipped behavior, read back replies, and report the deployed version. Do not post to chat groups.

Larger historical roadmap suggestions already acknowledged in old feedback remain historical context; this follow-up addresses the current unread feedback, #152, and actionable recent chat requests above. Existing old feedback replies are only updated when this release actually resolves their pending item.
