import os
from flask import Flask, render_template, redirect, url_for
import psycopg2
from psycopg2 import pool

app = Flask(__name__)

db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 5,
    dbname="appdb",
    user="postgres",
    password="Riya@123",
    host="127.0.0.1",
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
@app.route("/indexes")
def indexes():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    schemaname,
                    relname,
                    indexrelname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                ORDER BY pg_relation_size(indexrelid) DESC;
            """)
            unused = cur.fetchall()

            cur.execute("""
                SELECT
                    relname AS tablename,
                    indexrelname AS indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
                    idx_scan AS times_used,
                    idx_tup_read AS tuples_read
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
                LIMIT 20;
            """)
            all_indexes = cur.fetchall()

            cur.execute("""
                SELECT
                    relname AS tablename,
                    seq_scan,
                    idx_scan,
                    pg_size_pretty(pg_total_relation_size(relid)) AS table_size,
                    n_live_tup AS live_rows
                FROM pg_stat_user_tables
                WHERE seq_scan > 0
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
@app.route("/security")
def security():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Check superuser count
            cur.execute("""
                SELECT count(*) FROM pg_roles
                WHERE rolsuper = true;
            """)
            superuser_count = cur.fetchone()[0]

            # List all superusers
            cur.execute("""
                SELECT rolname, rolsuper, rolcreatedb, rolcreaterole
                FROM pg_roles
                WHERE rolsuper = true;
            """)
            superusers = cur.fetchall()

            # Check password encryption method
            cur.execute("SHOW password_encryption;")
            pwd_encryption = cur.fetchone()[0]

            # Check SSL status
            cur.execute("SHOW ssl;")
            ssl_status = cur.fetchone()[0]

            # Check all roles and their attributes
            cur.execute("""
                SELECT rolname,
                       rolsuper,
                       rolcreatedb,
                       rolcreaterole,
                       rolcanlogin,
                       rolvaliduntil
                FROM pg_roles
                WHERE rolname NOT LIKE 'pg_%'
                ORDER BY rolsuper DESC, rolname;
            """)
            all_roles = cur.fetchall()

            # Check public schema privileges
            cur.execute("""
                SELECT grantee, privilege_type
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public'
                LIMIT 10;
            """)
            public_grants = cur.fetchall()

            # Check tables with no privileges defined
            cur.execute("""
                SELECT relname, relacl
                FROM pg_class
                WHERE relkind = 'r'
                AND relnamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname = 'public'
                )
                LIMIT 10;
            """)
            table_privs = cur.fetchall()

            # Check roles with no password expiry
            cur.execute("""
                SELECT rolname, rolvaliduntil
                FROM pg_roles
                WHERE rolcanlogin = true
                AND rolvaliduntil IS NULL
                AND rolname NOT LIKE 'pg_%';
            """)
            no_expiry = cur.fetchall()

            # Calculate security score
            score = 100
            issues = []

            if superuser_count > 1:
                score -= 20
                issues.append(("High", f"{superuser_count} superusers found — should be only 1"))

            if ssl_status == "off":
                score -= 25
                issues.append(("Critical", "SSL is disabled — connections are not encrypted"))

            if pwd_encryption != "scram-sha-256":
                score -= 15
                issues.append(("Medium", f"Password encryption is {pwd_encryption} — use scram-sha-256"))

            if len(no_expiry) > 0:
                score -= 10
                issues.append(("Low", f"{len(no_expiry)} roles have no password expiry set"))

            if len(public_grants) > 5:
                score -= 10
                issues.append(("Medium", "Too many public schema grants — review access"))

            if score >= 80:
                risk = "Low"
                risk_color = "green"
            elif score >= 60:
                risk = "Medium"
                risk_color = "amber"
            elif score >= 40:
                risk = "High"
                risk_color = "red"
            else:
                risk = "Critical"
                risk_color = "red"

    finally:
        release_conn(conn)

    return render_template("security.html",
                           superuser_count=superuser_count,
                           superusers=superusers,
                           ssl_status=ssl_status,
                           pwd_encryption=pwd_encryption,
                           all_roles=all_roles,
                           public_grants=public_grants,
                           no_expiry=no_expiry,
                           score=score,
                           risk=risk,
                           risk_color=risk_color,
                           issues=issues)
@app.route("/masking")
def masking():
    conn = get_conn()
    try:
        with conn.cursor() as cur:

            # Get all tables in public schema
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()

            # Get all columns with possible PII
            cur.execute("""
                SELECT
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND (
                    lower(column_name) LIKE '%email%' OR
                    lower(column_name) LIKE '%phone%' OR
                    lower(column_name) LIKE '%password%' OR
                    lower(column_name) LIKE '%address%' OR
                    lower(column_name) LIKE '%name%' OR
                    lower(column_name) LIKE '%ssn%' OR
                    lower(column_name) LIKE '%credit%' OR
                    lower(column_name) LIKE '%salary%' OR
                    lower(column_name) LIKE '%dob%' OR
                    lower(column_name) LIKE '%birth%'
                )
                ORDER BY table_name, column_name;
            """)
            pii_columns = cur.fetchall()

            # Get all existing views
            cur.execute("""
                SELECT table_name, view_definition
                FROM information_schema.views
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            views = cur.fetchall()

            # Get role privileges on tables
            cur.execute("""
                SELECT
                    grantee,
                    table_name,
                    privilege_type
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public'
                ORDER BY grantee, table_name;
            """)
            privileges = cur.fetchall()

    finally:
        release_conn(conn)

    return render_template("masking.html",
                           tables=tables,
                           pii_columns=pii_columns,
                           views=views,
                           privileges=privileges)


if __name__ == "__main__":
    app.run(debug=True)
