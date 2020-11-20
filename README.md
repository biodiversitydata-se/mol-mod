# mol-mod
TEST module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

Uses some (e.g. BLAST) code from [Baltic sea Reference Metagenome web server](https://github.com/EnvGen/BARM_web_server).

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). The BLAST db was also pre-built from one of these views, using additional python code (see **misc/make-blastdb-from-api.py**).

### Files and folders
* **molmod:** Flask app
* **misc:** Auxiliary files needed to run app, e.g. DB dump, API config and some test query files for BLAST.

### Notes from my setup on server
#### Firewall (ufw)
```bash
# Allow connections to db port 5432
ufw allow 5432/tcp
```
(also needed to open port on the security group applied to cloud server)
#### PostgreSQL (DB)
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

# If not using dumps from *misc* folder:
# In local/source db:
# Dump roles
pg_dumpall -g > db-roles.sql
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

#### PostgREST (API server)
```bash
# Install
mkdir postgrest
cd postgrest
wget -c https://github.com/PostgREST/postgrest/releases/download/v7.0.1/postgrest-v7.0.1-linux-x64-static.tar.xz
tar xfJ postgrest-v7.0.1-linux-x64-static.tar.xz
```
Then copy file *postgrest.conf* from *misc* to *postgrest* folder.
Requires environmental variable *PGRST_DB_URI* to be set, e.g. by running:
```bash
export PGRST_DB_URI='postgres://authenticator:xxx@localhost:5432/asv-postgrest'
```
...or by setting it in conda environment (se header below).
```bash
# Start service (and direct output to log)
./postgrest postgrest.conf </dev/null >postgrest.log 2>&1 &
# Check
lsof -Pnl +M -i4
```
#### Conda
I use [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file) for package & environment management, i.e. not python venv.
```bash
# Install
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
sh Miniconda3-latest-Linux-x86_64.sh
# [yes, yes, yes]
conda config --set auto_activate_base false
# Create conda environment from file
# (if anything fails to install, it may help to change to less specific versions of packages)
conda env create -f environment-linux.yml
conda activate flapp
conda env config vars set SECRET_KEY='xxx'
conda env config vars set PGRST_DB_URI='xxx'
conda activate flapp
# Check var
echo $SECRET_KEY
```

#### Flask app
```bash
git clone https://github.com/biodiversitydata-se/mol-mod.git
```

#### Gunicorn, systemd + nginx
```bash
# Add new app service
sudo nano /etc/systemd/system/molmod.service
# Add the following:
Description=Gunicorn instance to serve molmod app
After=network.target
[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/mol-mod
Environment="FLASK_ENV=development"
ExecStart=/bin/bash -c 'source /home/ubuntu/miniconda3/etc/profile.d/conda.sh; \
    conda activate flapp; \
    gunicorn --workers 3 --bind unix:molmod.sock -m 007 wsgi:app'
[Install]
WantedBy=multi-user.target
# The following should create a molmod-sock file - used by nginx
sudo systemctl start molmod
# To auto-start after reboot (but requires db & api to run as well)
sudo systemctl enable molmod
# Start service
sudo systemctl start molmod
# Configure nginx
sudo nano /etc/nginx/sites-available/molmod
# And add:
server {
listen 80;
  server_name 89.45.233.130 molecular2.infrabas.se;
location / {
  include proxy_params;
  proxy_pass http://unix:/home/ubuntu/mol-mod/molmod.sock;
  }
}
sudo ln -s /etc/nginx/sites-available/molmod /etc/nginx/sites-enabled
sudo systemctl start nginx
```


### Docker environment

The development system can be run as a docker-compose environment. If you have
docker available you can create the docker environment with:
```
  $ docker-compose up
```
Once the system is running, you can insert the default data in the database:
```
  $ ./backup.sh restore db-dump-data_2020-11-18.sql.tar
```

The development site should now be available at http://localhost:5000.

The server will automatically rebuild on changes to the python code for ease of
development. Note that this setup is not intended for production, and should not
be used as such.

### Testing

To run the available python unittests, you need to create a local python
environment with the required packages. This can be done with the following
commands:
```
  $ python3 -m venv venv
  $ source venv/bin/activate
  $ pip install --upgrade pip
  $ pip install -r molmod/requirements.txt
```

Once the environment is available, you don't need to rebuild it unless you add
additional requirements to the `requirements.txt` file.

Run the tests with:
```
  $ source venv/bin/activate
  $ python tests.py
```
