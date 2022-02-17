# mol-mod
Module ([the Swedish ASV portal](http://asv-portal.biodiversitydata.se/)) for handling sequence-based occurrence data in [SBDI](https://biodiversitydata.se/).

[![DOI](https://zenodo.org/badge/220973056.svg)](https://zenodo.org/badge/latestdoi/220973056)

### Overview
Flask + jQuery app for BLAST and metadata search of sequence-based occurrences in SBDI, via separate BLAST and Amplicon Sequence Variant (ASV) databases. Views of the ASV db are exposed via [postgREST server](https://postgrest.org/en/v7.0.0/index.html), and accessed in API calls (for metadata search part). Note that different contributors have used different tools for communicating with the database (see */scripts* dir). This could perhaps be made more consistent in the future.

### Prerequisites
The application can be run as a docker-compose environment, assuming you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed. Mac users may additionally need to install coreutils, to access the included greadlink tool, plus a newer version of bash, to run some db maintenance scripts. This can e.g. be done with Homebrew:
```
  $ brew install coreutils
  $ brew install bash
```

### Environmental variables
Use *.env.template* to create *.env* file, and add missing values to the latter, before proceeding.
```
  $ cp .env.template .env
```

### Development environment
In development, postgres data and config files are written to bind-mounted dir *postgres-data*, which needs to be deleted if you later want to regenerate the db from schema files in *db* dir. This is also required when you generate new passwords and API config file (secrets).
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

Once the system is up and running, see *Production environment*, below, for how to insert data into the database, and how to build a blast database from sequences in the Bioatlas etc. Note that the bind-mounted directory *blast-databases* is only used in development.

The server will automatically rebuild on changes to the python code for ease of
development (except for changes in *worker.py*, as it is copied into container at startup, i.e. not mounted from host). Note that this setup is not intended for production, and should not
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
In production, postgres and blastdb data are saved to named volumes (*mol-mod_postgres-db* & *mol-mod_blast-db*), and compose operations are simplified using a Makefile (which also includes rules for executing various scripts, in either environment). We use a
[dockerised NGINX reverse proxy setup](https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker).

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
You also need to build a BLAST database:
```
  $ make blastdb
```
...and update the materialised view used for the About stats.
```
  $ make stats
```

Note that the blast-worker uses the same Dockerfile for both development and production, but that we set
*FLASK_ENV=production* in *docker-compose.prod.yml*.

You can use a script to create incremental backups of the database, container logs and uploaded files to (host) folder [repos-path]/backups:
```
  $ ./scripts/scheduled-backup.sh
```
This script can also be used to run from crontab (time-based job scheduler). Suggested crontab entry for twice-daily backups as 9 AM and 9 PM:
```
  0 9,21 * * * /opt/mol-mod/scripts/scheduled-backup.sh
```

### CAS authentication
For local testing of production environment, you need to run or add this to your bash startup file (e.g. *~/.bash_profile*):
```
  $ export HOST_URL=http://localhost:5000
```
Otherwise the Bioatlas CAS server will redirect users to 'https://asv-portal.biodiversitydata.se' after logout.

### Database access
Database access can be limited to IP ranges listed in environment variable `DBACCESS` in *.env* file. As a default, this is set to include loopback/same device, private and Docker networking defaults:
```
DBACCESS=127.0.0.1/8 192.168.0.0/16 10.0.0.0/8 172.16.0.0/12
```
Note that you need to stop services and remove the database for any changes to take effect.

Alternatively, to add new address range(s) without removing the database, you can run a script inside the container, and then restart it for changes in *pg_hba.conf* to take effect:
```
  $ docker exec -e DBACCESS='xxx.xx.xx.xxx/32' asv-db docker-entrypoint-initdb.d/04-restrict-db.sh
  $ docker restart asv-db
```
Note that you may have to edit firewall settings to allow incoming connections to port 5432, from those same ranges, e.g. in ufw:
```
  $ sudo ufw allow from xxx.xx.xx.xxx/32 to any port 5432
```

### File uploads
The size limit you set in nginx (*molecular.conf: client_max_body_size*) needs to correspond to the setting in flask (*.env: MAX_CONTENT_LENGTH*) for restriction to work properly. Note that neither the flask development server nor uwsgi handles this well, resulting in a connection reset error instead of a 413 response (See Connection Reset Issue in [Flask documentation](https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/)), but see added file validation in *molmod/static/js/main.js*.

When a file is uploaded, an email notification is sent to each of the addresses included in the environmental variables *UPLOAD_EMAIL* or *DEV_UPLOAD_EMAIL*.

You can list uploaded files in the running asv-main container using a Makefile rule:
```
  $ make uplist
```
It is also possible to copy a specific file, or the whole directory, to the host, using either of these commands:
```
  $ make upcopy
  $ make upcopy file=some-file.xlsx
```
Analogously, to delete a single/all uploaded file(s) in a running container:
```
  $ make updel
  $ make updel file=some-file.xlsx
```
### Data import
Before uploaded files can be imported into the postgres database, you need to do some preprocessing, including adding *dataset* and *annotation* tabs/files, and possibly cleaning data. Use the standalone R script *./scripts/import-test/asv-input-processing.R*, which can be customised and stored together with each uploaded file, for reproducibility. You can use the dummy data in *./scripts/import-test/input* to test the R script. The (*.tar.gz*) output can then be imported into postgres, using a separate python script that executes *importer.py* inside the main container. Note that the importer accepts *.xlsx* files as well, but that the *.xlsx* output from our R script currently only works if you open and save it in Excel first. Check the *PARSER.add_argument* section in the importer for available arguments, which can be added to main function call like so:
```
  $ ./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```
Alternatively, use a Makefile rule, e.g.:
```
  $ make dry-import file=/path/to/file.tar.gz
  $ make import file=/path/to/file.xlsx
```

Import includes some rudimentary validation (see e.g. regular expressions in *./molmod/importer/data-mapping.json*), but this should be improved in the future.

After importing, and publishing a dataset in the Bioatlas, you need change the *in_bioatlas* property to *true*, for data to be included in BLAST, filter search and About stats:
```
  $ make status pid=17 status=1 ruid=dr15
```
Also rebuild the BLAST database (See *BLAST-database generation* below).

### BLAST-database generation
Generate a new BLAST database (including ASVs from datasets that have been imported into the Bioatlas only) using a script that executes *blast_builder.py* inside a blast-worker container. Again, check the *PARSER.add_argument* section for available arguments, which can be added to main function call like so:
```
  $ ./scripts/build_blast_db.py -vv
```
...or use a Makefile rule:
```
  $ make blastdb
```

### Data deletions
You can delete single datasets with an interactive script:
```
  $ scripts/delete-dataset.sh
```
or:
```
  $ make delete
```
Both commands will bring up a menu with instructions for how to proceed with deletions. Remember to update status accordingly (see above).

### Taxonomic annotation
During the final step of data import, we add a record in table taxon_annotation for every new(!) ASV in the dataset. This is the standard SBDI annotation that we also plan to update as reference databases and/or annotation algorithms develop. To update the annotation of all ASV:s currently annotated against a specific reference database, you should first export a fasta file with those ASVs, using e.g.:
```
  $ make fasta ref=UNITE:8.0
```
This can then be used as input to the [ampliseq pipeline](https://nf-co.re/ampliseq), and the output (minus the *asv_id_alias* column, and saved as *.xlsx* or *.csv*, for now. See  *./scripts/update-annotation.sh* for info on structure of input) can then be fed into the database like so:
```
  $ make reannot file=/path/to/annotation.xlsx
```
Any previous annotations of these ASVs will be given *status='old'*, whereas the new rows will have *status='valid'*. Note that you have to update stats to make any changes visible in the *About* page table:
```
  $ make stats
```


### Target prediction filtering
In version 2.0.0, we make it possible to import all denoised sequences from a dataset, and then dynamically filter out any ASVs that we do not (currently) predict to derive from the targeted gene, thereby excluding these from BLAST and filter searches, result displays and IPT views. ASVs are thus only imported once, but their status can change, e.g. at taxonomic re-annotation. Criteria used for ASV exclusion may vary between genes / groups of organisms, but could e.g. combine the output from the *BAsic Rapid Ribosomal RNA Predictor (barrnap)* with the taxonomic annotation itself. For example, we may decide that only ASVs that are annotated at least at kingdom level OR get positive barrnap prediction should be considered as TRUE 16S rRNA sequences.

We implement this as follows:

Before import of a new dataset, we add the following annotation data to each ASV:
- *annotation_target* = target gene of reference database used for taxonomic annotation (eg. *16S rRNA*). At this stage, *annotation_target* will equal the *target_gene* of the dataset.
- *target_prediction* = whether the ASV is predicted to derive from the annotation_target (*TRUE/FALSE*).
- *target_criteria* = criteria used for setting *target_prediction* to *TRUE* (eg. *'Assigned kingdom OR Barrnap-positive'*, or *'None: defaults to TRUE'*).

During import, we compare annotation targets and predictions of ASVs in new datasets to annotations that already exist in db, with the following possible outcomes and responses:

```
--	target	pred	pred	pred	pred
db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneA	TRUE	TRUE	FALSE	FALSE
--	----	Ignore	Check	Check	Ignore

db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneB	TRUE	TRUE	FALSE	FALSE
--	----	Check	Update	ignore	Ignore
```

For example, in the top left case, an ASV in a new dataset comes in with an annotation for geneA, is also predicted to be a TRUE geneA sequence, and this corresponds with what is already noted in the database for that ASV, so we do nothing (the existing annotation remains). If, instead, a new dataset has a TRUE geneB prediction for an ASV that has previously been considered a FALSE geneA, this annotation can be automatically updated. Other conflicts likely require manual inspection and will cancel import with a notice of this. See */molmod/importer/importer.py* and function *compare_annotations* for details.

After import, we filter all database views with an extended WHERE clause:
```
WHERE ta.status::text = 'valid'
    # Criteria added for target prediction:
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See */db/db-api-schema.sql*.

### Tests
Note that tests have not been updated and adapted to the docker-compose environment.

### Licenses
This code (biodiversitydata-se/mol-mod) is released under CC0 (see https://github.com/biodiversitydata-se/mol-mod/blob/master/LICENSE), but uses the following components with MIT licenses:

[jQuery](https://github.com/jquery/jquery/blob/main/LICENSE.txt):
Copyright OpenJS Foundation and other contributors, https://openjsf.org/

[DataTables](https://datatables.net/license/mit#MIT-license):
Copyright (C) 2008-2022, SpryMedia Ltd.

[select2](https://github.com/select2/select2/blob/develop/LICENSE.md):
Copyright (c) 2012-2017 Kevin Brown, Igor Vaynberg, and Select2 contributors

The following permission statement apply to each of the above:

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
