# mol-mod
Module ([the Swedish ASV portal](http://asv-portal.biodiversitydata.se/)) for sharing and exploring Amplicon Sequence Variants (ASVs) and species occurrences derived from metabarcoding (eDNA) studies in [SBDI](https://biodiversitydata.se/).

[![DOI](https://zenodo.org/badge/220973056.svg)](https://zenodo.org/badge/latestdoi/220973056)

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
