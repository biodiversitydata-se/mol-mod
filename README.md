# mol-mod
TEST module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

Uses some (e.g. BLAST) code from [Baltic sea Reference Metagenome web server](https://github.com/EnvGen/BARM_web_server).

### Overview
Flask (+ jQuery) app for BLAST and metadata (currently just gene & pcr primer) search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata part). The BLAST db was also pre-built from one of these views, using additional python code (see **misc/make-blastdb-from-api.py**).

### Branches
* **taxonid:** Based on using ASV id as taxonID only ('master' branch).

### Files and folders
* **molmod:** Flask app
* **misc:** Auxiliary files needed to run app, e.g. DB dump, API config and some test query files for BLAST.
* **environment.yml:** [Conda file](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file)

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

### DB setup
```
# Make current UNIX user into PostgreSQL user
sudo -u postgres createuser --superuser $USER
sudo -u postgres createdb $USER
# Set up roles from file (e.g. from previous pg_dumpall -g > db-roles.sql)
psql -f ~/[dir]/db-roles.sql
# Make new DB
createdb [db-name]
# Restore from dump file (from previous pg_dump [db-name])
psql --single-transaction [db-name] < ~/[dir]/db-dump
```
