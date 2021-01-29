# mol-mod
TEST module for handling sequence-based occurrence data in [Biodiversity Atlas Sweden](https://bioatlas.se/) / [SBDI](https://biodiversitydata.se/). See [GitHub Pages on molecular data services](https://biodiversitydata-se.github.io/mol-data/) for more info.

Uses some (e.g. BLAST) code from [Baltic sea Reference Metagenome web server](https://github.com/EnvGen/BARM_web_server).

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). The BLAST db was also pre-built from one of these views, using additional python code (see **misc/make-blastdb-from-api.py**).

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
