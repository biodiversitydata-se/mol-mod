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

Uploaded files are processed with `scripts/processing/asv-input-processing.R`,
which turns the provider's sheets into an import archive. A dated copy of the
script is kept with each dataset, for reproducibility. Setup, the helper
scripts and the checks are described in
[`scripts/processing/README.md`](../scripts/processing/README.md); the dummy
data in `scripts/processing/input` can be used for testing.

Work in a folder per dataset, outside the repository:

```
<datasetID>/
├── asv-input-processing-<YYMMDD>.R
├── input/      # uploaded file (name unchanged); later annotation.tsv, ASV_tax.*.tsv
├── ampliseq/   # params.yaml
└── output/     # <datasetID>.fasta, <datasetID>-adm.xlsx, <datasetID>-adm.tar.gz
```

1. Copy `asv-input-processing.R` into the folder as
   `asv-input-processing-<YYMMDD>.R` and edit section 1.
2. **First pass:** source the script. Without `input/annotation.tsv` it stops
   after section 11, having written the fasta, `ampliseq/params.yaml` and
   `output/submission-checks.txt`, and asks for the ampliseq version
   (Enter = latest release).
3. **Review** the output and the submission checks. Correct the provider's
   data in section 14 with `change_value()`.
4. **Annotate** with nf-core/ampliseq on the HPC cluster, from the dataset
   folder:
   ```sh
   ampliseq-hpc.sh push     # copy params.yaml and fasta to the cluster
   ampliseq-hpc.sh start    # run ampliseq in a detached screen session
   ampliseq-hpc.sh status   # repeat until annotation.tsv is present
   ampliseq-hpc.sh fetch    # copy annotation.tsv (and ASV_tax.*.tsv) to input/
   ```
5. **Second pass:** source the script again; it now runs to the end and
   writes `output/<datasetID>-adm.tar.gz`, `output/changes.txt` and, if
   anything was changed, `draft_changes_email.eml`.

### Importing

The import archive is imported into the database by a Python script that
runs `importer.py` inside the main container. Check the
`PARSER.add_argument` section in the importer for available arguments, e.g.:
```sh
./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```
Alternatively, use a Makefile rule, e.g.:
```sh
make dry-import file=/path/to/file.tar.gz
make import file=/path/to/file.xlsx
```

