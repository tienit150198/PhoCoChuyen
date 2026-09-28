# Dependencies and asset provenance

Runtime application code uses the Python standard library and browser APIs; no third-party JavaScript bundle, CDN, image stock pack or audio recording is shipped. The only bundled third-party asset is the font listed below.

Room geometry, character drawing, item icons and audio tones are authored procedurally in `public/js/`. The visual style is an original 2D vector interpretation; no logo or branded illustration from the user reference images is embedded in the runtime.

`reference/` contains the user's previously generated design baseline. It is retained for traceability and further development, not relabeled as a new third-party asset license.

Development-only UI tests optionally use Playwright, Chromium and httpx installed by the developer. Their binaries/packages are **not included** in this ZIP; follow their respective licenses when obtaining/distributing them. Python and the optional Docker base image are also provided separately, not bundled here.

## Fonts

**Be Vietnam Pro** (weights 400, 600, 700, 800; Latin and Vietnamese subsets, WOFF2) in `public/fonts/`, used by `public/css/app.css`.
Copyright 2021 The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro).
Licensed under the SIL Open Font License, Version 1.1; the full license text ships next to the files as `public/fonts/OFL.txt`.
The WOFF2 subsets were taken unmodified from the `@fontsource/be-vietnam-pro` 5.3.0 package. The font is self-hosted (CSP `font-src 'self'`); no font CDN is contacted.
System font stacks remain as fallbacks, and the legal pages (`public/css/legal.css`) still use system fonts only.
