#!/usr/bin/env bash
# 🎙️ LiveKit (the SFU of Phòng hát mic trực tiếp) on the production server. Read deploy/livekit/README.md first.
# Run as root from the release directory (e.g. /opt/mot-ngay-lam-nghe/current), off-peak (not 17:30-20:00):
#
#   bash deploy/livekit/install.sh check     # read-only: what is there, what would change
#   bash deploy/livekit/install.sh stage1    # LiveKit + nginx /sfu/ + ufw 7881/tcp + the env for the two services
#   bash deploy/livekit/install.sh smoke     # the SFU answers through nginx; a room can be created and deleted
#   bash deploy/livekit/install.sh stage2    # optional: TURN/TLS on 443 (needs DNS turn.phocochuyen.io.vn first)
#   bash deploy/livekit/install.sh off       # stop it (the game keeps working; the mic switch should be 0 first)
#
# It never turns the mic on for players: that stays LIVE_KARAOKE_MIC=1 in /etc/mot-ngay-lam-nghe/kara-mic.env, then
# `systemctl restart mnl-live` and a restart of the game (README "Turn it on"). Every file it changes is backed up
# to <file>.bak-kmic-<time> first; nginx is tested before each reload and restored when the test fails.
set -euo pipefail

VERSION=1.13.8
TARBALL=livekit_${VERSION}_linux_amd64.tar.gz
SHA256=059f6de65da11a57400e4646027da705d592ce42acb48c08570a397df446f869
URL=https://github.com/livekit/livekit/releases/download/v${VERSION}/${TARBALL}
HERE=$(cd "$(dirname "$0")" && pwd)
SITE=/etc/nginx/sites-enabled/phocochuyen
ENVF=/etc/mot-ngay-lam-nghe/kara-mic.env
STAMP=$(date +%Y%m%d%H%M%S)
PUBLIC_URL=wss://phocochuyen.io.vn/sfu

say() { printf '\n== %s\n' "$*"; }
backup() { [ -e "$1" ] && cp -a "$1" "$1.bak-kmic-$STAMP" && echo "   backup: $1.bak-kmic-$STAMP" || true; }
need_root() { [ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }; }
nginx_safe_reload() {   # $1: the backup to restore if the test fails
    if nginx -t; then systemctl reload nginx; else echo "!! nginx -t failed: restoring $1"; [ -n "${1:-}" ] && cp -a "$1.bak-kmic-$STAMP" "$1"; nginx -t && systemctl reload nginx; exit 1; fi
}

check() {
    say "LiveKit binary";        ls -l /usr/local/bin/livekit-server 2>/dev/null && /usr/local/bin/livekit-server --version || echo "   not installed"
    say "service";               systemctl is-active mnl-livekit 2>/dev/null || true
    say "config";                ls -l /etc/livekit 2>/dev/null || echo "   none"
    say "ufw";                   ufw status | grep -E '7881|7882|5349' || echo "   no SFU rule yet (stage1 adds 7881/tcp)"
    say "nginx /sfu/";           grep -n 'mnl-sfu.conf' "$SITE" || echo "   not included yet"
    say "nginx stream";          ls /etc/nginx/modules-enabled/ | grep -i stream || echo "   libnginx-mod-stream not installed (stage2 only)"
    say "env";                   [ -f "$ENVF" ] && sed -E 's/(SECRET=).*/\1…/' "$ENVF" || echo "   $ENVF not written yet"
    say "DNS turn.phocochuyen.io.vn (stage2)"; getent hosts turn.phocochuyen.io.vn || echo "   no A record yet"
    say "listening";             ss -ltnup | grep -E ':(7880|7881|7882|5349|5350|8443)\b' || echo "   nothing on the SFU ports"
}

