📦 Phase 2: Backup, Restore & Disaster Recovery

 Objective
The goal of this phase is to ensure data reliability and recoverability in PostgreSQL by implementing automated backup systems, restore validation, and basic disaster recovery mechanisms.

Environment Setup
- OS: Ubuntu (WSL / Virtual Machine)
- Database: PostgreSQL 18
- Port: 5433
- Database Used: `appdb`

Commands Used
sudo mkdir -p /pgbackups/{full,schema,data,logs}
sudo chown -R postgres:postgres /pgbackups

Backup Types Implemented
🔹 Full Backup (Custom Format)
sudo -u postgres pg_dump -p 5433 -Fc appdb \
> /pgbackups/full/appdb_full_$(date +%F).dump

🔹 Schema-Only Backup
sudo -u postgres pg_dump -p 5433 -s appdb \
> /pgbackups/schema/appdb_schema_$(date +%F).sql

🔹 Data-Only Backup
sudo -u postgres pg_dump -p 5433 -a appdb \
> /pgbackups/data/appdb_data_$(date +%F).sql

Backup Integrity CheckRotation Commands
find /pgbackups/full -type f -mtime +7 -delete
find /pgbackups/schema -type f -mtime +14 -delete
find /pgbackups/data -type f -mtime +30 -delete

Step 1: Insert Sample Data
CREATE TABLE recovery_test (
  id SERIAL PRIMARY KEY,
  name TEXT
);

INSERT INTO recovery_test (name)
VALUES ('Alice'), ('Bob'), ('Charlie');

Step 2: Take Backup
pg_dump -Fc appdb > appdb_full_after_data.dump

Step 3: Delete Data
DELETE FROM recovery_test;

Step 4: Restore to New Database
createdb appdb_recovered
pg_restore -d appdb_recovered appdb_full_after_data.dump

Step 5: Verify Recovery
SELECT COUNT(*) FROM recovery_test;

Outcome
* Implemented a fully automated PostgreSQL backup system
* Ensured data recoverability through restore validation
* Simulated disaster recovery scenarios
* Applied production-level backup strategies
