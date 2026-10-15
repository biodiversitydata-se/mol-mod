# mol-mod
Module ([the Swedish ASV portal](http://asv-portal.biodiversitydata.se/)) for sharing and exploring Amplicon Sequence Variants (ASVs) and species occurrences derived from metabarcoding (eDNA) studies in [SBDI](https://biodiversitydata.se/).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19572089.svg)](https://doi.org/10.5281/zenodo.19572089)

### Overview
The ASV portal web application (described in detail [here](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-022-05120-z)) lets users submit metabarcoding (eDNA) datasets to the ASV database and SBDI Bioatlas/GBIF, search for Amplicon Sequence Variants (ASVs) and associated Bioatlas records (via BLAST or taxonomy/sequencing filters), and download occurrence datasets in a condensed Darwin Core–like format that can be unpacked, merged and summarised using the [asvoccur R package](https://github.com/biodiversitydata-se/asvoccur).

The portal is built using a set of small services managed with Docker Compose. The main app has a Python-Flask backend and a jQuery frontend, and in production it runs behind uWSGI and [a dockerised NGINX reverse proxy](https://github.com/biodiversitydata-se/proxy-ws-mol-mod-docker). Data are stored in PostgreSQL and made available through [postgREST](https://postgrest.org/en/stable/). BLAST jobs are handled by a scalable worker service, and persistent storage (via bind-mounted volumes) supports e.g. BLAST and ASV databases. The repository also includes admin scripts for managing data, written in both Python and Bash by different contributors.

The main service uses a lightweight Dockerfile for development and a fuller one for production, while the BLAST worker always builds from a single image controlled by the `FLASK_DEBUG` Compose setting. Separate Compose files exist for development, production, and local testing of the production runtime.

The `Makefile` uses explicit build targets for development vs production images, while runtime targets (e.g. `up`, `down`, `logs`) select the appropriate Compose file. On macOS, `PLATFORM=mac` defaults to the local production runtime variant (`docker-compose.prod.local.yml`).

---

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
- On Apple Silicon (ARM), images must still be built for the server's architecture (amd64), and the published images exist for amd64 only. Install Rosetta and make Docker build, pull and run amd64 images, e.g. in `~/.bash_profile`:
  ```
  softwareupdate --install-rosetta
  export DOCKER_DEFAULT_PLATFORM=linux/amd64
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

### Data management
Processing uploaded files, taxonomic annotation, importing, publishing in the
IPT and GBIF, making datasets public, exports, post-import edits,
taxonomic updates, BLAST-database generation, deletions and background on target
prediction filtering are described in
[`docs/data-management.md`](docs/data-management.md).

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