stage1() {
    need_root
    say "1/7 the binary ($VERSION, sha256 checked)"
    if ! /usr/local/bin/livekit-server --version 2>/dev/null | grep -q "$VERSION"; then
        tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
        curl -fsSL -o "$tmp/$TARBALL" "$URL"
        echo "$SHA256  $tmp/$TARBALL" | sha256sum -c -
        tar -xzf "$tmp/$TARBALL" -C "$tmp" livekit-server
        install -m 0755 -o root -g root "$tmp/livekit-server" /usr/local/bin/livekit-server
    fi
    /usr/local/bin/livekit-server --version

    say "2/7 user and config"
    id livekit >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin livekit
    install -d -m 0750 -o root -g livekit /etc/livekit
    [ -f /etc/livekit/livekit.yaml ] && backup /etc/livekit/livekit.yaml
    install -m 0640 -o root -g livekit "$HERE/livekit.yaml" /etc/livekit/livekit.yaml
    if [ ! -s /etc/livekit/keys.yaml ]; then
        key="API$(head -c 9 /dev/urandom | od -An -tx1 | tr -d ' \n')"
        secret="$(head -c 32 /dev/urandom | base64 | tr -d '/+=\n' | head -c 43)"
        umask 077; printf '%s: %s\n' "$key" "$secret" > /etc/livekit/keys.yaml
        chown livekit:livekit /etc/livekit/keys.yaml; chmod 0600 /etc/livekit/keys.yaml
        echo "   new key pair: $key"
    fi

    say "3/7 systemd unit"
    install -m 0644 "$HERE/mnl-livekit.service" /etc/systemd/system/mnl-livekit.service
    systemctl daemon-reload
    systemctl enable --now mnl-livekit
    sleep 2; systemctl is-active mnl-livekit
    curl -fsS http://127.0.0.1:7880/ && echo "   (LiveKit answers on 127.0.0.1:7880)"

    say "4/7 firewall: ICE over TCP (the media; the provider drops UDP)"
    ufw allow 7881/tcp comment 'livekit ice-tcp (karaoke mic)'

    say "5/7 nginx: wss://phocochuyen.io.vn/sfu → 127.0.0.1:7880"
    install -m 0644 "$HERE/nginx-sfu.conf" /etc/nginx/snippets/mnl-sfu.conf
    if ! grep -q 'snippets/mnl-sfu.conf' "$SITE"; then
        backup "$SITE"
        # inside the 443 server block, just before its certbot-managed listen lines
        python3 - "$SITE" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
mark = '    listen [::]:443 ssl http2 ipv6only=on; # managed by Certbot'
if mark not in s:
    mark = '    listen 443 ssl http2; # managed by Certbot'
assert s.count(mark) == 1, 'the 443 listen line was not found once: add `include snippets/mnl-sfu.conf;` by hand'
s = s.replace(mark, '    # 🎙️ Phòng hát mic trực tiếp: the SFU signal (deploy/livekit/nginx-sfu.conf)\n    include snippets/mnl-sfu.conf;\n\n' + mark)
open(p, 'w').write(s)
PY
        nginx_safe_reload "$SITE"
    fi
    curl -fsS https://phocochuyen.io.vn/sfu/ && echo "   (through nginx: OK)"

    say "6/7 the env of the two services (the mic switch stays 0)"
    key=$(cut -d: -f1 /etc/livekit/keys.yaml); secret=$(cut -d' ' -f2 /etc/livekit/keys.yaml)
    [ -f "$ENVF" ] && backup "$ENVF"
    cur=$(grep -s '^LIVE_KARAOKE_MIC=' "$ENVF" || echo 'LIVE_KARAOKE_MIC=0')
    umask 077
    printf '%s\n' "# 🎙️ Phòng hát mic trực tiếp (deploy/livekit/README.md). The switch: 1 = on (both services must restart)." \
        "$cur" "LIVEKIT_URL=$PUBLIC_URL" "LIVEKIT_API_URL=http://127.0.0.1:7880" "LIVEKIT_API_KEY=$key" "LIVEKIT_API_SECRET=$secret" > "$ENVF"
    chmod 0600 "$ENVF"
    for unit in mnl-live mot-ngay-lam-nghe; do
        install -d /etc/systemd/system/$unit.service.d
        printf '[Service]\nEnvironmentFile=-%s\n' "$ENVF" > /etc/systemd/system/$unit.service.d/zz-kara-mic.conf
    done
    systemctl daemon-reload
    echo "   written: $ENVF and the zz-kara-mic.conf drop-ins (they apply at the next restart of each service)"

    say "7/7 done. Next: bash $0 smoke; then README \"Turn it on\"."
}

