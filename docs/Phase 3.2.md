Task 3.2 — Slow query analyzer
Step 1 — Enable pg_stat_statements first 
Find your config file:
sudo find / -name "postgresql.conf" 2>/dev/null
Open it:
sudo nano /etc/postgresql/15/main/postgresql.conf
Find and change these two lines (use Ctrl+W to search):
shared_preload_libraries = 'pg_stat_statements'
log_min_duration_statement = 1000
Save (Ctrl+O, Enter, Ctrl+X) then restart:
sudo systemctl restart postgresql

Step 2 — Enable the extension in your database:
sudo -u postgres psql -p 5432 -d appdb
sqlCREATE EXTENSION IF NOT EXISTS pg_stat_statements;
\q

Step 3 — Add Task 3.2 to your app.py
Open your file:
nano ~/flask_dashboard/app.py
Add these two new routes at the bottom, just before if __name__ == "__main__":+
##CODE
@app.route("/slowqueries")
def slow_queries():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Top slow queries by average time
            cur.execute("""
                SELECT
                    left(query, 100),
                    calls,
                    round(total_exec_time::numeric, 2) AS total_ms,
                    round(mean_exec_time::numeric, 2) AS avg_ms,
                    round(stddev_exec_time::numeric, 2) AS stddev_ms,
                    rows
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat%'
                ORDER BY mean_exec_time DESC
                LIMIT 15;
            """)
            slow = cur.fetchall()

            # Most executed queries
            cur.execute("""
                SELECT
                    left(query, 100),
                    calls,
                    round(total_exec_time::numeric, 2) AS total_ms,
                    round(mean_exec_time::numeric, 2) AS avg_ms,
                    rows
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat%'
                ORDER BY calls DESC
                LIMIT 15;
            """)
            most_called = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("slowqueries.html",
                           slow=slow,
                           most_called=most_called)


@app.route("/explain", methods=["POST"])
def explain():
    from flask import request
    query = request.form.get("query", "")
    result = ""
    error = ""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("EXPLAIN ANALYZE " + query)
            rows = cur.fetchall()
            result = "\n".join(row[0] for row in rows)
    except Exception as e:
        error = str(e)
        conn.rollback()
    finally:
        release_conn(conn)
    return render_template("slowqueries.html",
                           slow=[],
                           most_called=[],
                           explain_result=result,
                           explain_error=error,
                           explain_query=query)
Make html file
Step 4 — Create the new template file
nano ~/flask_dashboard/templates/slowqueries.html

Step 5 — Add a link to Task 3.2 in your main dashboard
Open templates/index.html:
nano ~/flask_dashboard/templates/index.html
Find the topbar section and add this link next to the Live badge:
html<a href="/slowqueries" class="nav-btn" style="background:#334155; color:#94a3b8; border:1px solid #475569; border-radius:8px; padding:6px 14px; font-size:12px; text-decoration:none;">
  Slow Query Analyzer
</a>

Step 6 — Run and test
python3 app.py
Then open browser and go to:
http://127.0.0.1:5000/slowqueries
