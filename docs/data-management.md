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

Uploaded files are turned into an import archive with
`scripts/processing/asv-input-processing.R`; setup, helper scripts and checks
are described in [`scripts/processing/README.md`](../scripts/processing/README.md)
(dummy data for testing in `scripts/processing/input`). Work in a folder per
dataset, outside the repository:

```
<datasetID>/
├── asv-input-processing-<YYMMDD>.R
├── input/      # uploaded file (name unchanged); later annotation.tsv, ASV_tax.*.tsv
├── ampliseq/   # params.yaml
└── output/     # <datasetID>.fasta, <datasetID>-adm.xlsx, <datasetID>-adm.tar.gz
```

1. Copy the script into the folder as `asv-input-processing-<YYMMDD>.R` and
   edit section 1.
2. **First pass:** source the script. Without `input/annotation.tsv` it stops
   after section 11, writing the fasta, `ampliseq/params.yaml` and
   `output/submission-checks.txt`, and asks for the ampliseq version.
3. **Review** the output and checks; correct the provider's data in section
   14 with `change_value()`.
4. **Annotate** with nf-core/ampliseq on the HPC cluster, from the dataset
   folder:
   ```sh
   ampliseq-hpc.sh push     # copy params.yaml and fasta to the cluster
   ampliseq-hpc.sh start    # run ampliseq in a detached screen session
   ampliseq-hpc.sh status   # repeat until annotation.tsv is present
   ampliseq-hpc.sh fetch    # copy annotation.tsv (and ASV_tax.*.tsv) to input/
   ```
5. **Second pass:** source the script again. It writes
   `output/<datasetID>-adm.tar.gz`, `output/changes.txt` and, if anything was
   changed, `draft_changes_email.eml`.

### Importing

```sh
make dry-import file=/path/to/<datasetID>-adm.tar.gz
make import file=/path/to/<datasetID>-adm.tar.gz
```
These run `importer.py` in the main container; for more options, see its
`PARSER.add_argument` section or run e.g.
`./scripts/import_excel.py FILE --dry-run -vv`.