smoke() {
    say "signal through nginx";   curl -fsS https://phocochuyen.io.vn/sfu/; echo
    say "server API (create → list → delete a test room) with the live service's own code"
    set -a; . "$ENVF"; set +a
    cd "$(dirname "$HERE")/.." && PYTHONPATH=/opt/mot-ngay-lam-nghe/shared/pyvendor python3 - <<'PY'
import asyncio, os
from live.sfu import Sfu
async def main():
    s = Sfu(os.environ['LIVEKIT_URL'], os.environ['LIVEKIT_API_URL'], os.environ['LIVEKIT_API_KEY'], os.environ['LIVEKIT_API_SECRET'])
    assert await s.create_room('kara-smoke.0.1', 5), 'CreateRoom failed'
    names = await s.rooms()
    assert 'kara-smoke.0.1' in names, names
    assert await s.delete_room('kara-smoke.0.1')
    print('   OK: create, list, delete')
asyncio.run(main())
PY
    say "ICE/TCP port open"; ss -ltn | grep -q ':7881 ' && echo "   7881/tcp listening" || echo "!! 7881/tcp not listening"
}

stage2() {
    need_root
    getent hosts turn.phocochuyen.io.vn >/dev/null || { echo "!! add the DNS A record turn.phocochuyen.io.vn → 103.195.238.178 first"; exit 1; }
    say "1/5 nginx stream module"
    apt-get install -y libnginx-mod-stream
    say "2/5 certificate for turn.phocochuyen.io.vn"
    [ -d /etc/letsencrypt/live/turn.phocochuyen.io.vn ] || certbot certonly --nginx -d turn.phocochuyen.io.vn --deploy-hook 'systemctl reload nginx'
    say "3/5 nginx: SNI on 443 (the game site moves to 127.0.0.1:8443 with the PROXY protocol)"
    backup "$SITE"; backup /etc/nginx/nginx.conf
    install -m 0644 "$HERE/nginx-stream-443.conf" /etc/nginx/mnl-stream.conf
    grep -q 'mnl-stream.conf' /etc/nginx/nginx.conf || sed -i 's#^include /etc/nginx/modules-enabled/\*.conf;#&\ninclude /etc/nginx/mnl-stream.conf;#' /etc/nginx/nginx.conf
    python3 - "$SITE" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
if '127.0.0.1:8443' not in s:
    a = '    listen [::]:443 ssl http2 ipv6only=on; # managed by Certbot\n'
    b = '    listen 443 ssl http2; # managed by Certbot\n'
    assert s.count(a) == 1 and s.count(b) == 1, 'listen lines not found: edit by hand (nginx-stream-443.conf header)'
    s = s.replace(a, '').replace(b, '    listen 127.0.0.1:8443 ssl http2 proxy_protocol; # 🎙️ behind the stream SNI router on :443 (deploy/livekit)\n'
                  '    set_real_ip_from 127.0.0.1;\n    real_ip_header proxy_protocol;\n')
    open(p, 'w').write(s)
PY
    if ! nginx -t; then
        echo "!! nginx -t failed: restoring"; cp -a "$SITE.bak-kmic-$STAMP" "$SITE"; cp -a /etc/nginx/nginx.conf.bak-kmic-$STAMP /etc/nginx/nginx.conf; rm -f /etc/nginx/mnl-stream.conf; nginx -t; exit 1
    fi
    systemctl restart nginx   # a listen socket moves from http to stream: reload is not enough (a ~1 s gap)
    curl -fsS -o /dev/null -w '   game site through the SNI router: %{http_code}\n' https://phocochuyen.io.vn/
    say "4/5 LiveKit: TURN on"
    backup /etc/livekit/livekit.yaml
    python3 - <<'PY'
p = '/etc/livekit/livekit.yaml'; s = open(p).read()
s = s.replace('turn:\n  enabled: false', 'turn:\n  enabled: true', 1)
open(p, 'w').write(s)
PY
    systemctl restart mnl-livekit; sleep 2; systemctl is-active mnl-livekit
    say "5/5 TLS for TURN answers on 443"
    timeout 5 openssl s_client -connect 103.195.238.178:443 -servername turn.phocochuyen.io.vn </dev/null 2>/dev/null | grep -E 'subject=|Verify return code' || true
}

off() {
    need_root
    systemctl disable --now mnl-livekit || true
    echo "   LiveKit stopped. The mic switch: set LIVE_KARAOKE_MIC=0 in $ENVF and restart mnl-live (players then see no 🎙️)."
    echo "   ufw rule kept (ufw delete allow 7881/tcp to remove); nginx /sfu/ answers 502 until it runs again."
}

case "${1:-check}" in
    check) check ;;
    stage1) stage1 ;;
    smoke) smoke ;;
    stage2) stage2 ;;
    off) off ;;
    *) echo "usage: $0 check|stage1|smoke|stage2|off"; exit 2 ;;
esac
