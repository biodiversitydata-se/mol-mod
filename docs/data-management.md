# Data management

How a dataset goes from an uploaded file to a searchable, published dataset in
the ASV portal, and how imported data are maintained. Running the portal itself
is described in the main [README](../README.md).

## Overview

**New dataset**, in this order:
- [Preprocessing and annotation](#preprocessing-and-annotation): check and
  edit the uploaded file in R, annotate with ampliseq
- [Importing](#importing): dry-run locally, confirm changes with the provider,
  import on the server
- [Archiving](#archiving): zip the upload and R scripts for reproducibility
- [Publishing in the IPT and GBIF](#publishing-in-the-ipt-and-gbif): create
  the IPT resource, hand over to the provider, publish, register, Bioatlas
  ingestion
- [Going public in the ASV portal](#going-public-in-the-asv-portal): make the
  dataset searchable, update stats and BLAST database
- [Dataset exports](#dataset-exports): build the archive for the Download page

**Maintaining imported data**
- [Edits after import](#edits-after-import): fix or replace a dataset,
  republish and re-export
- [Taxonomic updates](#taxonomic-updates): re-annotate ASVs and republish the
  affected datasets
- [Rebuilding the BLAST database](#rebuilding-the-blast-database)
- [Data deletions](#data-deletions)

**Background**
- [Target prediction filtering](#target-prediction-filtering): how ASVs not
  from the target gene are excluded

## New dataset

### Preprocessing and annotation

Uploaded files are processed with `scripts/processing/asv-input-processing.R`
(setup, helpers, checks and test data:
[`scripts/processing/README.md`](../scripts/processing/README.md)). Work in a
folder per dataset, outside the repository:

```
<datasetID>/
├── asv-input-processing-<YYMMDD>.R
├── input/      # uploaded file (name unchanged); later annotation.tsv, ASV_tax.*.tsv
├── ampliseq/   # params.yaml
└── output/     # <datasetID>.fasta, <datasetID>-adm.xlsx, <datasetID>-adm.tar.gz
```

1. Copy the script into the folder as `asv-input-processing-<YYMMDD>.R` and
   edit section 1.
2. **First pass:** source the script. It stops after section 11 and writes
   the fasta, `ampliseq/params.yaml` and `output/submission-checks.txt`.
3. **Review** the output and checks; correct data in section 14 with
   `change_value()`.
4. **Annotate** on the HPC cluster, from the dataset folder:
   ```sh
   ampliseq-hpc.sh push     # copy params.yaml and fasta to the cluster
   ampliseq-hpc.sh start    # run ampliseq in a detached screen session
   ampliseq-hpc.sh status   # repeat until annotation.tsv is present
   ampliseq-hpc.sh fetch    # copy annotation.tsv (and ASV_tax.*.tsv) to input/
   ```
5. **Second pass:** source the script again. It writes
   `output/<datasetID>-adm.tar.gz`, `output/changes.txt` and, if data were
   changed, `draft_changes_email.eml`.

### Importing

```sh
make dry-import file=/path/to/<datasetID>-adm.tar.gz
make import file=/path/to/<datasetID>-adm.tar.gz
```
More options: `PARSER.add_argument` in `molmod/importer/importer.py`.

1. **Dry-run** locally; fix validation errors and
   [target-prediction conflicts](#target-prediction-filtering).
2. **Confirm changes:** send `draft_changes_email.eml` (Mac Mail: *Message →
   Send Again*) and wait for the provider's agreement.
3. **Import** on the server after `make backup`. `make conflict-import`
   imports despite conflicts; the affected ASVs keep their existing
   annotation until a [taxonomic update](#taxonomic-updates).

### Archiving

Move the dataset folder to `Imported/` and zip `input/` and all `*.R` files:
```sh
scripts/processing/zip-ds.sh <datasetID>   # run from the folder containing Imported/
```
Copy the zip to the archive folder on the server.

### Publishing in the IPT and GBIF

In the [IPT](https://www.gbif.se/ipt/) (see the
[manual](https://ipt.gbif.org/manual/en/ipt/latest/)):

1. **Create three SQL data sources** (occurrence, emof, mixs) from the views
   `api.dwc_oc_occurrence`, `api.dwc_oc_emof` and `api.dwc_oc_mixs`:
   ```sql
   SELECT * FROM api.dwc_oc_occurrence
   WHERE dataset_pid = <pid> AND "datasetID" = '<datasetID>'
   ```
2. **Create the resource**; short name = lowercase datasetID.
3. **Map the fields.** For 18S, do **not** map `kingdom` and `phylum`
   (worse name matching).
4. **Hand over to the provider:** add them as IPT user (*Manager without
   registration rights*) and email them (draft from
   `scripts/processing/email-generator.R`). They fill in the metadata and sign
   the agreement; their organisation must be a GBIF publisher.
5. **Finish the metadata:** remove yourself from *Associated Parties* and end
   the description with:
   ```html
   <p>This dataset was published via the <a href="https://asv-portal.biodiversitydata.se/">SBDI ASV portal</a>.</p>
   ```

   If the description editor strips HTML, edit the EML (DocBook) and import it
   instead; do not save the description in the editor afterwards.
6. **Publish and register:** *Visibility → Public*, *Published Versions →
   Publish* (with a version note; review the report and DwC-A), then
   *Register*. Version notes can be edited later in the version history.
7. **Bioatlas ingestion:** email the Bioatlas team and note the resource ID
   (`drXXXX`) the dataset gets.

### Going public in the ASV portal

Once the dataset is in the Bioatlas, include it in BLAST, filter search,
About stats and the Download page:
```sh
make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
make stats
make blastdb
```
Find the pid in `api.annotation_overview` or the `make delete` menu (quit
without deleting). Then tell the provider.

### Dataset exports

Build the DwC-like zips for the Download page:
```sh
make export             # all datasets with in_bioatlas = TRUE
make export ds="1 4"    # specific datasets (pids)
```
The zip holds the database data and the current IPT EML; only the DOI comes
from GBIF. Re-export whenever a public dataset changes.

Then check:
- that the versions in each zip agree:
  ```sh
  docker exec -i asv-main python3 - /app/data-volumes/exports < scripts/audit-export-versions.py
  ```
  `scripts/fix-export-readme.py` rebuilds a README citation from the IPT EML.
- that the README has a DOI. `DOI: N/A` means the dataset was not yet
  registered or GBIF did not respond; re-export.

## Maintaining imported data

The ASV portal, IPT, GBIF and Bioatlas are not synced automatically;
coordinate with the Bioatlas team before changing public data.

### Edits after import

Edit data directly in the database, not via the dataset's R script. For a
public dataset, then:
1. Republish in the IPT with a version note.
2. `make export ds="<pid>"` (and `make stats` / `make blastdb` if affected).
3. Remind the Bioatlas team to re-ingest.
4. Log the change in the post-import edit log (one row per IPT version).

To **replace** a dataset:
1. [Delete](#data-deletions) it first; the importer keeps existing
   annotations of ASVs already in the database.
2. Import the new version with the same datasetID.
3. Update the IPT data sources to the new pid, run `make status`, republish
   and re-export.

### Taxonomic updates

`api.annotation_overview` shows reference database, ampliseq version and
classifier per dataset. To re-annotate the ASVs of a target gene tied to a
reference database:

1. **Export** the sequences:
   ```sh
   make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
   ```
2. **Annotate** with [nf-core/ampliseq](https://nf-co.re/ampliseq).
3. **Add target prediction fields** with
   `scripts/processing/reannotation-processing.R` (also applies PR2/COIDB
   corrections) or by hand from `scripts/processing/output/reannotation.xlsx`.
4. **Import** in maintenance mode (old annotations get `status='old'`):
   ```sh
   make backup
   make main
   make reannot file=/path/to/reannotation.xlsx
   ```
   Check the result in `api.annotation_overview`.
5. **Republish** with `scripts/ipt-update/batch-update-ipt.py` (resource IDs
   and version notes in `resources.tsv`; credentials in `.ipt.cred`). It only
   starts the publications: check `pub_info.tsv` and wait until all finish.
6. **Re-export** and finish:
   ```sh
   make export ds="<pids>"
   make blastdb
   make nomain
   make backup
   ```
7. **Check** the Download page and remind the Bioatlas team to re-ingest.

### Rebuilding the BLAST database

```sh
make blastdb
```
Includes datasets with `in_bioatlas = TRUE` only. More options:
`PARSER.add_argument` in `blast-worker/blast_builder/blast_builder.py`.

### Data deletions

```sh
make delete      # or scripts/delete-dataset.sh
```
Then `make stats`, and `make blastdb` if the dataset was public.

## Background

### Target prediction filtering

All denoised sequences are imported; ASVs not predicted to derive from the
target gene are hidden from searches, results and IPT views. The prediction
can change at re-annotation. Before import, each ASV gets:
- `annotation_target`: target gene of the reference database (e.g.
  `16S rRNA`).
- `target_prediction`: `TRUE`/`FALSE`.
- `target_criteria`: e.g. `'Assigned kingdom OR Barrnap-positive'` or
  `'None: defaults to TRUE'`.

At import, they are compared with existing annotations:

```
--	target	pred	pred	pred	pred
db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneA	TRUE	TRUE	FALSE	FALSE
--	----	Ignore	Check	Check	Ignore

db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneB	TRUE	TRUE	FALSE	FALSE
--	----	Check	Update	ignore	Ignore
```

"Update" is applied automatically. "Check" stops the import with a table of
affected ASVs (see [Importing](#importing) for `make conflict-import`).
Otherwise, incoming annotations of existing ASVs are ignored, so they need not
match the database. See `compare_annotations` in
`molmod/importer/importer.py`.

All views filter on:
```sql
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See `db/db-api-schema.sql`.
