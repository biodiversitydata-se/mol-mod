# mol-mod
TEST module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

Uses some (e.g. BLAST) code from [Baltic sea Reference Metagenome web server](https://github.com/EnvGen/BARM_web_server).

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). The BLAST db was also pre-built from one of these views, using additional python code (see **misc/make-blastdb-from-api.py**).

### Branches
* **taxonid:** 'master' branch

### Files and folders
* **molmod:** Flask app
* **misc:** Auxiliary files needed to run app, e.g. DB dump, API config and some test query files for BLAST.
* **environment.yml:** [Conda file](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file)

### Notes from my setup on server
#### Firewall (ufw)
```bash
# Allow connections to db port 5432
ufw allow 5432/tcp
```
(also needed to open port on the security group applied to cloud server)
#### PostgreSQL
```bash
# Install
sudo apt update
sudo apt install postgresql postgresql-contrib
# Listen for connections from client applications on any TCP/IP address
sudo nano /etc/postgresql/12/main/postgresql.conf
# ..and add:
listen_addresses = '*'
# Allow any user on any IPv4 or IPv6 address to connect (with correct md5-encrypted password)
sudo nano /etc/postgresql/12/main/pg_hba.conf
# ...and add (to bottom) 
host   all             all              0.0.0.0/0               md5
host   all             all              ::/0                    md5
# Restart service
sudo service postgresql restart
# In local/source db: 
# Dump roles
pg_dumpall -g > roles.sql
# Dump db
pg_dump asv-postgrest > db-dump.sql
# On server:
# Add current linux user & user db (as postgres user)
sudo -u postgres createuser --superuser $USER
sudo -u postgres createdb $USER
# Add roles from source db
psql -f ~/mp-temp/db-roles.sql
# Add dumped db
createdb asv-postgrest
psql --single-transaction asv-postgrest < ~/mp-temp/db-dump
# Set pwd for postgres user 
psql
ALTER ROLE postgres WITH PASSWORD 'xxx';
```

### Environmental variables
Required environmental variable SECRET_KEY (used for global CSRF protection) can be set in your Conda environment:
```
conda activate [your-env-name]
# List existing
conda env config vars list
# Set var
conda env config vars set SECRET_KEY=[your-secret-key]
conda activate [your-env-name]
# Check var
echo $SECRET_KEY
```
