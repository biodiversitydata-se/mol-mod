# mol-mod
Module ([the Swedish ASV portal](http://asv-portal.biodiversitydata.se/)) for sharing and exploring Amplicon Sequence Variants (ASVs) and species occurrences derived from metabarcoding (eDNA) studies in [SBDI](https://biodiversitydata.se/).

[![DOI](https://zenodo.org/badge/220973056.svg)](https://zenodo.org/badge/latestdoi/220973056)

### Overview
The ASV portal web application (described in detail [here](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-022-05120-z)) lets users submit metabarcoding (eDNA) datasets to the ASV database and SBDI Bioatlas/GBIF, search for Amplicon Sequence Variants (ASVs) and associated Bioatlas records (via BLAST or taxonomy/sequencing filters), and download occurrence datasets in a condensed Darwin Core–like format that can be unpacked, merged and summarised using the [asvoccur R package](https://github.com/biodiversitydata-se/asvoccur).

The portal is built using a set of small services managed with Docker Compose. The main app has a Python-Flask backend and a jQuery frontend, and in production it runs behind uWSGI and [a dockerised NGINX reverse proxy](https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker). Data are stored in PostgreSQL and made available through [postgREST](https://postgrest.org/en/stable/). BLAST jobs are handled by a scalable worker service, and persistent storage (via bind-mounted volumes) supports e.g. BLAST and ASV databases. The repository also includes admin scripts for managing data, written in both Python and Bash by different contributors. In the future, these tools may be unified and integrated into a dedicated web-based admin interface.

The main service uses a lightweight Dockerfile for development and a fuller one for production, while the BLAST worker always builds from a single image controlled by the `FLASK_DEBUG` Compose setting. Separate Compose files exist for development, production, and local testing of production image, with a `Makefile` selecting the appropriate one for Mac users (see `Platform notes (macOS)`).

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- Updated **bash**, and GNU **coreutils** on the host (for admin scripts)

#### Platform notes (macOS)
- Install updated tools and set variable for Makefile with [Miniconda](https://docs.conda.io/en/latest/miniconda.html):  
  ```
  conda create -n admin-env -c conda-forge python=3.10 bash coreutils
  conda activate admin-env
  conda env config vars set PLATFORM=mac  # Used in Makefile to select correct Compose file
  conda deactivate && conda activate admin-env
  ```
- Port **5000** is used by the Flask/asv-main service, but may already be taken by Apple’s AirPlay Receiver. Disable AirPlay in `System Settings` or remap the port in `docker-compose.[prod.local.]yml`.  

### Environment & secrets
Create `.env` and edit as needed before running the app:
```
  $ cp .env.template .env
```

Generate [secrets](https://docs.docker.com/compose/how-tos/use-secrets/), or reuse old:
```
$ python3 ./scripts/generate_secrets.py --skip-existing
```
or use `Makefile target`:
```
  $ make secrets
```
If no secrets exist:
 - `config/email.conf.template` is copied to `.secret.email_config` (fill in mail server + account details).
 - Add recipient addresses to `UPLOAD_EMAIL` in `.env`

### Quick-start

#### Production
In production, Compose operations are simplified using a `Makefile`, which also provides targets for running admin scripts in any environment. To pull images and start up services:
```
  $ make up
```

Insert the default data into the database:
```
  $ make restore
```

Build a BLAST database:
```
  $ make blastdb
```

Update the materialised view used for the About stats.
```
  $ make stats
```

Export a dataset archive and make it available in the Download page:
```
  $ make export
```

See `Makefile` or relevant sections below for additional operations.

#### Development
In development, the server auto-reloads on code changes (except in `worker.py`, which is copied in at startup). To apply changes to the PostgreSQL schema (e.g. after generating new secrets), you need to empty the postgres data volume before starting services, though:
```
rm -rf ./data-volumes/postgres-db
```

Use the default `docker-compose.yml` directly, without the `Makefile`, for Compose-related operations. For example, to start and stop services:
```
docker compose up [-d]
docker compose down
```
The development site should be available at `http://localhost:5000`.

Makefile targets that are independent of a specific Compose file (e.g. admin scripts) behave the same as in `Production`.

Optionally, clean up dangling images and volumes:
```
docker system prune --volumes
```

### Database access
Database access can be limited to IP ranges listed in environment variable `DBACCESS` in `.env* file`. By default this includes loopback/same device, private, and Docker networking defaults:
```
DBACCESS=127.0.0.1/8 192.168.0.0/16 10.0.0.0/8 172.16.0.0/12
```
Note that you need to stop services and remove the database for changes to take effect.

Alternatively, to add new address range(s) without removing the database, you can run a script inside the container, and then restart it for changes in `pg_hba.conf` to apply:
```
  $ docker exec -e DBACCESS='xxx.xx.xx.xxx/32' asv-db docker-entrypoint-initdb.d/04-restrict-db.sh
  $ docker restart asv-db
```
If you connect from an external client (e.g. pgAdmin), you may also need to open the firewall for port 5432 on the host, for example with ufw:
```
  $ sudo ufw allow from xxx.xx.xx.xxx/32 to any port 5432
```

### File uploads
Ensure the nginx limit (`molecular.conf: client_max_body_size`) matches the Flask limit (`.env: MAX_CONTENT_LENGTH`) for proper enforcement. Neither the Flask development server nor uWSGI handle this gracefully: oversized uploads trigger a connection reset instead of a 413 response (See Connection Reset Issue in [Flask documentation](https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/)), but see additional file validation in `molmod/static/js/main.js`.

On successful upload, email notifications are sent to the addresses in `UPLOAD_EMAIL` or `UPLOAD_EMAIL_TEST`.

### Data import
Before uploaded files can be imported into the postgres database, you need to do some preprocessing, including adding `dataset` and `annotation` tabs/files, and possibly cleaning data. Use the standalone R script `./scripts/processing/asv-input-processing.R`, which can be customised and stored together with each uploaded file, for reproducibility. You can use the dummy data in `./scripts/processing/input` to test the R script. The output can then be imported into postgres, using a separate python script that executes `importer.py` inside the main container. Check the `PARSER.add_argument` section in the importer for available arguments, which can be added to main function call like so:
```
  $ ./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```
Alternatively, use a Makefile rule, e.g.:
```
  $ make dry-import file=/path/to/file.tar.gz
  $ make import file=/path/to/file.xlsx
```

Import includes some rudimentary validation (see e.g. regular expressions in `./molmod/importer/data-mapping.json`), but this should be improved in the future.

After importing, and publishing a dataset in the Bioatlas, you need change the `in_bioatlas` property to `true`, for data to be included in `BLAST SEARCH`, `FILTER SEARCH` and `ABOUT` page stats. You also need to add Bioatlas and IPT resource IDs, for the `DOWNLOAD DATA` page to work.
```
  $ make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
```
Also rebuild the BLAST database (See `BLAST-database generation` below).

### BLAST-database generation
Generate a new BLAST database (including ASVs from datasets that have been imported into the Bioatlas only) using a script that executes `blast_builder.py` inside a blast-worker container. Again, check the `PARSER.add_argument` section for available arguments, which can be added to main function call like so:
```
  $ ./scripts/build_blast_db.py -vv
```
or:
```
  $ make blastdb
```

### Backups
Since June 2025, the Swedish ASV portal backups are managed centrally by SBDI.  
Database dumps can, however, still be generated and saved under `./backups` with:
```
  $ ./scripts/database-backup.sh data
```
or:
```
make backup
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
Both commands will bring up a menu with instructions for how to proceed with deletions. Remember to update stats accordingly (see above).

### Taxonomic (re)annotation
On import, each **new** ASV gets a row in table `taxon_annotation` (standard SBDI annotation, updated as reference DBs/algorithms evolve).

To re-annotate ASVs for a given target gene currently tied to a specific reference DB:
  1) Export FASTA:
     ```
     make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
     ```
  2) Run the FASTA with [nf-core/ampliseq](https://nf-co.re/ampliseq).
  3) Since Ampliseq output doesn’t yet include fields from `Target prediction filtering` (as of 250904), either:
     - add them via `./scripts/processing/reannotation.processing.R`, or  
     - use `./scripts/processing/output/reannotation.xlsx` as a template and edit your own file.
  4) Import:
     ```
     make reannot file=/path/to/reannotation.xlsx
     ```
Previous annotations are marked `status='old'`; new rows get `status='valid'`.

### Target prediction filtering
In version 2.0.0, we make it possible to import all denoised sequences from a dataset, and then dynamically filter out any ASVs that we do not (currently) predict to derive from the targeted gene, thereby excluding these from BLAST and filter searches, result displays and IPT views. ASVs are thus only imported once, but their status can change, e.g. at taxonomic re-annotation. Criteria used for ASV exclusion may vary between genes / groups of organisms, but could e.g. combine the output from the *BAsic Rapid Ribosomal RNA Predictor (barrnap)* with the taxonomic annotation itself. For example, we may decide that only ASVs that are annotated at least at kingdom level OR get positive barrnap prediction should be considered as TRUE 16S rRNA sequences.

We implement this as follows:

Before import of a new dataset, we add the following annotation data to each ASV:
- `annotation_target` = target gene of reference database used for taxonomic annotation (eg. `16S rRNA`). At this stage, `annotation_target` will equal the `target_gene` of the dataset.
- `target_prediction` = whether the ASV is predicted to derive from the annotation_target (`TRUE/FALSE`).
- `target_criteria` = criteria used for setting `target_prediction` to `TRUE` (eg. `'Assigned kingdom OR Barrnap-positive'`, or `'None: defaults to TRUE'`).

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

For example, in the top left case, an ASV in a new dataset comes in with an annotation for geneA, is also predicted to be a TRUE geneA sequence, and this corresponds with what is already noted in the database for that ASV, so we do nothing (the existing annotation remains). If, instead, a new dataset has a TRUE geneB prediction for an ASV that has previously been considered a FALSE geneA, this annotation can be automatically updated. Other conflicts likely require manual inspection and will cancel import with a notice of this. See `/molmod/importer/importer.py` and function `compare_annotations` for details.

After import, we filter all database views with an extended WHERE clause:
```sql
WHERE ta.status::text = 'valid'
    -- Criteria added for target prediction:
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See `/db/db-api-schema.sql`.

### Dataset exports
To export condensed DwC-like dataset archives (zips) and make these available in the `Download` page, use the following `Makefile` target:
```
  $ make export             # All datasets
  $ make export ds="1 4"    # Specific dataset (pid:s)
```

### Maintenance mode
To show/hide a `Site Maintenance` message while keeping app running,
toggle `MAINTENANCE_MODE` and restart app, using `Makefile` targets (in production):
```
  $ make main [routes="blast filter"]
  $ make nomain
```

### Scaling of BLAST functionality
If needed, the system could be scaled to have more blast instances, by modifying the Compose command, e.g. like this:
```
  $ docker-compose up --scale=blast-worker=3
```
We have not looked into the details of this, though.

### Coding contributions
Suggestions and code contributions are always welcome. I aim to follow a Git-Flow branching model, though I occasionally simplify the process.

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
