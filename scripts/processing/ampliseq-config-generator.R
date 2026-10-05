# Script for generating nf-core/ampliseq config files (params.yaml, proj_env)
# for taxonomic annotation of a dataset's fasta on the HPC cluster.
# Expects objects dataset, dna and marker from asv-input-processing.R (run
# through section 11), and is sourced from the dataset folder, e.g.:
#   source("<path-to-mol-mod>/scripts/processing/ampliseq-config-generator.R")
# Files are written to <cluster>/ in the dataset folder.
#
# Site-specific settings are read from environment variables (e.g. set in
# ~/.Renviron), so that no project IDs or paths are stored in the repo:
#   NAISS_PROJECT         NAISS compute project (required)
#   AMPLISEQ_CLUSTER      cluster name, used as output folder (default: dardel)
#   AMPLISEQ_REMOTE_BASE  project storage directory on the cluster, under which
#                         one folder per dataset is created (optional; if
#                         unset, proj_env is not written)

cluster <- Sys.getenv("AMPLISEQ_CLUSTER", "dardel")
naiss_project <- Sys.getenv("NAISS_PROJECT")
remote_base <- Sys.getenv("AMPLISEQ_REMOTE_BASE", NA)
if (naiss_project == "") {
  stop("Set environment variable NAISS_PROJECT (e.g. in ~/.Renviron)")
}

# Reference databases and options per marker. The pattern is matched
# (case-insensitively) against the marker set in section 1 of the R script.
marker_presets <- list(
  list(
    pattern = "^16S",
    params = list(dada_ref_taxonomy = "sbdi-gtdb=R09-RS220-1")
  ),
  list(
    pattern = "^18S",
    params = list(dada_ref_taxonomy = "pr2=5.0.0")
  ),
  list(
    pattern = "^ITS",
    params = list(
      dada_ref_taxonomy = "unite-alleuk=10.0",
      skip_barrnap = TRUE,
      addsh = TRUE,
      cut_its = "its2"
    )
  ),
  list(
    pattern = "^CO(I|1)",
    params = list(
      sintax_ref_taxonomy = "coidb=221216",
      skip_dada_taxonomy = TRUE,
      skip_barrnap = TRUE
    )
  )
)

get_marker_params <- function(marker) {
  for (preset in marker_presets) {
    if (grepl(preset$pattern, marker, ignore.case = TRUE)) {
      return(preset$params)
    }
  }
  stop(
    "No ampliseq preset matches marker '", marker, "'. Known patterns: ",
    paste(sapply(marker_presets, `[[`, "pattern"), collapse = ", ")
  )
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
  out_dir <- cluster
  dir.create(out_dir, showWarnings = FALSE)

  params <- c(
    list(
      project = naiss_project,
      input_fasta = paste0(dataset_id, ".fasta"),
      outdir = "results",
      skip_qiime = TRUE,
      sbdiexport = TRUE
    ),
    get_marker_params(marker),
    list(
      FW_primer = get_primer(dna, "pcr_primer_forward"),
      RV_primer = get_primer(dna, "pcr_primer_reverse")
    )
  )
  params_lines <- paste0(names(params), ": ", sapply(params, format_yaml_value))
  writeLines(params_lines, file.path(out_dir, "params.yaml"))
  message("Wrote ", file.path(out_dir, "params.yaml"))

  if (is.na(remote_base)) {
    warning("remote_base is not set; skipping proj_env")
    return(invisible(params))
  }

  work_dir <- file.path(remote_base, dataset_id)
  proj_env_lines <- c(
    "# Source after loading modules, but before running",
    "# Cap Java memory use",
    "export NXF_OPTS='-Xms1g -Xmx4g'",
    "# Keep Nextflow and container caches out of the home directory",
    sprintf("export NXF_HOME='%s'", work_dir),
    sprintf("export NXF_SINGULARITY_CACHEDIR='%s/nextflow_files'", work_dir),
    sprintf("export APPTAINER_CACHEDIR='%s'", remote_base)
  )
  writeLines(proj_env_lines, file.path(out_dir, "proj_env"))
  message("Wrote ", file.path(out_dir, "proj_env"))

  invisible(params)
}

write_ampliseq_config(dataset, dna, marker)
