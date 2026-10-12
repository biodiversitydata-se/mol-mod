# Script for generating the nf-core/ampliseq params.yaml for taxonomic annotation
# of a dataset's fasta on the HPC cluster.
# Expects objects dataset, dna and marker from asv-input-processing.R (run
# through section 11), and is sourced from the dataset folder, e.g.:
#   source("<path-to-mol-mod>/scripts/processing/ampliseq-config-generator.R")
# The file is written to ampliseq/params.yaml in the dataset folder.
#
# Reference database and classifier are taken from the
# annotations currently used for the same marker in the ASV portal database
# (view api.annotation_overview), so that new datasets are annotated like
# existing ones. If the database cannot be reached, or has no datasets for the
# marker, fallback presets are used and a warning is given.
#
# The ampliseq version to run is asked for interactively, with the latest
# release on GitHub as default.
#
# Site-specific settings are read from environment variables (e.g. set in
# ~/.Renviron), so that no project IDs or host names are stored in the repo:
#   NAISS_PROJECT     NAISS compute project, billed for the run (required)
#   AMPLISEQ_CONFIG_DIR  local folder for params.yaml (default: ampliseq)
#   ASV_DB_SSH_HOST   ssh host (alias) of the ASV portal server, or 'local' to
#                     query a local asv-db container (optional; if unset,
#                     fallback presets are used)

library(data.table)

# Folder of this script when sourced (innermost source() call), else the
# working directory
config_generator_dir <- local({
  dir <- "."
  for (i in rev(seq_len(sys.nframe()))) {
    f <- sys.frame(i)$ofile
    if (!is.null(f)) {
      dir <- dirname(f)
      break
    }
  }
  dir
})
source(file.path(config_generator_dir, "asv-db-query.R"))

config_dir <- Sys.getenv("AMPLISEQ_CONFIG_DIR", "ampliseq")
naiss_project <- Sys.getenv("NAISS_PROJECT")
db_host <- Sys.getenv("ASV_DB_SSH_HOST")
if (naiss_project == "") {
  stop("Set environment variable NAISS_PROJECT (e.g. in ~/.Renviron)")
}

# Per-marker settings. 'pattern' is matched (case-insensitively) against the
# marker set in section 1 of the R script. 'options' are always applied, as
# they cannot be derived from the database (e.g. addsh only shows up there if
# some ASV got an SH hit). 'fallback' is used only when the database gives no
# answer, and should be kept in line with current practice.
marker_presets <- list(
  list(
    pattern = "^16S",
    options = list(),
    fallback = list(db = "SBDI-GTDB-R11-RS232-1", classifier = "DADA2:assignTaxonomy",
                    options = NA, algo = "Ampliseq v2.18.0")
  ),
  list(
    pattern = "^18S",
    options = list(),
    fallback = list(db = "PR2 v5.1.0", classifier = "DADA2:assignTaxonomy",
                    options = NA, algo = "Ampliseq v2.14.0")
  ),
  list(
    pattern = "^ITS",
    options = list(addsh = TRUE, skip_barrnap = TRUE),
    fallback = list(db = "UNITE-alleuk v10.0", classifier = "DADA2:assignTaxonomy",
                    options = "cut_its:its2", algo = "Ampliseq v2.16.1")
  ),
  list(
    pattern = "^CO(I|1)",
    options = list(skip_barrnap = TRUE),
    fallback = list(db = "COIDB 221216", classifier = "VSEARCH:sintax",
                    options = NA, algo = "Ampliseq v2.12.0")
  )
)

get_marker_preset <- function(marker) {
  for (preset in marker_presets) {
    if (grepl(preset$pattern, marker, ignore.case = TRUE)) {
      return(preset)
    }
  }
  stop(
    "No ampliseq preset matches marker '", marker, "'. Known patterns: ",
    paste(sapply(marker_presets, `[[`, "pattern"), collapse = ", ")
  )
}

# Current annotation setups per marker from api.annotation_overview, or NULL
# (with a warning) if the database cannot be reached
query_annotation_overview <- function(host) {
  sql <- paste(
    "SELECT annotation_target, db, algo, classifier, options, count(*) AS n_datasets",
    "FROM api.annotation_overview GROUP BY 1, 2, 3, 4, 5;"
  )
  overview <- query_asv_db(sql, host)
  if (is.null(overview)) {
    warning("Using fallback presets for the annotation setup")
    return(NULL)
  }
  overview[, n_datasets := as.integer(n_datasets)]
  overview[options == "", options := NA_character_]
  overview
}

# Latest nf-core/ampliseq release on GitHub, or NA if it cannot be fetched
latest_ampliseq_release <- function() {
  old <- options(timeout = 10)
  on.exit(options(old))
  json <- tryCatch(
    suppressWarnings(readLines("https://api.github.com/repos/nf-core/ampliseq/releases/latest")),
    error = function(e) NULL
  )
  tag <- regmatches(json, regexpr('"tag_name": *"[^"]+"', json))
  if (length(tag) == 0) {
    return(NA_character_)
  }
  sub('.*"([^"]+)"$', "\\1", tag[1])
}

