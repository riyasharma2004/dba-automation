Task 3.1 — PostgreSQL monitoring dashboard
Active vs idle connections
Done — showing active_count and idle_count as metric cards
Long-running queries
Done — queries over 1 min shown with PID, user, duration, kill button
Locks and blocking queries
Done — pg_locks JOIN pg_stat_activity showing blocker and blocked PIDs
DB size growth
Done — all databases listed with sizes from pg_database
Table size ranking
Done — top 10 tables by size from pg_stat_user_tables
Auto-kill query over N minutes
Done — /kill/<pid> route uses pg_terminate_backend(), threshold set to 10 min
All 4 required views used
pg_stat_activity · pg_locks · pg_database · pg_stat_user_tables
Steps --
*Flask web dashboard
*PostgreSQL monitoring
*Runs on Ubuntu (VM/WSL)
*Clean UI

🔵STEP 1 — OPEN TERMINAL
 Open Ubuntu terminal

🔵 STEP 2 — INSTALL REQUIRED PACKAGES
sudo apt update
sudo apt install python3-pip -y
pip3 install flask psycopg2-binary

🔵 STEP 3 — CREATE PROJECT FOLDER
mkdir flask_dashboard
cd flask_dashboard

🔵 STEP 4 — CREATE FILES
touch app.py
mkdir templates
touch templates/index.html

🔵 STEP 5 — WRITE BACKEND CODE
📍 Open file:
nano app.py

CODE

import os
from flask import Flask, render_template, redirect, url_for
import psycopg2
from psycopg2 import pool

app = Flask(_name_)

db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 5,
    dbname="appdb",
    user="postgres",
    password="yourpassword",
    host="localhost",
    port="5433"
)

KILL_THRESHOLD_MINUTES = 10
EXCLUDED_ROLES = ["postgres", "replication"]

def get_conn():
    return db_pool.getconn()

def release_conn(conn):
    db_pool.putconn(conn)

@app.route("/")
def dashboard():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            cur.execute("SELECT state, COUNT(*) FROM pg_stat_activity GROUP BY state;")
            conn_rows = cur.fetchall()
            connections = {(row[0] or "unknown"): row[1] for row in conn_rows}
            active_count = connections.get("active", 0)
            idle_count = connections.get("idle", 0)

            cur.execute("""
                SELECT datname, pg_size_pretty(pg_database_size(datname))
                FROM pg_database ORDER BY pg_database_size(datname) DESC;
            """)
            db_size = cur.fetchall()

            cur.execute("""
                SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
            """)
            tables = cur.fetchall()

            cur.execute("""
                SELECT pid, usename,
                       round(extract(epoch from now() - query_start) / 60) AS minutes,
                       left(query, 80)
                FROM pg_stat_activity
                WHERE state = 'active'
                  AND query_start IS NOT NULL
                  AND now() - query_start > interval '1 minute'
                  AND usename != ALL(%s)
                ORDER BY query_start;
            """, (EXCLUDED_ROLES,))
            long_queries = cur.fetchall()

            cur.execute("""
                SELECT blocked.pid,
                       blocked.usename,
                       left(blocked.query, 60),
                       blocking.pid,
                       blocking.usename,
                       round(extract(epoch from now() - blocked.query_start) / 60)
                FROM pg_stat_activity AS blocked
                JOIN pg_locks AS bl ON bl.pid = blocked.pid AND NOT bl.granted
                JOIN pg_locks AS gl ON gl.relation = bl.relation AND gl.granted
                JOIN pg_stat_activity AS blocking ON blocking.pid = gl.pid;
            """)
            locks = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("index.html",
                           active_count=active_count,
                           idle_count=idle_count,
                           db_size=db_size,
                           tables=tables,
                           long_queries=long_queries,
                           locks=locks,
                           kill_threshold=KILL_THRESHOLD_MINUTES)

@app.route("/kill/<int:pid>")
def kill_query(pid):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_terminate_backend(%s);", (pid,))
            conn.commit()
    finally:
        release_conn(conn)
    return redirect(url_for("dashboard"))

if _name_ == "_main_":
    app.run(debug=True)

💾 SAVE FILE
👉 Press:
CTRL + O → Enter
CTRL + X

🔵 STEP 6 — WRITE FRONTEND (UI)
📍 Open file:
nano templates/index.html

CODE 

<!DOCTYPE html>
<html>
<head>
<title>PostgreSQL Monitor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; font-size: 13px; }

.topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding: 14px 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
.topbar-title { font-size: 16px; font-weight: bold; color: #f1f5f9; }
.topbar-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
.badge-live { background: #052e16; color: #4ade80; font-size: 11px; padding: 3px 10px; border-radius: 20px; border: 1px solid #166534; }

.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.mcard { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px; }
.mcard-label { font-size: 11px; color: #64748b; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .05em; }
.mcard-val { font-size: 28px; font-weight: bold; line-height: 1; }
.mcard-sub { font-size: 11px; color: #64748b; margin-top: 6px; }

.green { color: #4ade80; } .amber { color: #fbbf24; } .red { color: #f87171; } .blue { color: #60a5fa; }

.conn-bar-wrap { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px; }
.conn-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 10px 0 8px; }

.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.card-title { font-size: 13px; font-weight: bold; color: #f1f5f9; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
.card-title span { font-size: 11px; color: #64748b; font-weight: normal; }

.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }

table { width: 100%; border-collapse: collapse; }
th { font-size: 11px; color: #64748b; text-align: left; padding: 6px 8px; border-bottom: 1px solid #334155; text-transform: uppercase; letter-spacing: .04em; }
td { font-size: 12px; color: #cbd5e1; padding: 8px; border-bottom: 1px solid #1e3050; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #243044; }

.pill { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: bold; }
.pill-green { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.pill-amber { background: #2d1a00; color: #fbbf24; border: 1px solid #854d0e; }
.pill-red   { background: #2d0000; color: #f87171; border: 1px solid #7f1d1d; }
.pill-blue  { background: #0c1e3d; color: #60a5fa; border: 1px solid #1d4ed8; }
.pill-gray  { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }

.kill-btn { background: #2d0000; color: #f87171; border: 1px solid #7f1d1d; border-radius: 6px; padding: 3px 10px; font-size: 11px; cursor: pointer; }
.kill-btn:hover { background: #450a0a; }

.bar-wrap { display: flex; align-items: center; gap: 8px; }
.bar-bg { flex: 1; height: 6px; background: #0f172a; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; }

.mono { font-family: monospace; font-size: 11px; color: #94a3b8; }
.divider { text-align: center; font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: .08em; margin: 20px 0 12px; display: flex; align-items: center; gap: 10px; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: #334155; }
.footer { text-align: center; font-size: 11px; color: #334155; padding-top: 12px; }
</style>
</head>
<body>

<div class="topbar">
  <div>
    <div class="topbar-title">PostgreSQL Monitor</div>
    <div class="topbar-sub">appdb &nbsp;·&nbsp; localhost:5433 &nbsp;·&nbsp; PostgreSQL 15</div>
  </div>
  <span class="badge-live">● Live</span>
</div>

<!-- Metric cards -->
<div class="metrics">
  <div class="mcard">
    <div class="mcard-label">Active connections</div>
    <div class="mcard-val green">{{ active_count }}</div>
    <div class="mcard-sub">Running queries</div>
  </div>
  <div class="mcard">
    <div class="mcard-label">Idle connections</div>
    <div class="mcard-val blue">{{ idle_count }}</div>
    <div class="mcard-sub">Waiting for work</div>
  </div>
  <div class="mcard">
    <div class="mcard-label">Blocking locks</div>
    <div class="mcard-val amber">{{ locks|length }}</div>
    <div class="mcard-sub">Needs attention</div>
  </div>
  <div class="mcard">
    <div class="mcard-label">Long queries</div>
    <div class="mcard-val red">{{ long_queries|length }}</div>
    <div class="mcard-sub">Over 1 minute</div>
  </div>
</div>

<!-- Long-running queries -->
<div class="divider">Long-running queries</div>
<div class="card">
  <div class="card-title">
    Active queries over threshold
    <span>Source: pg_stat_activity</span>
  </div>
  <table>
    <thead>
      <tr><th>PID</th><th>User</th><th>Duration</th><th>Query</th><th>Action</th></tr>
    </thead>
    <tbody>
      {% for q in long_queries %}
      <tr>
        <td class="mono">{{ q[0] }}</td>
        <td>{{ q[1] }}</td>
        <td>
          {% if q[2] >= 10 %}
            <span class="pill pill-red">{{ q[2] }} min</span>
          {% else %}
            <span class="pill pill-amber">{{ q[2] }} min</span>
          {% endif %}
        </td>
        <td class="mono">{{ q[3] }}...</td>
        <td>
          <a href="/kill/{{ q[0] }}"
             onclick="return confirm('Kill PID {{ q[0] }}?')"
             class="kill-btn" style="text-decoration:none;">Kill</a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="5" style="color:#4ade80;text-align:center;padding:20px">
        No long-running queries
      </td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- Blocking locks -->
<div class="divider">Blocking locks</div>
<div class="card">
  <div class="card-title">
    Lock contention
    <span>Source: pg_locks JOIN pg_stat_activity</span>
  </div>
  <table>
    <thead>
      <tr><th>Blocked PID</th><th>Blocked user</th><th>Blocking PID</th><th>Blocking user</th><th>Wait</th><th>Query</th></tr>
    </thead>
    <tbody>
      {% for l in locks %}
      <tr style="color:#fbbf24">
        <td class="mono">{{ l[0] }}</td>
        <td>{{ l[1] }}</td>
        <td class="mono">{{ l[3] }}</td>
        <td>{{ l[4] }}</td>
        <td><span class="pill pill-red">{{ l[5] }} min</span></td>
        <td class="mono">{{ l[2] }}...</td>
      </tr>
      {% else %}
      <tr><td colspan="6" style="color:#4ade80;text-align:center;padding:20px">
        No blocking locks
      </td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- DB sizes + Table sizes -->
<div class="row2">
  <div class="card">
    <div class="card-title">Database sizes <span>pg_database</span></div>
    <table>
      <thead><tr><th>Database</th><th>Size</th></tr></thead>
      <tbody>
        {% for db in db_size %}
        <tr>
          <td>{{ db[0] }}</td>
          <td class="green">{{ db[1] }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">Top tables by size <span>pg_stat_user_tables</span></div>
    <table>
      <thead><tr><th>#</th><th>Table</th><th>Size</th></tr></thead>
      <tbody>
        {% for t in tables %}
        <tr>
          <td style="color:#64748b">{{ loop.index }}</td>
          <td>{{ t[0] }}</td>
          <td class="blue">{{ t[1] }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<div class="footer">Auto-refresh every 5s &nbsp;·&nbsp; Phase 3 — Task 3.1 &nbsp;·&nbsp; pg_stat_activity · pg_locks · pg_database · pg_stat_user_tables</div>

<script>
  setTimeout(() => { location.reload(); }, 5000);
</script>
</body>
</html>

💾 SAVE

👉 CTRL + O → Enter → CTRL + X

🔵 STEP 7 — RUN YOUR DASHBOARD
python3 app.py

🌐 STEP 8 — OPEN IN BROWSER
👉 Open:
http://127.0.0.1:5000
