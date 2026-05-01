Overview
Phase 4 covers two core DBA tasks focused on reducing query latency and preventing performance degradation in PostgreSQL databases. Both tasks were implemented as web-based tools integrated into the existing Flask monitoring dashboard built in Phase 3.

Task 4.1 — Index & Table Optimization Tool
Objective
Reduce query latency by identifying missing, unused, and duplicate indexes in the PostgreSQL database.
What is an Index?
An index is a data structure that allows PostgreSQL to find rows quickly without scanning the entire table. Without indexes, PostgreSQL performs a Sequential Scan — reading every row one by one. With an index, it performs an Index Scan — jumping directly to the relevant rows.
Index = that catalog for your database.

##Step 1
nano ~/flask_dashboard/app.py
Add before if __name__ == "__main__":
##CODE
@app.route("/indexes")
def indexes():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Unused indexes
            cur.execute("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    idx_scan AS times_used
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                ORDER BY pg_relation_size(indexrelid) DESC;
            """)
            unused = cur.fetchall()

            # All indexes with usage
            cur.execute("""
                SELECT
                    t.tablename,
                    i.indexname,
                    pg_size_pretty(pg_relation_size(i.indexrelid)) AS size,
                    s.idx_scan AS times_used,
                    s.idx_tup_read AS tuples_read
                FROM pg_indexes i
                JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
                JOIN pg_stat_user_tables t ON t.tablename = s.relname
                ORDER BY s.idx_scan DESC
                LIMIT 20;
            """)
            all_indexes = cur.fetchall()

            # Missing indexes — tables with high seq scans and no index scans
            cur.execute("""
                SELECT
                    relname AS tablename,
                    seq_scan,
                    idx_scan,
                    pg_size_pretty(pg_total_relation_size(relid)) AS table_size,
                    n_live_tup AS live_rows
                FROM pg_stat_user_tables
                WHERE seq_scan > 50
                  AND (idx_scan IS NULL OR idx_scan < seq_scan)
                ORDER BY seq_scan DESC
                LIMIT 10;
            """)
            missing = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("indexes.html",
                           unused=unused,
                           all_indexes=all_indexes,
                           missing=missing)


@app.route("/vacuum")
def vacuum():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Dead tuples per table
            cur.execute("""
                SELECT
                    relname AS tablename,
                    n_dead_tup AS dead_tuples,
                    n_live_tup AS live_tuples,
                    pg_size_pretty(pg_total_relation_size(relid)) AS size,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_dead_tup DESC
                LIMIT 15;
            """)
            bloat = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("vacuum.html", bloat=bloat)


@app.route("/run_vacuum/<tablename>")
def run_vacuum(tablename):
    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"VACUUM ANALYZE {tablename};")
        conn.autocommit = False
    finally:
        release_conn(conn)
    return redirect(url_for("vacuum"))

    @app.route("/indexes")
def indexes():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Unused indexes
            cur.execute("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    idx_scan AS times_used
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                ORDER BY pg_relation_size(indexrelid) DESC;
            """)
            unused = cur.fetchall()

            # All indexes with usage
            cur.execute("""
                SELECT
                    t.tablename,
                    i.indexname,
                    pg_size_pretty(pg_relation_size(i.indexrelid)) AS size,
                    s.idx_scan AS times_used,
                    s.idx_tup_read AS tuples_read
                FROM pg_indexes i
                JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
                JOIN pg_stat_user_tables t ON t.tablename = s.relname
                ORDER BY s.idx_scan DESC
                LIMIT 20;
            """)
            all_indexes = cur.fetchall()

            # Missing indexes — tables with high seq scans and no index scans
            cur.execute("""
                SELECT
                    relname AS tablename,
                    seq_scan,
                    idx_scan,
                    pg_size_pretty(pg_total_relation_size(relid)) AS table_size,
                    n_live_tup AS live_rows
                FROM pg_stat_user_tables
                WHERE seq_scan > 50
                  AND (idx_scan IS NULL OR idx_scan < seq_scan)
                ORDER BY seq_scan DESC
                LIMIT 10;
            """)
            missing = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("indexes.html",
                           unused=unused,
                           all_indexes=all_indexes,
                           missing=missing)


@app.route("/vacuum")
def vacuum():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Dead tuples per table
            cur.execute("""
                SELECT
                    relname AS tablename,
                    n_dead_tup AS dead_tuples,
                    n_live_tup AS live_tuples,
                    pg_size_pretty(pg_total_relation_size(relid)) AS size,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_dead_tup DESC
                LIMIT 15;
            """)
            bloat = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("vacuum.html", bloat=bloat)


@app.route("/run_vacuum/<tablename>")
def run_vacuum(tablename):
    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"VACUUM ANALYZE {tablename};")
        conn.autocommit = False
    finally:
        release_conn(conn)
    return redirect(url_for("vacuum"))

Step 2 — Create indexes.html
nano ~/flask_dashboard/templates/indexes.html

Task 4.2
What is Vacuum?
When you DELETE or UPDATE a row in PostgreSQL, the old row is not immediately removed. It stays as a dead tuple — like a ghost row taking up space.
Over time thousands of dead tuples pile up → database gets slow and bloated.
VACUUM = cleaning up those ghost rows.

Step 3 — Create vacuum.html
nano ~/flask_dashboard/templates/vacuum.html

Step 4 — Add navigation links in index.html
Find your topbar links section and add these two new buttons:
<a href="/indexes" class="nav-btn" style="background:#334155; color:#94a3b8; border:1px solid #475569; border-radius:8px; padding:6px 14px; font-size:12px; text-decoration:none;">
  Index Optimizer
</a>
<a href="/vacuum" class="nav-btn" style="background:#334155; color:#94a3b8; border:1px solid #475569; border-radius:8px; padding:6px 14px; font-size:12px; text-decoration:none;">
  Vacuum Manager
</a>

Step 5 — Run and test
python3 app.py
