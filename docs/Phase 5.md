Phase 5
**Task 5.1 Security, Compliance & Auditing**
##Objective
Check the database for security weaknesses and give a score so a DBA knows how safe the database is and what to fix.

Example
Score               Risk
Level80 – 100    Low risk — database is secure
60 – 79          Medium risk — some fixes needed
40 – 59          High risk — serious problems
Below 40         Critical — fix immediately

Step 1 — Add this route to app.py
nano ~/flask_dashboard/app.py
Add before if __name__ == "__main__":
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

Step 2 — Create security.html
nano ~/flask_dashboard/templates/security.html


Step 3 — Add security link to your main dashboard topbar in index.html
Find the topbar links and add:
<a href="/security" class="nav-btn" style="background:#334155; color:#94a3b8; border:1px solid #475569; border-radius:8px; padding:6px 14px; font-size:12px; text-decoration:none;">
  Security Audit
</a>

Step 4 — Run and test
python3 app.py


**Task 5.2 — Data Masking & Access Control**
Objective
Protect sensitive data by hiding it from users who should not see the real values, and verify that every role only has the access it needs.

Example:
Real value                        Masked value
john.smith@gmail.com              joh***@***.com
9876543210                        ***-***-3210
mypassword123                     ********
John Smith                        J***

Step 1 — Add route to app.py
nano ~/flask_dashboard/app.py

Step 2 — Create masking.html

Step 3 — Add link in index.html topbar

Step 4 - Run And Test 
