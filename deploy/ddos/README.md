# Request limits and anti-flood (installed on the production server 01/10/2026)

Generous per-address limits (Vietnamese carriers share addresses). Measured before setting them: API peak
12 req/s per address, a cold load about 170 static files in one second.

| File | Installed as |
|---|---|
| `nginx-mnl-ddos.conf` | `/etc/nginx/conf.d/mnl-ddos.conf` (zones, 429, slow-client timeouts) |
| `apply_site_limits.py` | run once against `/etc/nginx/sites-enabled/phocochuyen` (adds `limit_req` / `limit_conn` per location: API 20 r/s burst 60, login/register 10 r/min, bootstrap 5 r/s burst 30, static 300 r/s burst 600, `/live` 2 new sockets/s and 30 sockets, 150 connections per address) |
| `fail2ban-mnl-nginx.local` | `/etc/fail2ban/jail.d/mnl-nginx.local` (30 limit hits in 60 s → 15 min ban; never the old server or localhost) |
| `sysctl-90-mnl-ddos.conf` | `/etc/sysctl.d/90-mnl-ddos.conf` (accept queues, SYN cookies) |

Check: `grep -c limiting /var/log/nginx/error.log`, `fail2ban-client status nginx-limit-req`, and 429s in
`/var/log/nginx/phocochuyen_api.log`. A burst of 200 `/api/health` from localhost gave 120 × 200 and 80 × 429.

Volumetric attacks (bandwidth floods) need protection in front of the server, e.g. Cloudflare (free plan, proxies
WebSockets): the owner would move the DNS to Cloudflare and nginx would trust its addresses for the real IP.
