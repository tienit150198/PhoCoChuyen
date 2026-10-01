# Dependencies and asset provenance

Runtime application code uses the Python standard library and browser APIs; no third-party JavaScript bundle, CDN or image stock pack is shipped. The bundled third-party assets are the font and the CC0 background music listed below.

Room geometry, character drawing, item icons and UI sound effects are authored procedurally in `public/js/`. The visual style is an original 2D vector interpretation; no logo or branded illustration from the user reference images is embedded in the runtime.

`reference/` contains the user's previously generated design baseline. It is retained for traceability and further development, not relabeled as a new third-party asset license.

Development-only UI tests optionally use Playwright, Chromium and httpx installed by the developer. Their binaries/packages are **not included** in this ZIP; follow their respective licenses when obtaining/distributing them. Python and the optional Docker base image are also provided separately, not bundled here.

## Fonts

**Be Vietnam Pro** (weights 400, 600, 700, 800; Latin and Vietnamese subsets, WOFF2) in `public/fonts/`, used by `public/css/app.css`.
Copyright 2021 The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro).
Licensed under the SIL Open Font License, Version 1.1; the full license text ships next to the files as `public/fonts/OFL.txt`.
The WOFF2 subsets were taken unmodified from the `@fontsource/be-vietnam-pro` 5.3.0 package. The font is self-hosted (CSP `font-src 'self'`); no font CDN is contacted.
System font stacks remain as fallbacks, and the legal pages (`public/css/legal.css`) still use system fonts only.

## Music

Six background-music tracks in `public/music/`, all released under **CC0 1.0** (public domain) on OpenGameArt.org:

- *Apple Cider* by Zane Little Music
- *Hot Springs Town* by kistol
- *Happy Lullaby (song17)* by cynicmusic
- *Good Morning* by Cakeflaps
- *Urban Shop* and *Cozy Puzzle Title* by mintodog

`public/music/CREDITS.md` has the source links and what each track is used for. The files were re-encoded to MP3 and loudness-levelled; the music itself is unchanged.

Four wedding-party tracks in `public/music/wedding-*.mp3`, all **CC0 1.0** (public domain dedication):

- *Funky House* by Of Far Different Nature (OpenGameArt.org)
- *Funky Disco Beats to Boogie/Woogie to* by Fupi (OpenGameArt.org)
- Richard Wagner, *Bridal Chorus (Treulich gefuehrt)*, the Musopen recording on Wikimedia Commons (the composition is public domain, the recording CC0)
- *Chinese Hong Kong folk drums and gongs beating 02* by Jor92 (Freesound.org)

The groom's playlist adds six more, all **CC0 1.0** on OpenGameArt.org (title, author, tempo, length):

- `wedding-edm.mp3`: *Joyfully* by MintoDog, 170 BPM, 93.2 s
- `wedding-remix.mp3`: *Melodic EDM Loops* by Fupi, 140 BPM, 68.6 s
- `wedding-electro.mp3`: *Vengeance Electro* by Of Far Different Nature, 128 BPM, 60.0 s
- `wedding-latin.mp3`: *OMW to beat the big bad* by Fupi, 120 BPM, 80.0 s
- `wedding-funk.mp3`: *Funked Up* by Joth, 87 BPM, 66.2 s
- `wedding-love.mp3`: *Love Song [instrumental]* by nene, 95 BPM, 80.8 s

They were cut to loop lengths, crossfaded at the loop point and re-encoded to mono MP3; `public/music/CREDITS.md` has the source links.