1. **Dry-run** against a local copy of the stack and resolve any validation
   errors and target-prediction conflicts (see
   [Target prediction filtering](#target-prediction-filtering)).
2. **Confirm changes** with the provider: if `output/changes.txt` lists
   changes, send `draft_changes_email.eml` and wait for the provider's
   agreement before importing. Doing this after the dry-run keeps all
   corrections in one email. To send a draft (`.eml`), open it in Mac Mail and
   choose *Message → Send Again* (⇧⌘D), which gives an editable copy.
3. **Import** on the server, after a clean dry-run and a backup
   (`make backup`).

Import includes some rudimentary validation (see e.g. regular expressions in
`./molmod/importer/data-mapping.json`), but this should be improved in the
future. Conflicting target predictions for pre-existing ASVs stop the import;
`make conflict-import` imports anyway (see
[Target prediction filtering](#target-prediction-filtering)).

### Archiving

After a successful import, move the dataset folder from the pending area to
`Imported/` and zip the uploaded file, the annotation and the dated R scripts
for reproducibility:
```sh
scripts/processing/zip-ds.sh <datasetID>   # run from the folder containing Imported/
```
The zip contains `input/` and all `*.R` files (not `output/`, which can be
regenerated). Copy it to the archive folder on the server, which is included in
the server backups.

### Publishing in the IPT and GBIF

Datasets are published through the Swedish IPT (`https://www.gbif.se/ipt/`).
Most steps are manual in the IPT interface; see the
[IPT manual](https://ipt.gbif.org/manual/en/ipt/latest/) for details.

1. **Create three SQL data sources**, for occurrence, emof and mixs (DNA)
   data, from the views `api.dwc_oc_occurrence`, `api.dwc_oc_emof` and
   `api.dwc_oc_mixs`, filtered on the dataset:
   ```sql
   SELECT * FROM api.dwc_oc_occurrence
   WHERE dataset_pid = <pid> AND "datasetID" = '<datasetID>'
   ```
   The datasetID condition is a safeguard: with a wrong pid the source is
   empty instead of showing another dataset. If a dataset is deleted and
   re-imported, it gets a new pid; update all three sources (an empty source is
   the sign), or filter on `"datasetID"` only.
2. **Create the resource.** Use the provider's datasetID; its lowercase form
   is the IPT short name (`ipt_resource_id`). Early datasets were given
   `SBDI-ASV-<N>` IDs by us instead.
3. **Map the fields.** For 18S data, do **not** map `kingdom` and `phylum`:
   they make GBIF/Bioatlas name matching markedly worse.
4. **Hand over to the provider.** Add the provider as an IPT user with the
   role *Manager without registration rights*, and email them.
   `scripts/processing/email-generator.R` drafts the email (dataset-specific
   links and IPT login) in the R session of the second pass; see
   [`scripts/processing/README.md`](../scripts/processing/README.md). The
   provider describes the dataset in the IPT metadata, and signs the
   data-sharing agreement. If their organisation is not yet a GBIF publisher,
   it needs to be registered and endorsed by GBIF Sweden before it can be
   selected in the IPT.
5. **Finish the metadata.** Add this sentence at the very end of the
   description, and remove your own name from *Associated Parties* if it was
   added:
   > This dataset was published via the SBDI ASV portal
   > (https://asv-portal.biodiversitydata.se/).

   The description editor in the IPT strips HTML on save. To keep links and
   lists, edit the description in the EML file (DocBook: `para`,
   `ulink`/`citetitle`, `itemizedlist`/`listitem`) and import it instead.
6. **Publish and register**, once the metadata is complete and the agreement
   is signed, in this order from the resource overview:
   1. *Visibility → Public*
   2. *Published Versions → Publish*, with a version note (change summary)
      describing what changed. Review the publishing report and the
      resulting DwC-A.
   3. *Published Versions → Register*

   GBIF crawls the resource shortly after registration. Later publications
   update the GBIF registration automatically. Version notes can be edited
   afterwards on the resource homepage (version history), when logged in as
   a manager.
7. **Bioatlas ingestion.** The Bioatlas picks up datasets that are new or
   changed in GBIF, but remind the Bioatlas team anyway, e.g. with an issue
   labelled `DataMobilization` in
   [sbdi-bioatlas](https://github.com/biodiversitydata-se/sbdi-bioatlas/labels/DataMobilization).
   They confirm ingestion and give the Bioatlas resource ID (`drXXXX`).

### Going public in the ASV portal

After importing, and publishing a dataset in the Bioatlas, you need to change
the `in_bioatlas` property to `true`, for data to be included in
`BLAST SEARCH`, `FILTER SEARCH` and `ABOUT` page stats. You also need to add
Bioatlas and IPT resource IDs, for the `DOWNLOAD DATA` page to work:
```sh
make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
```
The dataset `pid` is shown in the `make delete` menu (quit without deleting)
and in the view `api.annotation_overview`. Then update the About stats and
rebuild the BLAST database (see
[Rebuilding the BLAST database](#rebuilding-the-blast-database)):
```sh
make stats
make blastdb
```
Then let the provider know that their data are published.

### Dataset exports

To export condensed DwC-like dataset archives (zips) and make these available
in the `Download` page, use the following `Makefile` target:
```sh
make export             # All datasets
make export ds="1 4"    # Specific dataset (pid:s)
```
Without `ds`, all datasets with `in_bioatlas = TRUE` are exported.

The zip is a snapshot of the database and the current IPT metadata (version,
citation and description from the IPT EML; only the DOI comes from GBIF).
Re-run the export whenever a public dataset changes (see
[Edits after import](#edits-after-import)); otherwise the `Download` page
keeps serving the old version.

To check that the versions inside each zip agree (EML packageId, EML citation
and README citation), run the read-only audit script against the exports
volume on the server:
```sh
docker exec -i asv-main python3 - /app/data-volumes/exports < scripts/audit-export-versions.py
```
`scripts/fix-export-readme.py` rebuilds an export's README citation from the
IPT EML. The audit does not compare with GBIF. After republishing, also check
that GBIF has picked up the IPT version (`version` in
`https://api.gbif.org/v1/dataset/<uuid>`). If a resource is published twice
in quick succession, GBIF may crawl between the two and stay one version
behind until its next scheduled crawl.

## Maintaining imported data

There is no automatic version sync between the ASV portal, the IPT, GBIF and
the Bioatlas. Coordinate with the Bioatlas team before changing data that are
already public, and keep a log of post-import changes per IPT version.

### Edits after import

Fix imported data directly in the database rather than by re-running an old
preprocessing script: the general part of the script changes over time, so old
dataset scripts cannot be re-run against a newer template or database. For a
public dataset, then:
1. Republish the resource in the IPT, with a version note describing the
   change.
2. Re-export the dataset (`make export ds="<pid>"`), and run `make stats` /
   `make blastdb` if the change affects them.
3. Remind the Bioatlas team to re-ingest the dataset.
4. Log the change.

To **replace** a dataset with a reprocessed version, delete the old dataset
first (see [Data deletions](#data-deletions)) and keep its datasetID, so that
occurrence and event IDs stay stable. The importer keeps the existing
annotation of ASVs that are already in the database, so importing before
deleting would not update them. The new import gets a new pid: update the IPT
data sources and `make status`, then republish and re-export as above.

### Taxonomic updates

On import, each **new** ASV gets a row in table `taxon_annotation` (standard
SBDI annotation, updated as reference databases and algorithms evolve). The
current reference database, ampliseq version and classifier per dataset are
listed in the view `api.annotation_overview`.

The Bioatlas lags behind the portal until it has re-ingested the republished
datasets, so agree on the timing with the Bioatlas team first. To re-annotate
the ASVs of a target gene that are currently tied to a specific reference
database:

1. **Export** the sequences to a FASTA file:
   ```sh
   make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
   ```
2. **Annotate** the FASTA with [nf-core/ampliseq](https://nf-co.re/ampliseq).
3. **Add target prediction fields**, which ampliseq output does not include
   (see [Target prediction filtering](#target-prediction-filtering)), either:
   - with `scripts/processing/reannotation-processing.R`, which also applies
     the PR2/COIDB genus/species corrections, or
   - by hand, using `scripts/processing/output/reannotation.xlsx` as a
     template.
4. **Import** the new annotation, after a backup and in maintenance mode:
   ```sh
   make backup
   make main
   make reannot file=/path/to/reannotation.xlsx
   ```
   Previous annotations are marked `status='old'` and new rows get
   `status='valid'`. Check the result in `api.annotation_overview`.
5. **Republish** the affected datasets in the IPT with
   `scripts/ipt-update/batch-update-ipt.py`, which reads IPT resource IDs and
   version notes from `resources.tsv` (see `resources.template`) and
   credentials from `.ipt.cred`. The script only starts the publications:
   check its output and `pub_info.tsv`, fix any problems in the IPT
   interface, and wait until all publications have finished.
6. **Re-export** the datasets, rebuild the BLAST database, end maintenance
   mode and back up:
   ```sh
   make export ds="<pids>"
   make blastdb
   make nomain
   make backup
   ```
7. **Check** the `Download` page, and remind the Bioatlas team to re-ingest
   the datasets.

### Rebuilding the BLAST database

The BLAST database includes ASVs from datasets that are in the Bioatlas
(`in_bioatlas = TRUE`) only. Rebuild it after making a dataset public and after
changes that affect sequences or annotations:
```sh
make blastdb
```
This runs `scripts/build_blast_db.py`, which executes `blast_builder.py` in a
blast-worker container; see its `PARSER.add_argument` section for options
(e.g. `./scripts/build_blast_db.py -vv`).

### Data deletions

Delete a single dataset with the interactive menu (or
`scripts/delete-dataset.sh`):
```sh
make delete
```
The menu lists datasets by pid; quitting without deleting is a quick way to
look up a pid. Rebuild the About stats afterwards (`make stats`), and the
BLAST database if the dataset was public.

## Background

### Target prediction filtering

In version 2.0.0, we make it possible to import all denoised sequences from a
dataset, and then dynamically filter out any ASVs that we do not (currently)
predict to derive from the targeted gene, thereby excluding these from BLAST
and filter searches, result displays and IPT views. ASVs are thus only imported
once, but their status can change, e.g. at taxonomic re-annotation. Criteria
used for ASV exclusion may vary between genes / groups of organisms, but could
e.g. combine the output from the *BAsic Rapid Ribosomal RNA Predictor
(barrnap)* with the taxonomic annotation itself. For example, we may decide
that only ASVs that are annotated at least at kingdom level OR get positive
barrnap prediction should be considered as TRUE 16S rRNA sequences.

We implement this as follows:

Before import of a new dataset, we add the following annotation data to each
ASV:
- `annotation_target` = target gene of reference database used for taxonomic
  annotation (eg. `16S rRNA`). At this stage, `annotation_target` will equal
  the `target_gene` of the dataset.
- `target_prediction` = whether the ASV is predicted to derive from the
  annotation_target (`TRUE/FALSE`).
- `target_criteria` = criteria used for setting `target_prediction` to `TRUE`
  (eg. `'Assigned kingdom OR Barrnap-positive'`, or `'None: defaults to
  TRUE'`).

During import, we compare annotation targets and predictions of ASVs in new
datasets to annotations that already exist in db, with the following possible
outcomes and responses:

```
--	target	pred	pred	pred	pred
db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneA	TRUE	TRUE	FALSE	FALSE
--	----	Ignore	Check	Check	Ignore

db	geneA	TRUE	FALSE	TRUE	FALSE
new	geneB	TRUE	TRUE	FALSE	FALSE
--	----	Check	Update	ignore	Ignore
```

For example, in the top left case, an ASV in a new dataset comes in with an
annotation for geneA, is also predicted to be a TRUE geneA sequence, and this
corresponds with what is already noted in the database for that ASV, so we do
nothing (the existing annotation remains). If, instead, a new dataset has a
TRUE geneB prediction for an ASV that has previously been considered a FALSE
geneA, this annotation can be automatically updated. Other conflicts (a
same-target prediction flip, or two targets both predicted TRUE) cancel the
import by default, with a printed table of the affected ASVs. Re-run with
`--allow-conflicts` (`make conflict-import`) to import anyway — those ASVs keep
their existing database annotation, the table is printed as a warning, and the
marker should be re-annotated afterwards. Note that the importer never stores
the incoming annotation (taxonomy or target prediction) of a pre-existing ASV,
except in the automatic update case above, so there is no need to edit incoming
target predictions to match the database before importing. See
`/molmod/importer/importer.py` and function `compare_annotations` for details.

After import, we filter all database views with an extended WHERE clause:
```sql
WHERE ta.status::text = 'valid'
    -- Criteria added for target prediction:
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See `/db/db-api-schema.sql`.
