# mol-mod
Module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part).

### Prerequisites
The application can be run as a docker-compose environment, assuming you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

### Development environment
In development, postgres data and config files are written to bind-mounted dir *postgres-data*, which needs to be deleted if you later want to regenerate the db from schema files and dumps in *sql* dir. This is also required when you generate new passwords and API config file (secrets).
```
  $ rm -R postgres-data/
```
Generate secrets, or reuse old:
```
  $ ./scripts/generate_secrets.py --skip-existing
```
Then, start up services:
```
  $ docker-compose up
```
Once the system is running, you can insert the default data into the database:
```
  $ ./backup.sh restore
```

The development site should now be available at http://localhost:5000.

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
In production, postgres and blastdb data are instead saved to named volumes (mol-mod_postgres-db & mol-mod_blast-db), and compose operations are simplified using a Makefile.

Again, you need to either generate secrets, or reuse old:
```
  $ make secrets
```
Then, to pull images and start up services:
```
  $ make run
```
Once the system is running, you can insert the default data in the database, and copy blastdb files into worker container:
```
  $ make restore
  $ make blast
```
If you want to stop and restart clean, use the following shortcut (see details in Makefile):
```
  $ make rebuild
```

Note that the blast-worker uses the same Dockerfile for both development and production, but that we set FLASK_ENV=production in docker-compose.prod.yml.

### Data import
Import data (in Excel or text file format) using a separate python script. See:
```
  $ ./scripts/import_excel.py --help
```
This script executes *importer.py* inside the main container. Check the *PARSER.add_argument* section in this script for available arguments, which can be added to main function call like so:
```
  $ ./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```

### BLAST-database generation
Generate a new BLAST database (including ASVs from datasets that have been imported into the Bioatlas only), using another script. See:
```
  $ ./scripts/build_blast_db.py --help
```
This script executes *blast_builder.py* inside a blast-worker container. Again, check the *PARSER.add_argument* section for available arguments, which can be added to main function call like so:
```
  $ ./scripts/build_blast_db.py -vv
```

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