# Ask for the ampliseq version to run, defaulting to the latest release (or,
# if GitHub cannot be reached, the version used for existing annotations)
choose_ampliseq_version <- function(annotation) {
  default <- latest_ampliseq_release()
  if (is.na(default)) {
    default <- sub("^Ampliseq v", "", annotation$algo)
    warning("Could not fetch the latest ampliseq release; defaulting to ", default)
  }
  if (!interactive()) {
    return(default)
  }
  answer <- trimws(readline(paste0(
    "ampliseq version to run (existing annotations: ", annotation$algo,
    ") [", default, "]: "
  )))
  if (answer == "") default else sub("^v", "", answer)
}

# Pick the annotation setup used by most datasets with the same marker.
# Only ampliseq annotations are considered; datasets that keep a provider's
# own taxonomy (e.g. algo 'custom-IBA', no classifier) are ignored.
select_annotation <- function(overview, marker, preset) {
  if (is.null(overview)) {
    return(preset$fallback)
  }
  rows <- overview[annotation_target == marker & grepl("^Ampliseq", algo) &
                     !is.na(classifier) & classifier != ""]
  if (nrow(rows) == 0) {
    warning("No datasets with annotation_target '", marker, "' in the database; using fallback presets")
    return(preset$fallback)
  }
  rows <- rows[order(-n_datasets)]
  if (nrow(rows) > 1) {
    warning(
      "Datasets with marker '", marker, "' are annotated in different ways; using the most common:\n",
      paste(capture.output(print(rows)), collapse = "\n")
    )
  }
  as.list(rows[1, .(db, classifier, options, algo)])
}

# Translate a reference database name as stored in asv-db into an ampliseq
# taxonomy option value, e.g. 'PR2 v5.1.0' -> 'pr2=5.1.0'
db_to_ampliseq <- function(db) {
  db_patterns <- c(
    "^SBDI-GTDB-(.+)$" = "sbdi-gtdb=\\1",
    "^PR2 v(.+)$" = "pr2=\\1",
    "^UNITE-(alleuk|fungi) v(.+)$" = "unite-\\1=\\2",
    "^COIDB (.+)$" = "coidb=\\1"
  )
  for (p in names(db_patterns)) {
    if (grepl(p, db)) {
      return(sub(p, db_patterns[[p]], db))
    }
  }
  stop("Unknown reference database '", db, "'; add it to db_to_ampliseq()")
}

# Translate database name, classifier and run options into ampliseq parameters
annotation_to_params <- function(annotation) {
  ref <- db_to_ampliseq(annotation$db)
  classifier <- annotation$classifier
  params <- if (identical(classifier, "VSEARCH:sintax")) {
    list(sintax_ref_taxonomy = ref, skip_dada_taxonomy = TRUE)
  } else if (identical(classifier, "DADA2:assignTaxonomy")) {
    list(dada_ref_taxonomy = ref)
  } else {
    stop("Unknown or mixed classifier '", classifier, "'")
  }
  options <- if (is.na(annotation$options)) "" else annotation$options
  cut_its <- regmatches(options, regexpr("(?<=cut_its:)[a-z0-9]+", options, perl = TRUE))
  if (length(cut_its) == 1) {
    params$cut_its <- cut_its
  }
  params
}

get_primer <- function(dna, field) {
  primer <- unique(na.omit(trimws(as.character(dna[[field]]))))
  primer <- primer[primer != ""]
  if (length(primer) != 1) {
    stop(
      "Expected exactly one value in dna$", field, ", found ", length(primer),
      if (length(primer) > 0) paste0(": ", paste(primer, collapse = ", "))
    )
  }
  if (!grepl("^[ACGTURYSWKMBDHVNI]+$", primer, ignore.case = TRUE)) {
    stop("dna$", field, " contains non-IUPAC characters: ", primer)
  }
  toupper(primer)
}

format_yaml_value <- function(value) {
  if (is.logical(value)) {
    return(tolower(as.character(value)))
  }
  paste0('"', value, '"')
}

write_ampliseq_config <- function(dataset, dna, marker) {
  dataset_id <- dataset$datasetID
  preset <- get_marker_preset(marker)
  annotation <- select_annotation(query_annotation_overview(db_host), marker, preset)
  ampliseq_version <- choose_ampliseq_version(annotation)

  params <- c(
    list(
      project = naiss_project,
      input_fasta = paste0(dataset_id, ".fasta"),
      outdir = "results",
      skip_qiime = TRUE,
      sbdiexport = TRUE
    ),
    annotation_to_params(annotation),
    preset$options,
    list(
      FW_primer = get_primer(dna, "pcr_primer_forward"),
      RV_primer = get_primer(dna, "pcr_primer_reverse")
    )
  )

  # The ampliseq version to run is kept as a comment, for use when starting the
  # run, together with the existing annotation the settings are based on
  header <- c(
    paste0("# ampliseq_version: ", ampliseq_version),
    paste0(
      "# Based on: ", annotation$db, " / ", annotation$classifier,
      if (!is.na(annotation$options) && annotation$options != "") paste0(" ", annotation$options),
      " / ", annotation$algo
    )
  )
  params_lines <- paste0(names(params), ": ", sapply(params, format_yaml_value))
  out_dir <- config_dir
  dir.create(out_dir, showWarnings = FALSE)
  writeLines(c(header, params_lines), file.path(out_dir, "params.yaml"))
  message("Wrote ", file.path(out_dir, "params.yaml"))

  invisible(params)
}

write_ampliseq_config(dataset, dna, marker)
