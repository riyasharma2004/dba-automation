Overview
Phase 4 covers two core DBA tasks focused on reducing query latency and preventing performance degradation in PostgreSQL databases. Both tasks were implemented as web-based tools integrated into the existing Flask monitoring dashboard built in Phase 3.

Task 4.1 — Index & Table Optimization Tool
Objective
Reduce query latency by identifying missing, unused, and duplicate indexes in the PostgreSQL database.
What is an Index?
An index is a data structure that allows PostgreSQL to find rows quickly without scanning the entire table. Without indexes, PostgreSQL performs a Sequential Scan — reading every row one by one. With an index, it performs an Index Scan — jumping directly to the relevant rows.

