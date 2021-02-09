# mol-mod
Module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). The BLAST db was also pre-built from one of these views, using additional python code (see **misc/make-blastdb-from-api.py**).

### Development environment
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
development (except for changes in worker.py, as it is copied into container at startup, i.e. not mounted from host). Note that this setup is not intended for production, and should not
be used as such.

### Production environment
To test the production system, you will first need to simulate a 'real' .env file (to be auto-generated later):
```
$ cp .env.template .env
```

Docker-compose operations (in production) are simplified using a Makefile. Pull the images and start the server with:
```
$ make run
```

Finally, you will need to put some data on the volumes as well, this can be done using:
```
$ ./backup.sh restore
for file in blast-databases/*; do docker cp $file mol-mod_blast-worker_1:/blastdbs/; done
```
Note that the blast-worker uses the same Dockerfile for both development and production, but that we set FLASK_ENV=production in docker-compose.prod.yml.

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
