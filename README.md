# mol-mod
Module ([the Swedish ASV portal](http://asv-portal.biodiversitydata.se/)) for handling sequence-based occurrence data in [SBDI](https://biodiversitydata.se/).

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). Note that different contributors have used different tools for communicating with the database (see /scripts dir). This could perhaps be made more consistent in the future.

### Prerequisites
The application can be run as a docker-compose environment, assuming you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed. Mac users may additionally need to install coreutils, to access the included greadlink tool, plus a newer version of bash, to run some db maintenance scripts. This can e.g. be done with Homebrew:
```
  $ brew install coreutils
  $ brew install bash
```

### Environmental variables
Use .env.template to create .env file, and add missing values to the latter, before proceeding.
```
  $ cp .env.template .env
```

### Development environment
In development, postgres data and config files are written to bind-mounted dir *postgres-data*, which needs to be deleted if you later want to regenerate the db from schema files and dumps in *db* dir. This is also required when you generate new passwords and API config file (secrets).
```
  $ rm -R postgres-data/
```
Generate secrets, or reuse old:
```
  $ ./scripts/generate_secrets.py --skip-existing
```
If no secrets exist before, this will copy *config/email.conf.template* into *.secret.email_config* which then needs to be manually filled with mail server and account details. Likewise, you need to add a list of recipient email addresses to environmental variable *UPLOAD_EMAIL*, plus the IP:s of webapp and IPT hosts to *DBACCESS*, in *.env* file.

Then, start up services:
```
  $ docker-compose up
```
The development site should now be available at http://localhost:5000.

Once the system is up and running, see *Production environment* below for how to insert data into the database, and how to build a blast database from sequences in the Bioatlas etc.

The server will automatically rebuild on changes to the python code for ease of
development (except for changes in worker.py, as it is copied into container at startup, i.e. not mounted from host). Note that this setup is not intended for production, and should not
be used as such.

To stop and remove containers as well as remove network and volumes:
```
  $ docker-compose down -v
```
You may also want to get rid of dangling images and associated volumes:
```
  $ docker system prune --volumes
```

### Production environment
In production, postgres and blastdb data are saved to named volumes (mol-mod_postgres-db & mol-mod_blast-db), and compose operations are simplified using a Makefile (actually, make-rules that don't involve a specific docker-compose file can also be used in development environment).

Again, you need to either generate secrets, or reuse old ones:
```
  $ make secrets
```
Also, see *Development environment* (above) on how to set up email and database access, before continuing.

Then, to pull images and start up services:
```
  $ make run
```

Once the system is running, you can insert the default data into the database:
```
  $ make restore
```
You also need to copy the BLAST database into the worker container:
```
  $ make blast-copy
```
Alternatively, you may want to *generate and* copy the blast-db:
```
  $ make blast
```
As BLAST, filter search and About stats will only return data from datasets already in the Bioatlas, you may also need to update the Bioatlas metadata for a dataset:
```
  $ make status pid=17 status=1 ruid=dr15
```
...which also updates the materialized view behind the About stats.
Alternatively, you can just update the view:
```
  $ make status
```
Note that the blast-worker uses the same Dockerfile for both development and production, but that we set
FLASK_ENV=production in docker-compose.prod.yml.

You can use a script to create incremental backups of the database, container logs and uploaded files to (host) folder [repos-path]/backups:
```
  $ ./scripts/scheduled-backup.sh
```
This script can also be used to run from crontab (time-based job scheduler). Suggested crontab entry for twice-daily backups as 9 AM and 9 PM:
```
  0 9,21 * * * /opt/mol-mod/scripts/scheduled-backup.sh
```

### CAS authentication
For local testing of production environment, you need to run or add this to your bash startup file (e.g. ~/.bash_profile):
```
  $ export HOST_URL=http://localhost:5000
```
Otherwise the Bioatlas CAS server will redirect users to 'https://asv-portal.biodiversitydata.se' after logout.


### Database access
Database access can be limited to IP ranges listed in environment variable `DBACCESS` in .env file. As a default, this is set to include loopback/same device, private and Docker networking defaults:
```
DBACCESS=127.0.0.1/8 192.168.0.0/16 10.0.0.0/8 172.16.0.0/12
```
Note that you need to stop services and remove the database for any changes to take effect.

Alternatively, to add new address range(s) without removing the database, you can run a script inside the container, and then restart it for changes in pg_hba.conf to take effect:
```
  $ docker exec -e DBACCESS='xxx.xx.xx.xxx/32' asv-db docker-entrypoint-initdb.d/04-restrict-db.sh
  $ docker restart asv-db
```
Note that you may have to edit firewall settings to allow incoming connections to port 5432, from those same ranges, e.g. in ufw:
```
  $ sudo ufw allow from xxx.xx.xx.xxx/32 to any port 5432
```

### File uploads
The size limit you set in nginx (molecular.conf: client_max_body_size) needs to correspond to the setting in flask (.env: MAX_CONTENT_LENGTH) for restriction to work properly. Note that neither the flask development server nor uwsgi handles this well, resulting in a connection reset error instead of a 413 response (See Connection Reset Issue in [Flask documentation](https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/) when testing locally.

You can list uploaded files in running asv-main container:
```
  $ docker exec asv-main ls /uploads
```
It is also possible to copy a specific file, or the whole directory, to the host, using either of these commands:
```
  $ mkdir -p uploads && docker cp asv-main:/uploads/[filename] uploads
  $ docker cp  asv-main:/uploads .
```
When a file is uploaded, an email notification is sent to each of the addresses included in the environmental variables UPLOAD_EMAIL or DEV_UPLOAD_EMAIL.

### Data import
Import data (in Excel or text file format) using a separate python script. See:
```
  $ ./scripts/import_excel.py --help
```
This script executes *importer.py* inside the main container. Check the *PARSER.add_argument* section in this script for available arguments, which can be added to main function call like so:
```
  $ ./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```
For new datasets to be available in BLAST database build or filter search, you also need to set dataset property *in_bioatlas* to *true* (e.g. via pgAdmin until implemented as script running in container). See also *BLAST-database generation* below.

### Data deletions
In the production environment, you can delete single datasets with an interactive script:
```
  $ scripts/delete-dataset.sh
```
Remember to update status accordingly (see above).

### BLAST-database generation
Generate a new BLAST database (including ASVs from datasets that have been imported into the Bioatlas only), using another script. See:
```
  $ ./scripts/build_blast_db.py --help
```
This script executes *blast_builder.py* inside a blast-worker container. Again, check the *PARSER.add_argument* section for available arguments, which can be added to main function call like so:
```
  $ ./scripts/build_blast_db.py -vv
```

### Updates on server
If you have built new images locally and pushed to dockerhub](https://hub.docker.com/r/bioatlas/), you can just pull and run these directly on the server:
```
  $ make pull
  $ make up
  # or
  $ make run
```
But if you have made changes to *compose* or *.env files*, you also need to update the git repos:
```
  $ git pull
```
If the app still doesn't update properly, double-check that you have pulled the correct version of the image: with info on dockerhub:
```
  $ docker image ls --digests
```
You may also have to empty the browser cache (Chrome/Mac: shift + cmd + R), to implement changes in jQuery.

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
