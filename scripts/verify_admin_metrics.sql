-- Re-check the "📊 Tổng quan đầu tư" numbers of one Vietnam day straight from the database (docs/ADMIN_METRICS.md).
--
-- PostgreSQL, psql. READ ONLY, every statement under 5 s, every read through an index on a bounded range:
--   psql "$DATABASE_URL" -v day=2026-10-01 -f scripts/verify_admin_metrics.sql
-- (day = a finished Vietnam day; compare with the page, the CSV or stat_kpi_daily printed at the end.)
--
-- Indexes relied on (all created by game/pg_schema.py or game/kpi.py, see the doc's DDL):
--   stat_active      PRIMARY KEY (day, sid)            DAU, WAU, MAU, new players, D1
--   stat_births      stat_births_day (day)             new sessions, cohort of the day
--   accounts         stat_accounts_created (created_at)
--   player_feedback  stat_fb_created (created_at)
--   stat_counters    PRIMARY KEY (day, key)            xu, devices, http, latency, uptime, peaks, AI
--   stat_kpi_daily   PRIMARY KEY (day, key)            the frozen numbers
--   stat_players     stat_players_first (first_day)    first-time players
--   sessions         PRIMARY KEY (sid)                 the "ghost" check of the day's cohort only
-- No statement reads a save (sessions.state) or a whole big table.
--
-- SQLite: the same queries work with ?-parameters in place of :'day' and the date arithmetic done by hand
-- (VN day D = UTC from D-1 17:00:00 to D 17:00:00); there is no statement_timeout, run them on a copy.

\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';

\echo '== day' :day
SELECT :'day' AS day,
       to_char(:'day'::date + 1, 'YYYY-MM-DD') AS next_day,
       to_char(:'day'::date - interval '7 hours', 'YYYY-MM-DD HH24:MI:SS') AS utc_from,
       to_char(:'day'::date + 1 - interval '7 hours', 'YYYY-MM-DD HH24:MI:SS') AS utc_to;

\echo '== DAU (stat_active PK range)'
SELECT COUNT(*) AS dau FROM stat_active WHERE day = :'day';

\echo '== WAU / MAU (stat_active PK range, 7 and 30 days ending that day)'
SELECT (SELECT COUNT(DISTINCT sid) FROM stat_active
         WHERE day BETWEEN to_char(:'day'::date - 6, 'YYYY-MM-DD') AND :'day') AS wau,
       (SELECT COUNT(DISTINCT sid) FROM stat_active
         WHERE day BETWEEN to_char(:'day'::date - 29, 'YYYY-MM-DD') AND :'day') AS mau;

\echo '== new sessions / new players (stat_births_day + stat_active PK)'
SELECT COUNT(*) AS new_sessions,
       SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active a WHERE a.day = b.day AND a.sid = b.sid) THEN 1 ELSE 0 END) AS new_players
  FROM stat_births b WHERE b.day = :'day';

\echo '== D1 of the day cohort (new players of the day active the next day)'
SELECT COUNT(*) AS cohort,
       SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active a WHERE a.day = to_char(:'day'::date + 1, 'YYYY-MM-DD') AND a.sid = b.sid)
                THEN 1 ELSE 0 END) AS back_d1
  FROM stat_births b
 WHERE b.day = :'day' AND EXISTS (SELECT 1 FROM stat_active a WHERE a.day = b.day AND a.sid = b.sid);

\echo '== "ghost" saves among the day births (revision > 0 but never an active day): must not count as players'
SELECT COUNT(*) AS ghosts
  FROM stat_births b JOIN sessions s ON s.sid = b.sid
 WHERE b.day = :'day' AND s.revision > 0
   AND NOT EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid)
   AND NOT EXISTS (SELECT 1 FROM stat_players p WHERE p.sid = b.sid);

\echo '== new accounts (stat_accounts_created, UTC text range of the Vietnam day)'
SELECT COUNT(*) AS new_accounts FROM accounts
 WHERE created_at >= to_char(:'day'::date - interval '7 hours', 'YYYY-MM-DD HH24:MI:SS')
   AND created_at <  to_char(:'day'::date + 1 - interval '7 hours', 'YYYY-MM-DD HH24:MI:SS');

\echo '== first-time players (stat_players_first)'
SELECT COUNT(*) AS first_seen FROM stat_players WHERE first_day = :'day';

\echo '== feedback of the day (stat_fb_created, epoch range of the Vietnam day)'
SELECT kind, COUNT(*) AS notes FROM player_feedback
 WHERE created_at >= extract(epoch FROM (:'day'::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'))
   AND created_at <  extract(epoch FROM ((:'day'::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'))
 GROUP BY kind ORDER BY kind;

\echo '== counters of the day (stat_counters PK range): xu, http, uptime, peaks, AI'
SELECT SUM(n) FILTER (WHERE key LIKE 'xu\_in:%')  AS xu_in,
       SUM(n) FILTER (WHERE key LIKE 'xu\_out:%') AS xu_out,
       SUM(n) FILTER (WHERE key LIKE 'http:%')    AS http_all,
       SUM(n) FILTER (WHERE key = 'http:5xx')     AS http_5xx,
       SUM(n) FILTER (WHERE key LIKE 'cmd\_ms:%') AS timed_commands,
       MAX(n) FILTER (WHERE key = 'up_min')       AS up_minutes,
       MAX(n) FILTER (WHERE key = 'max:online5m') AS peak_online,
       MAX(n) FILTER (WHERE key = 'max:cmd_min')  AS peak_cmd_min,
       SUM(n) FILTER (WHERE key = 'ai:calls')     AS ai_calls
  FROM stat_counters WHERE day = :'day';

\echo '== devices of the day''s new sessions (stat_counters PK range)'
SELECT key, n FROM stat_counters
 WHERE day = :'day' AND (key LIKE 'dev\_%' OR key LIKE 'lang:%') ORDER BY key;

\echo '== the frozen numbers of the day (stat_kpi_daily PK range): should equal the live ones above'
SELECT key, value, to_timestamp(at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS frozen_at
  FROM stat_kpi_daily WHERE day = :'day' ORDER BY key;

ROLLBACK;
