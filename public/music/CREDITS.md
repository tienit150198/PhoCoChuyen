# Background music

Every track here is released under **CC0 1.0 (public domain)**: <https://creativecommons.org/publicdomain/zero/1.0/>. It may be used, changed and shared without asking and without credit. We credit the artists anyway.

The files were re-encoded to MP3 (mono, 32 kHz, 64 kbps, to keep the game light on phones) and levelled to about −20 LUFS so no track is much louder than another. The notes were not changed.

| File | Title | Artist | Source | Used for |
|---|---|---|---|---|
| `apple-cider.mp3` | Apple Cider | Zane Little Music | <https://opengameart.org/content/apple-cider> | Food shops, grocery (default) |
| `hot-springs-town.mp3` | Hot Springs Town | kistol | <https://opengameart.org/content/hot-springs-town> | Florist, farm, homestay, tour guide |
| `happy-lullaby.mp3` | Happy Lullaby (song17) | cynicmusic | <https://opengameart.org/content/happy-lullaby-song17> | Mother & baby, pet care, pharmacy; "Êm dịu" |
| `good-morning.mp3` | Good Morning | Cakeflaps (via You're Perfect Studio) | <https://opengameart.org/content/good-morning> | Teacher, salon, customer care |
| `urban-shop.mp3` | Urban Shop | mintodog | <https://opengameart.org/content/urban-shop> | Delivery, repair; "Tươi vui" |
| `cozy-puzzle.mp3` | Cozy Puzzle Title | mintodog | <https://opengameart.org/content/cozy-puzzle-title> | Accounting, tax & payroll |

The licence was checked on each source page on 2026-09-28. `public/js/v4/music.js` maps careers to tracks.

## Wedding party (`public/js/v4/wedfeast.js`, 1.3.0)

Recorded tracks for the live wedding party, all **CC0 1.0 (public domain dedication)**. The licence was checked on each source page, and the files downloaded, on 2026-10-02. Re-encoded like the tracks above (MP3 mono, 32 kHz, 64 kbps), levelled to about −17 LUFS (the march −19) and cut so each loops (notes below). None is a song by any artist the players named.

| File | Title | Author | Source | Licence | Notes |
|---|---|---|---|---|---|
| `wedding-house.mp3` | Funky House | Of Far Different Nature | <https://opengameart.org/content/funky-house> | CC0 | 128 BPM; the first 67.5 s (36 bars) so it loops, the ringing tail left out |
| `wedding-disco.mp3` | Funky Disco Beats to Boogie/Woogie to | Fupi | <https://opengameart.org/content/funky-disco-beats-to-boogiewoogie-to> | CC0 | 110 BPM; the whole track (61 bars, already a loop) |
| `wedding-march.mp3` | Bridal Chorus "Treulich geführt" (Wagner, *Lohengrin*, 1850) | Musopen (the recording) | <https://commons.wikimedia.org/wiki/File:Richard_Wagner_-_Treulich_geführt.ogg> | CC0 (`{{Cc-zero}}` on the file page) | the first 42 s, faded out: the couple's entrance |
| `wedding-lion.mp3` | Chinese Hong Kong folk drums and gongs beating 02 | Jor92 | <https://freesound.org/people/Jor92/sounds/792545/> | CC0 | a lion dance recorded in Hong Kong; 42 s from 0:20, crossfaded into a loop (from the site's HQ MP3 preview) |

### The groom's playlist ("🎧 Chọn nhạc", 1.3.0)

The groom (the bride when he is away) picks one of these, or the house and disco above, for the whole party (`live/wedding.py` `wed_music`). Same rules: **CC0 1.0** only, licence read on each OpenGameArt page and the files downloaded on 2026-10-02, re-encoded to MP3 mono 32 kHz 64 kbps, levelled to −17 LUFS (the slow song −19), cut to whole bars and crossfaded at the loop point. Together about 3.6 MB.

| File | Picker label | Title | Author | Source | Licence | BPM | Length / size | Notes |
|---|---|---|---|---|---|---|---|---|
| `wedding-edm.mp3` | 🔥 Quẩy EDM | Joyfully | MintoDog | <https://opengameart.org/content/joyfully> | CC0 | 170 | 93.2 s / 746 KB | the author's loop version (66 bars) |
| `wedding-remix.mp3` | 🚀 Remix bay phòng 140 | Melodic EDM Loops | Fupi | <https://opengameart.org/content/melodic-edm-loops> | CC0 | 140 | 68.6 s / 549 KB | seven of the pack's loops arranged into 40 bars |
| `wedding-electro.mp3` | ⚡ Electro house | Vengeance Electro | Of Far Different Nature | <https://opengameart.org/content/vengeance-electro> | CC0 | 128 | 60.0 s / 481 KB | bars 96-128 (3:00-4:00) |
| `wedding-latin.mp3` | 🌴 House Latin | OMW to beat the big bad | Fupi | <https://opengameart.org/content/omw-to-beat-the-big-bad> | CC0 | 120 | 80.0 s / 641 KB | the first 40 bars |
| `wedding-funk.mp3` | 🎸 Funk nhún nhảy | Funked Up | Joth | <https://opengameart.org/content/funked-up> | CC0 | 87 | 66.2 s / 531 KB | the whole 24-bar loop |
| `wedding-love.mp3` | 💞 Nhạc chậm cho cặp đôi | Love Song [instrumental] | nene | <https://opengameart.org/content/love-song-instrumental> | CC0 | 95 | 80.8 s / 647 KB | bars 24-56 (0:61-2:22), the first dance |

## The pagoda (`public/audio/chua/`, "Vào chùa": `public/js/v4/chua-visit.js`, 1.4.8)

Real recordings, each released under **CC0 1.0 (public domain dedication)** or marked **public domain** by its author (`{{PD-self}}` on Wikimedia Commons). The licence was read on each source page (the Freesound sound page, or the Commons file page and its API metadata) and the files were downloaded on 2026-10-02; Freesound files come from the site's HQ MP3 preview. None is synthesised and none is a song by any artist. Re-encoded to MP3 (mono, 44.1 kHz, 96 kbps); the one-shot sounds peak-normalised to −1.5 dBFS, the chanting levelled to about −20 LUFS and the background loops to about −24 LUFS. "Loop": the last 2 s crossfaded into the first 2 s, so the file repeats without a click.

| File | Length | Title | Author | Source | Licence | Used for · changes |
|---|---|---|---|---|---|---|
| `nen-chua-sang.mp3` | 88.0 s (loop) | zenkojibells_norm.wav | earthmonkey1 | <https://freesound.org/people/earthmonkey1/sounds/514135/> | CC0 | The yard and the dining hall: early morning birdsong, temple bells far away (Sakaori, Yamanashi). 142–232 s made into a loop |
| `tung-kinh-loop.mp3` | 88.0 s (loop) | Monks chanting in Chi Lin nunnery, Hong Kong November 2018 | Oplurus | <https://freesound.org/people/Oplurus/sounds/458983/> | CC0 | The main hall, played soft: chanting heard from inside the nunnery. 0–90 s made into a loop and made louder |
| `chuong-dai-hong-2.mp3` | 16.0 s | Temple Bell, Valley of the Temples | Mista Bumpy | <https://freesound.org/people/Mista%20Bumpy/sounds/232333/> | CC0 | The bell tower (nghe chuông): the bronze bell at Byōdō-in, Hawaii. The first strike (5.5–21.5 s), faded out over the last 3 s |
| `chuong-gia-tri.mp3` | 12.8 s | SingingBowl1.ogg ("Sound of a Singing Bowl") | BambooBeast | <https://commons.wikimedia.org/wiki/File:SingingBowl1.ogg> | Public domain (`{{PD-self}}`) | Khấn, and the start and end of a chant (chuông gia trì). Used whole, faded at the end |
| `mo-1.mp3` | 0.6 s | Mokugyo.wav | jonopodmore | <https://freesound.org/people/jonopodmore/sounds/607215/> | CC0 | Each tap on the mõ, and the abbot's three opening beats: a small mokugyo from Kōya-san with its cloth beater. One strike |
| `su-tung-kinh.mp3` | 31.1 s | singing monk in buddhism temple in vietnam | Ottak16 | <https://freesound.org/people/Ottak16/sounds/706583/> | CC0 | Thầy's voice under a chant (tụng kinh): a monk chanting in a temple in Vietnam, recorded in 2007. Used whole, faded in and out |
