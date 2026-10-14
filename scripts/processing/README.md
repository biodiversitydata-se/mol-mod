# Data processing for ASV portal imports

Scripts for turning an uploaded file into an import archive, including
taxonomic annotation with [nf-core/ampliseq](https://nf-co.re/ampliseq) on an
HPC cluster. Importing the archive is described in the main
[README](../../README.md#data-import).

| File | Purpose |
| --- | --- |
| `asv-input-processing.R` | Main script; a dated copy is kept with each dataset |
| `ampliseq-config-generator.R` | Writes `ampliseq/params.yaml` (sourced by the main script) |
| `ampliseq-hpc.sh` | Runs ampliseq on the cluster: `push`, `start`, `status`, `fetch` |
| `submission-checks.R` | Lists likely mistakes in the submitted data for review (sourced) |
| `change-log.R` | Logs corrections of the provider's data: `change_value()` (sourced) |
| `changes-email-generator.R`, `changes-email-template.html` | Draft email asking the provider to confirm the changes before import (sourced) |
| `asv-db-query.R` | Read-only queries to the ASV portal database (sourced) |
| `taxonomy-corrections.R`, `pr2-correction-lookup.tsv` | Fix genus/species splitting for PR2 and COIDB (sourced) |
| `output-checks.R` | Compares counts across output tables (sourced) |
| `email-generator.R`, `email-template.html` | Draft email to the data provider |
| `zip-ds.sh` | Archives imported datasets for reproducibility |
| `reannotation-processing.R` | Prepares re-annotations for `make reannot` |
| `input/`, `output/` | Dummy data for testing |

## One-time setup

**R** needs `data.table`, `openxlsx` and `jsonlite`. Personal and site-specific
settings go in your `~/.Renviron`: copy the lines from
[`.Renviron.template`](.Renviron.template), fill in the values (open the file
with `usethis::edit_r_environ()`) and restart R. Keep comments on their own
lines; R does not strip comments after a value.

`~/.Renviron` is read only by R. `ampliseq-hpc.sh` reads shell variables
(`AMPLISEQ_*`, see below), which are only needed to change its defaults.

**SSH** aliases in `~/.ssh/config`; the defaults are for Dardel (PDC):

```
Host dardel
  User <user>
  Hostname dardel.pdc.kth.se
Host dardel-ft
  User <user>
  Hostname dardel-ftn01.pdc.kth.se
```

PDC only accepts IP addresses registered in its
[login portal](https://loginportal.pdc.kth.se/) ("unauthorized system" means
the current address must be added).

**On the cluster**, all runs share one Nextflow environment file (default
`~/SBDI/asv-portal/nxf_env`) that keeps Nextflow and container files in
project storage:

```sh
export NXF_OPTS='-Xms1g -Xmx4g'
export NXF_HOME='<project storage>/asv-portal/nxf_files'
export APPTAINER_CACHEDIR="$NXF_HOME/cache/apptainer"
export NXF_SINGULARITY_CACHEDIR="$NXF_HOME/cache/singularity"
export SINGULARITY_CACHEDIR="$NXF_SINGULARITY_CACHEDIR"
export TMPDIR="$NXF_HOME/tmp"
export APPTAINER_TMPDIR="$TMPDIR"
export SINGULARITY_TMPDIR="$TMPDIR"
```

Optional: `alias ampliseq-hpc=/path/to/mol-mod/scripts/processing/ampliseq-hpc.sh`
in `~/.bash_profile`.

## Processing a dataset

Work in a folder per dataset, outside the repository:

```
<datasetID>/
├── asv-input-processing-<YYMMDD>.R
├── input/      # uploaded file (name unchanged); later annotation.tsv, ASV_tax.*.tsv
├── ampliseq/   # params.yaml
└── output/     # <datasetID>.fasta, <datasetID>-adm.xlsx, <datasetID>-adm.tar.gz
```

1. Copy `asv-input-processing.R` into the folder as
   `asv-input-processing-<YYMMDD>.R`; edit section 1 and, if needed,
   section 14 (dataset-specific fixes).
2. **First pass:** source the script. Without `input/annotation.tsv` it stops
   after section 11, having written the fasta and `ampliseq/params.yaml`, and
   asks for the ampliseq version (Enter = latest release).
3. **Review** the output, `params.yaml` and `output/submission-checks.txt`
   (see below). Correct the provider's data in section 14 with
   `change_value()`.
4. **Annotate**, from the dataset folder:
   ```sh
   ampliseq-hpc.sh push     # copy params.yaml and fasta to the cluster
   ampliseq-hpc.sh start    # run ampliseq in a detached screen session
   ampliseq-hpc.sh status   # repeat until annotation.tsv is present
   ampliseq-hpc.sh fetch    # copy annotation.tsv (and ASV_tax.*.tsv) to input/
   ```
5. **Second pass:** source the script again; it now runs to the end and
   writes `output/<datasetID>-adm.tar.gz`, `output/changes.txt` and, if
   anything was changed, `draft_changes_email.eml`.
6. Send the changes email and wait for the provider's confirmation. To send
   a draft (`.eml`), open it in Mac Mail and choose *Message → Send Again*
   (⇧⌘D), which gives an editable copy.
7. Import (main README), archive with `zip-ds.sh`, and draft the provider
   email with `email-generator.R` once the IPT resource exists.

## Checks and changes

The main script stops on errors that rule out a valid import (missing sheets
or columns, duplicated IDs, ASVs with reads but no sequence).
`submission-checks.R` lists likely mistakes that need judgement in
`output/submission-checks.txt` (in both passes):

- **WARN**: probably wrong, e.g. a primer name that in the database belongs to
  another sequence, a marker that differs from section 1, duplicated ENA
  links, swapped coordinates, non-integer counts, samples or ASVs that differ
  between sheets.
- **REVIEW**: new or unusual values to check by hand, e.g. primers, markers or
  institutions not yet in the database (with the organisation name from ROR),
  or columns that vary between samples where Excel autofill may have been used.

Correct the data in section 14 with
`change_value(table, field, old, new, reason)`, e.g.
`change_value(dna, "pcr_primer_reverse", "GGACTACHVGGGTWTCTAAT", "GACTACHVGGGTATCTAATCC", "Primer sequence did not match the primer name (805R)")`.
Each change is listed in `output/changes.txt` and in the email draft, by the
provider's sheet names.

## Annotation settings

`ampliseq-config-generator.R` reads `api.annotation_overview` on the server
(read-only) and uses the setup shared by most ampliseq-annotated datasets with
the same marker, so new datasets match existing ones: reference database
(e.g. `PR2 v5.1.0` → `pr2=5.1.0`), classifier (`DADA2:assignTaxonomy` →
`dada_ref_taxonomy`; `VSEARCH:sintax` → `sintax_ref_taxonomy` +
`skip_dada_taxonomy`) and options (`cut_its`). Presets add `addsh` (ITS) and
`skip_barrnap` (ITS, COI); primers come from the dataset. Without a server
connection, fallback presets are used with a warning; keep them current after
re-annotations.

## Running on the cluster

`start` runs `nextflow run nf-core/ampliseq -r <version> -profile <profile>
-params-file params.yaml -resume` in a `screen` session named after the
dataset, with all output in `run.log`. `-resume` means `start` also continues
a failed run. `fetch` will not overwrite `input/annotation.tsv` without `-f`.

Defaults (Dardel), overridable as shell variables:

| Variable | Default |
| --- | --- |
| `AMPLISEQ_CONFIG_DIR` | `ampliseq` (set the same in `~/.Renviron` if changed) |
| `AMPLISEQ_SSH_HOST` / `AMPLISEQ_TRANSFER_HOST` | `dardel` / `dardel-ft` |
| `AMPLISEQ_REMOTE_DIR` | `SBDI/asv-portal/initial-annotations` (relative to remote home) |
| `AMPLISEQ_NXF_ENV` | `SBDI/asv-portal/nxf_env` |
| `AMPLISEQ_MODULES` | `PDC nextflow/25.10.4 apptainer java/17` |
| `AMPLISEQ_PROFILE` | `pdc_kth` |

To move to another cluster (e.g. Arrhenius, profile `naiss`), change these
defaults and create the environment file there.

**Troubleshooting**

- Screen window silent or showing "Lmod is automatically replacing ...":
  harmless; output is in `run.log` (`ampliseq-hpc.sh status`, or
  `tail -n 30 run.log` in the remote dataset folder).
- Jobs `PENDING`: queued (`squeue -u $USER`).
- `retries: 1` on a task is normal. If the run fails, read the end of
  `run.log`, fix, and `start` again.
- Jobs rejected for the account: check `NAISS_PROJECT` / `project:` in
  `params.yaml`.

## Taxonomy corrections

ampliseq's SBDI export mis-splits some names into genus and epithets:

- **PR2** (18S): inconsistent underscores and genus names
  ([pr2database#56](https://github.com/pr2database/pr2database/issues/56),
  [ampliseq#921](https://github.com/nf-core/ampliseq/issues/921)). Known cases
  are fixed from `pr2-correction-lookup.tsv`.
- **COIDB** (COI): genera like `Naididae_X` end up as epithets
  ([ampliseq#923](https://github.com/nf-core/ampliseq/issues/923)); fixed by
  rule.

For PR2, the run's `input/ASV_tax.pr2_*.tsv` (DADA2 output, fetched by
`fetch`) is checked against the lookup table, with a warning for uncovered
genus/species combinations. Check them, add rows to
`pr2-correction-lookup.tsv`, commit, and rerun the second pass.

`reannotation-processing.R` applies the same corrections; put the run's
`results/dada2/ASV_tax.pr2_*.tsv` in its `input/` for the PR2 check.