1. **Dry-run** locally and resolve validation errors and target-prediction
   conflicts (see [Target prediction filtering](#target-prediction-filtering)).
2. **Confirm changes:** if `output/changes.txt` lists changes, send
   `draft_changes_email.eml` (in Mac Mail: *Message → Send Again*, ⇧⌘D) and
   wait for the provider's agreement.
3. **Import** on the server after `make backup`. To import despite
   target-prediction conflicts, use `make conflict-import`: the affected ASVs
   keep their existing annotation, so plan a
   [taxonomic update](#taxonomic-updates) of the marker.

### Archiving

Move the dataset folder to `Imported/` and zip `input/` and all `*.R` files:
```sh
scripts/processing/zip-ds.sh <datasetID>   # run from the folder containing Imported/
```
Copy the zip to the archive folder on the server.

### Publishing in the IPT and GBIF

Datasets are published through the [IPT](https://www.gbif.se/ipt/);
see the [IPT manual](https://ipt.gbif.org/manual/en/ipt/latest/).

1. **Create three SQL data sources** (occurrence, emof, mixs) from the views
   `api.dwc_oc_occurrence`, `api.dwc_oc_emof` and `api.dwc_oc_mixs`:
   ```sql
   SELECT * FROM api.dwc_oc_occurrence
   WHERE dataset_pid = <pid> AND "datasetID" = '<datasetID>'
   ```
   A re-imported dataset gets a new pid: update the sources.
2. **Create the resource**, with the lowercase datasetID as short name
   (`ipt_resource_id`).
3. **Map the fields.** For 18S, do **not** map `kingdom` and `phylum`
   (worse GBIF/Bioatlas name matching).
4. **Hand over to the provider:** add them as IPT user (*Manager without
   registration rights*) and email them; `scripts/processing/email-generator.R`
   drafts the email. The provider fills in the metadata and signs the
   data-sharing agreement. Their organisation must be a GBIF publisher,
   endorsed by GBIF Sweden.
5. **Finish the metadata:** remove yourself from *Associated Parties* and end
   the description with:
   ```html
   <p>This dataset was published via the <a href="https://asv-portal.biodiversitydata.se/">SBDI ASV portal</a>.</p>
   ```

   If the IPT description editor strips HTML, edit the EML (DocBook) instead
   and import it, to keep links and lists. Do not save the description in the
   editor afterwards.
6. **Publish and register** from the resource overview: *Visibility → Public*,
   *Published Versions → Publish* (with a version note; review the report and
   DwC-A), then *Published Versions → Register*. Later publications update
   the registration automatically. Version notes can be edited afterwards in
   the version history on the resource page.
7. **Bioatlas ingestion:** email the Bioatlas team and check which resource
   ID (`drXXXX`) the dataset gets. It is stored with `make status` but not
   otherwise used by the portal.

### Going public in the ASV portal

Once the dataset is in the Bioatlas, set `in_bioatlas` and the Bioatlas and
IPT IDs. This includes it in BLAST, filter search, About stats and the
Download page:
```sh
make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
make stats
make blastdb
```
The pid is listed in the `make delete` menu (quit without deleting) and in
`api.annotation_overview`. Then tell the provider the data are published.

### Dataset exports

Build the DwC-like zips for the Download page:
```sh
make export             # all datasets with in_bioatlas = TRUE
make export ds="1 4"    # specific datasets (pids)
```
The zip holds the database data and the current IPT EML (version, citation,
description); only the DOI comes from GBIF, which has it once the dataset is
registered. Re-run the export whenever a public dataset changes.

After exporting, check:
- that the versions inside each zip agree (read-only):
  ```sh
  docker exec -i asv-main python3 - /app/data-volumes/exports < scripts/audit-export-versions.py
  ```
  `scripts/fix-export-readme.py` rebuilds a README citation from the IPT EML.
- that the README has a DOI. `DOI: N/A` means the dataset was not registered
  or the GBIF API did not respond; re-export.
- that GBIF has the IPT version (`version` in
  `https://api.gbif.org/v1/dataset/<uuid>`). After two quick publications it
  can lag one version until the next crawl.

## Maintaining imported data

The ASV portal, IPT, GBIF and Bioatlas are not synced automatically.
Coordinate with the Bioatlas team before changing public data, and log
post-import changes per IPT version.

### Edits after import

Edit imported data directly in the database, not via the dataset's R script.
For a public dataset, then:
1. Republish in the IPT with a version note.
2. `make export ds="<pid>"` (and `make stats` / `make blastdb` if affected).
3. Remind the Bioatlas team.
4. Log the change.

To **replace** a dataset:
1. Delete it first (see [Data deletions](#data-deletions)); the importer keeps
   existing annotations of ASVs already in the database.
2. Import the new version with the same datasetID.
3. Update the IPT data sources to the new pid, run `make status`, then
   republish and re-export as above.

### Taxonomic updates

Each new ASV gets a valid annotation in `taxon_annotation`;
`api.annotation_overview` shows reference database, ampliseq version and
classifier per dataset. Agree on the timing with the Bioatlas team first. To
re-annotate the ASVs of a target gene tied to a reference database:

1. **Export** the sequences:
   ```sh
   make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
   ```
2. **Annotate** with [nf-core/ampliseq](https://nf-co.re/ampliseq).
3. **Add target prediction fields** with
   `scripts/processing/reannotation-processing.R` (also applies the PR2/COIDB
   genus/species corrections), or by hand from the template
   `scripts/processing/output/reannotation.xlsx`.
4. **Import** in maintenance mode; old annotations get `status='old'`:
   ```sh
   make backup
   make main
   make reannot file=/path/to/reannotation.xlsx
   ```
   Check the result in `api.annotation_overview`.
5. **Republish** with `scripts/ipt-update/batch-update-ipt.py` (resource IDs
   and version notes in `resources.tsv`, see `resources.template`;
   credentials in `.ipt.cred`). It only starts the publications: check its
   output and `pub_info.tsv`, and wait until all have finished.
6. **Re-export** and finish:
   ```sh
   make export ds="<pids>"
   make blastdb
   make nomain
   make backup
   ```
7. **Check** the Download page and remind the Bioatlas team.

### Rebuilding the BLAST database

```sh
make blastdb
```
Includes ASVs from datasets with `in_bioatlas = TRUE` only. Runs
`blast_builder.py` in a blast-worker container via
`scripts/build_blast_db.py` (options in its `PARSER.add_argument` section).

### Data deletions

```sh
make delete      # or scripts/delete-dataset.sh
```
Interactive menu listing datasets by pid. Afterwards run `make stats`, and
`make blastdb` if the dataset was public.

## Background

### Target prediction filtering

All denoised sequences are imported, and ASVs not predicted to derive from the
target gene are filtered out of BLAST, filter search, result displays and IPT
views. An ASV's status can change, e.g. at re-annotation. Criteria vary by
gene, e.g. "annotated at least to kingdom OR barrnap-positive" for 16S rRNA.

Before import, each ASV gets:
- `annotation_target`: target gene of the reference database (e.g.
  `16S rRNA`), initially the dataset's `target_gene`.
- `target_prediction`: whether the ASV is predicted to derive from
  `annotation_target` (`TRUE`/`FALSE`).
- `target_criteria`: criteria for `TRUE` (e.g.
  `'Assigned kingdom OR Barrnap-positive'`, `'None: defaults to TRUE'`).

At import, these are compared with existing annotations:

```
--	target	pred	pred	pred	pred
db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneA	TRUE	TRUE	FALSE	FALSE
--	----	Ignore	Check	Check	Ignore

db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneB	TRUE	TRUE	FALSE	FALSE
--	----	Check	Update	ignore	Ignore
```

A TRUE prediction for a new target, where the existing annotation is FALSE, is
updated automatically. Other conflicts ("Check") stop the import with a table
of the affected ASVs; `--allow-conflicts` (`make conflict-import`) imports
anyway, keeping the existing annotation, and the marker should then be
re-annotated. Otherwise, incoming annotations of existing ASVs are never
stored, so they need not be edited to match the database. See
`compare_annotations` in `molmod/importer/importer.py`.

All views filter on:
```sql
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See `db/db-api-schema.sql`.
