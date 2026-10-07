# 🎙️ Phòng hát mic trực tiếp: the SFU (LiveKit) on the production server

Owner decision 07/10: in the public karaoke rooms the singer on stage can turn on a live mic; everyone in the room
hears them; listeners cannot speak; nothing is recorded. The game side is `live/karaoke.py` (mic sessions),
`live/sfu.py` (tokens and the SFU's server API), `game/karaoke_mic.py` (birth year, age rule) and
`public/js/v4/karaoke-mic.js` (the browser SDK). Switch: `LIVE_KARAOKE_MIC=1`, off by default.

**Nothing here has been installed. The lead reviews this folder and runs `install.sh`.**

| File | Installed as |
|---|---|
| `livekit.yaml` | `/etc/livekit/livekit.yaml` (root:livekit 640) |
| `mnl-livekit.service` | `/etc/systemd/system/mnl-livekit.service` (user `livekit`, 2 cores, 1 GB, sandboxed) |
| `nginx-sfu.conf` | `/etc/nginx/snippets/mnl-sfu.conf`, included in the 443 server of `sites-enabled/phocochuyen` |
| `nginx-stream-443.conf` | stage 2 only: `/etc/nginx/mnl-stream.conf` (SNI routing on 443) |
| `install.sh` | run from the release dir: `check`, `stage1`, `smoke`, `stage2`, `off` |
| (written by stage1) | `/etc/livekit/keys.yaml` (livekit 600, a new random key pair), `/etc/mot-ngay-lam-nghe/kara-mic.env` (root 600), drop-ins `zz-kara-mic.conf` for `mnl-live` and `mot-ngay-lam-nghe` |

## Why LiveKit

| | One singer → ~30 listeners, 0.3–1 s | Ops on this server | Security / control | Verdict |
|---|---|---|---|---|
| **WebRTC mesh** | The singer's phone would send 30 copies (30 × ~50 kbps up, 30 encoders): phones cannot. P2P also shows each listener the singer's IP address (a minor's). Needs TURN anyway (UDP is blocked here). | none | none: every peer is trusted | ✖ |
| **mediasoup** | Works (a C++ worker under Node). We would write the signalling server, the room/permission model, reconnects, and run coturn for TURN. | Node + a native build toolchain on the server, ~1–2 k lines of our own code | as good as what we write | ✖ too much new code |
| **LiveKit** (Apache-2.0) | Built for it: one publisher, many subscribers, ICE/TCP and built-in TURN/TLS, Opus with jitter buffer (~100–300 ms end to end on a good line). | **one static Go binary**, one YAML, one systemd unit; JS SDK pinned on jsDelivr with SRI | JWT per player, per room: publish *microphone only* vs subscribe only; server API to create/delete rooms and remove a participant. No recording unless Egress is deployed (it is not). | **✔ chosen** |

Measured locally (`scripts/browser_live_karaoke_mic.py`, LiveKit 1.13.7, Chromium, fake mic): the singer publishes,
listeners receive (inbound RTP grows ~50 packets/s), a blocked listener gets nothing, the room is gone the second the
stage changes, an under-16 account gets no mic. With **`--tcp-only`** (Chromium forbidden to use UDP, like this
server) the voice flows over ICE/TCP. Stage 2 was rehearsed on the Mac too: browsers forced to relay only, TLS ended
in front of LiveKit on port 443 with a PROXY header (as nginx stream will), `turn.external_tls` +
`turn.proxy_protocol`: the voice arrived through TURN/TLS (`relayProtocol: tls`, ~50 packets/s). (A private node IP
needs `turn.allow_restricted_peer_cidrs`; production's node IP is public, so the shipped config does not.)

## UDP on 103.195.238.178 (read-only checks, 07/10)

* ufw: default deny incoming; only 22, 80, 443/tcp allowed. nftables/iptables are ufw's own rules.
* **Inbound UDP is dropped before it reaches the server.** A passive `tcpdump` on eth0 while the operator's Mac sent
  UDP to ports 3478, 7882, 443, 50123 and 123: **0 packets** arrived. A TCP SYN to port 50124 sent in the same minute
  **did** arrive (10 retries seen). The ufw log shows ~8.9 k blocked TCP probes from the internet in 2 days and **0
  UDP** to the server's address, which fits a provider filter.
* **Outbound UDP is dropped too**, except DNS: STUN to `stun.l.google.com:19302`, `stun.l.google.com:3478` and
  `stun.cloudflare.com:3478` all timed out; DNS to 8.8.8.8 works; NTP (UDP 123) is known blocked (HANDOFF §6).
* nginx 1.24 is built with `--with-stream=dynamic --with-stream_ssl_preread_module`; the module package
  `libnginx-mod-stream` is not installed (`apt install libnginx-mod-stream`, stage 2 only).
* The server has no global IPv6 address. No DNS name `rtc.`/`turn.phocochuyen.io.vn` exists yet.

So the media path must be TCP:

1. **Stage 1 — ICE over TCP on port 7881** (`ufw allow 7881/tcp`). Every current browser does ICE/TCP; most home
   Wi-Fi and 4G allow an outbound TCP port like 7881. Signal over the existing site: `wss://phocochuyen.io.vn/sfu`
   (nginx `location /sfu/`, no new certificate, no new DNS name, the page's CSP already allows its own wss origin).
2. **Stage 2 (optional) — TURN over TLS on 443** for networks that allow only 443 (school/office Wi-Fi). LiveKit always
   advertises `turns:<turn.domain>:443` (`pkg/service/roommanager.go`), so 443 must be shared with the website:
   nginx `stream` reads the SNI without terminating it and sends `turn.phocochuyen.io.vn` to LiveKit's TURN, everything
   else to the website, which moves to `127.0.0.1:8443` with the PROXY protocol (real client IPs kept for
   `limit_req`, fail2ban and the logs). Needs a DNS A record and a certificate for `turn.phocochuyen.io.vn`.
3. **If InterDigi opens UDP** (ask with the NTP request): `ufw allow 7882/udp` and nothing else; clients prefer UDP
   by themselves (lower latency). Ask for inbound UDP 7882 and outbound UDP in general.

## Resources and bandwidth

Measured on the Mac (Apple M-series), LiveKit 1.13.7, one singer and N listeners in one room, ICE/TCP only,
Opus "music" preset (48 kbps cap, mono, no DTX, no RED — RED would double the bytes and buys nothing over TCP):

| Listeners | LiveKit CPU (one core) | LiveKit RSS | Payload per listener |
|---|---|---|---|
| 0 (idle) | 0 % | 45 MB | — |
| 20 | 2.5 % (max 2.9 %) | 137 MB | 36.5 kbps (fake beep; singing ~40–48 kbps) |
| 30 | 4.3 % (max 4.9 %) | 164 MB | 36.5 kbps |

Per room on this server (Xeon 8163 cores are slower: count ~2×):

* **CPU**: ~10 % of one core for a full room (30 listeners); 12 full rooms (3 themes × 4) ≈ 1.2 cores. The unit allows
  2 (`CPUQuota=200%`). TURN/TLS adds nginx TLS work for the clients that need it.
* **RAM**: ~45 MB + ~4 MB per listener → ~170 MB per full room; `MemoryMax=1G` covers ~6 full rooms at once with
  margin (the real number of rooms with a live mic at the same time will be far lower).
* **Bandwidth**: per listener ~48 kbps payload + RTP/SRTP/TCP/IP overhead (~64 B × 50 packets/s ≈ 26 kbps) ≈
  **75 kbps** (≈ 85 kbps via TURN/TLS). A full room: **~2.3 Mbps out**, 75 kbps in. Per hour of mic in a full room:
  **~1 GB out**. A busy evening (3 rooms × 15 listeners × 3 h of mic) ≈ 3.6 GB.
* **Latency**: Opus 20 ms frames + jitter buffer + one TCP hop each way: ~150–400 ms on 4G (within the 0.3–1 s
  target). TCP adds head-of-line stalls on a lossy line (a short gap, then catch-up).
* **Ports**: 7881/tcp public; 7880 (127.0.0.1 only), 7882/udp (closed by ufw until UDP is open), 5349 (stage 2,
  localhost from nginx), TURN relays 30000–30200 (local only).

## Install (off-peak, never 17:30–20:00)

```bash
cd /opt/mot-ngay-lam-nghe/current        # a release that has this code (karaoke-mic)
bash deploy/livekit/install.sh check     # read-only
bash deploy/livekit/install.sh stage1    # binary 1.13.8 (sha256 checked), user, config, keys, unit, ufw 7881/tcp, nginx /sfu/, env
bash deploy/livekit/install.sh smoke     # /sfu/ answers "OK"; create/list/delete a room with the live service's code
```

Stage 1 changes, and how to undo each: `/usr/local/bin/livekit-server` (rm), `/etc/livekit` (rm -r), user `livekit`
(userdel), `mnl-livekit.service` (`install.sh off`, rm), ufw rule (`ufw delete allow 7881/tcp`), nginx (the
`include snippets/mnl-sfu.conf;` line; a backup `phocochuyen.bak-kmic-<time>` is made), `kara-mic.env` and two
`zz-kara-mic.conf` drop-ins (rm + daemon-reload). The game and the live service are not restarted by the script.

## Turn it on

1. The release with this code is live (the switch is 0: the game behaves exactly as 1.9.11).
2. `install.sh stage1` + `smoke` passed.
3. `sed -i 's/^LIVE_KARAOKE_MIC=0/LIVE_KARAOKE_MIC=1/' /etc/mot-ngay-lam-nghe/kara-mic.env`
4. `systemctl restart mnl-live` (clients reconnect by themselves) and restart the game server so its headers allow
   the mic (`Permissions-Policy: microphone=(self)`, the SDK in `script-src`): the rolling release script, or a plain
   restart off-peak. Until both run with the switch, players see no 🎙️ (the live service decides) or get a
   permission error (the game server decides): turn both on, or both off.
5. Check: `curl -sI https://phocochuyen.io.vn/ | grep -i permissions-policy` shows `microphone=(self)`;
   `curl -s 127.0.0.1:8770/live/health` shows `"kara_mic": true`; in a room, the singer sees **🎙️ Mic**.

Off again: set it back to 0 and restart both. `install.sh off` stops LiveKit itself.

## Stage 2: TURN/TLS on 443 (optional, after stage 1 runs well)

1. DNS (zonedns): `turn.phocochuyen.io.vn  A  103.195.238.178`.
2. `bash deploy/livekit/install.sh stage2`: `apt install libnginx-mod-stream`, a certificate for the turn name
   (`certbot certonly --nginx`), `/etc/nginx/mnl-stream.conf`, the site's 443 listen lines → `127.0.0.1:8443 ssl http2
   proxy_protocol` + `real_ip_header proxy_protocol`, `nginx -t` (restored on failure), **`systemctl restart nginx`
   (a ~1 s gap for every player: do it off-peak)**, `turn.enabled: true`, restart LiveKit.
3. Check: the site loads, `/api/health` from outside, `tail /var/log/nginx/phocochuyen_api.log` shows real client
   IPs (not 127.0.0.1), `fail2ban-client status nginx-limit-req` still counts.
4. Undo: restore `sites-enabled/phocochuyen.bak-kmic-*` and `nginx.conf.bak-kmic-*`, `rm /etc/nginx/mnl-stream.conf`,
   `turn.enabled: false`, restart nginx and LiveKit.

Note: certbot's own edits of the site (`# managed by Certbot` lines) — after stage 2, a `certbot --nginx` run for the
main domain may try to add `listen 443` back. Renewals (`certbot renew`) do not edit the file.

## Safety (what the code enforces, for the reviewer)

* Only the singer on stage gets a **publish** token: microphone only, no data, no metadata, no subscribing, valid
  until the mic's 6-minute end. Listeners get **subscribe-only, hidden** tokens valid 60 s to join.
* One SFU room per mic session (`kara-<room>.<song hash>.<n>`), created by the live service before any token
  (`room.auto_create: false`) and **deleted** to cut the mic: the singer and every listener are disconnected at once
  and no old token can rejoin. Cuts: song end / skip / vote-skip / admin skip, kick, chat mute, the singer leaving,
  the room closing, 6 minutes, the singer's own ⏹ Tắt mic, an admin (in the room: ⋯ › 🔇 Cắt mic; admin site:
  Phòng hát › 🎙️ Cắt mic), or 3 distinct reports of the live singer.
* Birth year asked once (`account_birth`, its own table: a rollback never sees it); counted as the youngest the player
  can be; under 16 → listening only. Accounts younger than 1 day cannot sing live (ban evasion).
* Blocks either way: no listening token; a block during the song removes that listener from the SFU within 1 s.
* No recording anywhere: no Egress service, no `recorder`/`roomRecord` grant, no MediaRecorder in the page. The heavy-
  words filter cannot apply to audio; moderation is cut-mic, report (🚩 Báo cáo giọng hát: rude / 🛟 minor / other,
  shown to admins as "🎙️ lúc hát mic trực tiếp"), mute and ban.

## Known limits

* **Voice vs video**: listeners hear the singer ~0.2–0.5 s after the singer's own video position (the sync of the
  video is unchanged on purpose). A later option: listeners delay their video by a measured lag while a mic is live.
* **Echo**: on a phone speaker the singer's mic also picks up the YouTube music; echo cancellation removes only part of
  it on Android. The note before the first mic, and the live banner, say to wear headphones.
* **A modified client** that a block (made mid-song) removed from the SFU could rejoin with the token LiveKit refreshes
  for connected participants, until that mic session ends (≤ 6 min). New sessions and blocks made before the mic are
  never affected. Stock clients obey.
* LiveKit's browser SDK asks Google's public STUN servers for a reflexive address (harmless here; no media goes there).
* Not tested on real phones yet (iPhone Safari autoplay → "🔈 Chạm để nghe giọng", Bluetooth headsets switching to
  the call profile while the mic is open). Test on a staging copy (`PUSH_DISABLED=1`) with 2–3 phones before turning
  the switch on for everyone.
