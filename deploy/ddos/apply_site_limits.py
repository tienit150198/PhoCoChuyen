p = "/etc/nginx/sites-enabled/phocochuyen"; s = open(p).read()
assert "mnl_api" not in s, "already applied"
def add(anchor, lines):
    global s
    assert s.count(anchor) == 1, anchor
    s = s.replace(anchor, anchor + "\n" + "\n".join("        " + l for l in lines))
add("    location ~ ^/(js|css|i18n|icons|music)/ {", ["limit_req zone=mnl_static burst=600 nodelay;"])
add("    location ^~ /fonts/ {", ["limit_req zone=mnl_static burst=600 nodelay;"])
add("    location = /live {", ["limit_req zone=mnl_live burst=10 nodelay;", "limit_conn mnl_liveconn 30;"])
add("    location /api/ {", ["limit_req zone=mnl_api burst=60 nodelay;"])
add("    location / {", ["limit_req zone=mnl_api burst=60 nodelay;"])
proxy = """        access_log /var/log/nginx/phocochuyen_api.log pcc_timing;
        access_log /var/log/nginx/access.log;
        proxy_pass http://phocochuyen_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
"""
extra = ("    location ~ ^/api/account/(login|register)$ {\n        limit_req zone=mnl_auth burst=10 nodelay;\n        limit_req zone=mnl_api burst=60 nodelay;\n" + proxy +
         "    location = /api/bootstrap {\n        limit_req zone=mnl_boot burst=30 nodelay;\n" + proxy + "\n")
anchor = "    location /api/ {"
s = s.replace(anchor, extra + anchor, 1)
srv = "    server_name phocochuyen.io.vn www.phocochuyen.io.vn;\n    client_max_body_size 16m;"
assert s.count(srv) == 1
s = s.replace(srv, srv + "\n    limit_conn mnl_conn 150;")
open(p, "w").write(s)
print("site updated")
