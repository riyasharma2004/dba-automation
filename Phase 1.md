Task 1: Installation and Basic Setup of PostgreSQL on Ubuntu

## Objective
To install PostgreSQL on Ubuntu, verify its status, and access the database using the PostgreSQL command-line interface.
---
## Step 1: Update System Packages
Update the package list to ensure the latest versions are installed.
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y

Verify PostgreSQL Service Status
sudo systemctl status postgresql
sudo systemctl start postgresql

Switch to PostgreSQL User
sudo -i -u postgres
Result - psql

Verify PostgreSQL Installation
SELECT version();

Exit PostgreSQL Shell
\q
exit

PostgreSQL was successfully installed on Ubuntu. The service was verified using systemctl, and the database was accessed using the psql interface.
Most Used Commands 
•	sudo → run as administrator
•	apt → Ubuntu package manager
•	update → refresh available packages
•	install → install software
•	git → package name
•	-y → auto-confirm yes
•	--version → tells the current version
•	grep → filter result
•	.systemctl → service manager

