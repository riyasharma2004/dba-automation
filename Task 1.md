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


![Uploading VirtualBox_ubuntu_26_02_2026_17_37_39.png…]()

