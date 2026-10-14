# Data management

How a dataset goes from an uploaded file to a searchable, published dataset in
the ASV portal, and how imported data are maintained. Running the portal itself
is described in the main [README](../README.md).

## Workflow overview

1. **Preprocess and annotate** the uploaded file with the R scripts in
   `scripts/processing` (see [below](#preprocessing-and-annotation)).
2. **Confirm changes** made to the provider's data with the provider.
3. **Import** the resulting archive: dry-run locally, then import on the
   server (see [Importing](#importing)).
4. **Archive** the dataset folder (`scripts/processing/zip-ds.sh`).
5. **Publish** the dataset in the IPT and register it with GBIF (manual steps
   in the IPT), and ask the Bioatlas team to ingest it.
6. **Make the dataset public** in the portal and rebuild the BLAST database and
   About stats (see [Going public](#going-public)).
7. **Export** the download archive (see [Dataset exports](#dataset-exports)).

## Preprocessing and annotation

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
6. **Send the changes email** and wait for the provider's confirmation before
   importing. To send a draft (`.eml`), open it in Mac Mail and choose
   *Message → Send Again* (⇧⌘D), which gives an editable copy.

After the IPT resource has been created, `scripts/processing/email-generator.R`
drafts the email that hands the dataset over to the provider.

## Importing

The import archive is imported into the database by a Python script that
runs `importer.py` inside the main container. Check the
`PARSER.add_argument` section in the importer for available arguments, e.g.:
```
  $ ./scripts/import_excel.py /path/to/file.xlsx --dry-run -vv
```
Alternatively, use a Makefile rule, e.g.:
```
  $ make dry-import file=/path/to/file.tar.gz
  $ make import file=/path/to/file.xlsx
```

Dry-run against a local copy of the stack first; import on the server only
after a clean dry-run, and back up the database before (`make backup`).

Import includes some rudimentary validation (see e.g. regular expressions in
`./molmod/importer/data-mapping.json`), but this should be improved in the
future. Conflicting target predictions for pre-existing ASVs stop the import;
see [Target prediction filtering](#target-prediction-filtering).

## Going public

After importing, and publishing a dataset in the Bioatlas, you need to change
the `in_bioatlas` property to `true`, for data to be included in
`BLAST SEARCH`, `FILTER SEARCH` and `ABOUT` page stats. You also need to add
Bioatlas and IPT resource IDs, for the `DOWNLOAD DATA` page to work:
```
  $ make status pid=3 status=1 ruid=dr963 ipt=kth-2013-baltic-18s
```
The dataset `pid` is shown in the `make delete` menu (quit without deleting)
and in the view `api.annotation_overview`. Then update the About stats and
rebuild the BLAST database:
```
  $ make stats
  $ make blastdb
```

## BLAST-database generation
Generate a new BLAST database (including ASVs from datasets that have been
imported into the Bioatlas only) using a script that executes
`blast_builder.py` inside a blast-worker container. Again, check the
`PARSER.add_argument` section for available arguments, which can be added to
main function call like so:
```
  $ ./scripts/build_blast_db.py -vv
```
or:
```
  $ make blastdb
```

## Dataset exports
To export condensed DwC-like dataset archives (zips) and make these available
in the `Download` page, use the following `Makefile` target:
```
  $ make export             # All datasets
  $ make export ds="1 4"    # Specific dataset (pid:s)
```

## Target prediction filtering
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

For example, in the top left case, an ASV in a new dataset comes in with an annotation for geneA, is also predicted to be a TRUE geneA sequence, and this corresponds with what is already noted in the database for that ASV, so we do nothing (the existing annotation remains). If, instead, a new dataset has a TRUE geneB prediction for an ASV that has previously been considered a FALSE geneA, this annotation can be automatically updated. Other conflicts (a same-target prediction flip, or two targets both predicted TRUE) cancel the import by default, with a printed table of the affected ASVs. Re-run with `--allow-conflicts` (`make conflict-import`) to import anyway — those ASVs keep their existing database annotation, the table is printed as a warning, and the marker should be re-annotated afterwards. Note that the importer never stores the incoming annotation (taxonomy or target prediction) of a pre-existing ASV, except in the automatic update case above, so there is no need to edit incoming target predictions to match the database before importing. See `/molmod/importer/importer.py` and function `compare_annotations` for details.

After import, we filter all database views with an extended WHERE clause:
```sql
WHERE ta.status::text = 'valid'
    -- Criteria added for target prediction:
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
```
See `/db/db-api-schema.sql`.

## Taxonomic (re)annotation
On import, each **new** ASV gets a row in table `taxon_annotation` (standard SBDI annotation, updated as reference DBs/algorithms evolve). The current reference database, ampliseq version and classifier per dataset are listed in the view `api.annotation_overview`.

To re-annotate ASVs for a given target gene currently tied to a specific reference DB:
  1) Export FASTA:
     ```
     make fasta ref="SBDI-GTDB-R07-RS207-1" target="16S rRNA"
     ```
  2) Run the FASTA with [nf-core/ampliseq](https://nf-co.re/ampliseq).
  3) Since Ampliseq output doesn’t yet include fields from `Target prediction filtering` (as of 250904), either:
     - add them via `./scripts/processing/reannotation-processing.R` (which also applies the PR2/COIDB genus/species corrections), or
     - use `./scripts/processing/output/reannotation.xlsx` as a template and edit your own file.
  4) Import:
     ```
     make reannot file=/path/to/reannotation.xlsx
     ```
Previous annotations are marked `status='old'`; new rows get `status='valid'`.

## Data deletions
You can delete single datasets with an interactive script:
```
  $ scripts/delete-dataset.sh
```
or:
```
  $ make delete
```
Both commands will bring up a menu with instructions for how to proceed with deletions. Remember to update stats accordingly (`make stats`).
