# This script processes provider uploads into the format required for import into the ASV DB.
# See README.md for additional context.
#
# Assumes the script is run from the project root, with:
#   - input/
#   - output/
#
# Expected input template sheets/files:
#   - Study
#   - Samples
#   - Taxonomy
#   - ASV-table
#
# User-facing ID columns:
#   - Samples should contain: sample_id
#   - Taxonomy should contain: asv_id
#   - ASV-table should contain: asv_id
#
# Internal names used by the script:
#   - sample_id -> eventID
#   - asv_id -> asv_id_alias
#
# Edit dataset-specific sections 1 and 14.
# Then run the script down to 'Create fasta for annotation workflow',
# run the ampliseq pipeline separately, place annotation.tsv in input/,
# and finish the script.

################################################################################
# 1. Set dataset-specific variables - EDIT HERE
################################################################################

rm(list = ls())

uploaded_file <- "input/jane.doe@univ.se_210902-212121_ampliseq.xlsx"
# uploaded_file <- "input/jane.doe@univ.se_210902-212121_ampliseq.tar.gz"
annotation_file <- "input/annotation.tsv"

marker <- "16S rRNA"
# target_criteria <- "None applied"
target_criteria <- "Assigned kingdom OR barrnap-positive"

bioatlas_resource_uid <- NA
ipt_resource_id <- NA

################################################################################
# 2. Packages and output paths
################################################################################

# install.packages("openxlsx")
# install.packages("data.table")

library(openxlsx)
library(data.table)

dir.create("output", showWarnings = FALSE)

################################################################################
# 3. Import uploaded data
################################################################################

if (grepl("\\.xlsx$", uploaded_file, ignore.case = TRUE)) {
  sheets <- getSheetNames(uploaded_file)

  for (sheet_name in sheets[sheets != "guide"]) {
    assign(
      gsub("-", "_", sheet_name),
      data.table(read.xlsx(uploaded_file, sheet = sheet_name, detectDates = TRUE))
    )
  }

} else if (grepl("\\.(tar\\.gz|tgz)$", uploaded_file, ignore.case = TRUE)) {

  untar(uploaded_file, exdir = "unpacked")

  files <- list.files(
    "unpacked",
    pattern = "\\.(tsv|csv)$",
    recursive = TRUE,
    full.names = TRUE
  )

  for (f in files) {
    name <- tools::file_path_sans_ext(basename(f))
    name <- gsub("-", "_", name)

    sep <- if (grepl("\\.tsv$", f, ignore.case = TRUE)) "\t" else ","

    assign(
      name,
      fread(
        f,
        sep = sep,
        na.strings = "",
        quote = "",
        fill = TRUE,
        encoding = "UTF-8"
      )
    )
  }

  unlink("unpacked", recursive = TRUE)

} else {
  stop("Unsupported file format. Use .xlsx or .tar.gz with .tsv/.csv files.")
}

required_tables <- c("Study", "Samples", "Taxonomy", "ASV_table")
missing_tables <- required_tables[!vapply(required_tables, exists, logical(1))]

if (length(missing_tables) > 0) {
  stop(
    paste0(
      "Missing required sheet(s)/file(s): ",
      paste(missing_tables, collapse = ", ")
    )
  )
}

################################################################################
# 4. Parse Study sheet
################################################################################

study_raw <- copy(Study)

if (ncol(study_raw) < 2) {
  stop("Study sheet must contain at least two columns: field and value.")
}

# Reconstruct first row from column names when Study was read with headers
study_header_row <- data.table(
  V1 = names(study_raw)[1],
  V2 = names(study_raw)[2]
)

study_raw <- study_raw[, 1:2]
setnames(study_raw, c("V1", "V2"))
study_raw <- rbindlist(list(study_header_row, study_raw), use.names = TRUE, fill = TRUE)

setnames(study_raw, c("field", "value"))

study_raw[, field := trimws(as.character(field))]
study_raw[, value := trimws(as.character(value))]
study_raw[, field := sub("^\ufeff", "", field)]
study_raw[, field := sub("^ï»¿", "", field)]
study_raw <- study_raw[!is.na(field) & field != ""]

study_list <- as.list(study_raw$value)
names(study_list) <- study_raw$field

get_study_value <- function(x) {
  if (x %in% names(study_list)) study_list[[x]] else NA_character_
}

dataset_id <- get_study_value("datasetID")

if (is.na(dataset_id) || dataset_id == "") {
  stop("Study must contain a non-empty 'datasetID'.")
}

excel_out <- paste0("output/", dataset_id, "-adm.xlsx")
tar_out <- paste0("output/", dataset_id, "-adm.tar.gz")
fasta_out <- paste0("output/", dataset_id, ".fasta")

################################################################################
# 5. Clean input tables and normalize user-facing ID columns
################################################################################

clean_character_dt <- function(dt, exclude_cols = character()) {
  char_cols <- names(dt)[vapply(dt, is.character, logical(1))]
  char_cols <- setdiff(char_cols, exclude_cols)

  if (length(char_cols) > 0) {
    dt[, (char_cols) := lapply(.SD, trimws), .SDcols = char_cols]
  }

  dt
}

clean_colnames <- function(dt) {
  nms <- names(dt)
  nms <- trimws(nms)
  nms <- sub("^\ufeff", "", nms)
  nms <- sub("^ï»¿", "", nms)
  setnames(dt, nms)
  dt
}

rename_or_use_first_col <- function(dt, candidates, target, dt_name, allow_first_col = FALSE) {
  hits <- intersect(candidates, names(dt))

  if (length(hits) > 1) {
    stop(
      paste0(
        dt_name,
        " contains multiple possible ID columns: ",
        paste(hits, collapse = ", "),
        ". Keep only one."
      )
    )
  }

  if (length(hits) == 1) {
    if (hits != target) {
      setnames(dt, hits, target)
    }
    return(dt)
  }

  if (allow_first_col) {
    if (ncol(dt) == 0) {
      stop(paste0(dt_name, " has no columns."))
    }
    first_col <- names(dt)[1]
    setnames(dt, first_col, target)
    return(dt)
  }

  stop(
    paste0(
      dt_name,
      " must contain one of the following columns: ",
      paste(candidates, collapse = ", "),
      ". Available columns: ",
      paste(names(dt), collapse = ", ")
    )
  )
}

Study <- clean_colnames(copy(Study))
Samples <- clean_colnames(clean_character_dt(copy(Samples)))
Taxonomy <- clean_colnames(clean_character_dt(copy(Taxonomy), exclude_cols = "DNA_sequence"))
ASV_table <- clean_colnames(clean_character_dt(copy(ASV_table)))

Samples <- rename_or_use_first_col(
  Samples,
  candidates = c("sample_id", "eventID"),
  target = "eventID",
  dt_name = "Samples",
  allow_first_col = TRUE
)

Taxonomy <- rename_or_use_first_col(
  Taxonomy,
  candidates = c("asv_id", "asv_id_alias"),
  target = "asv_id_alias",
  dt_name = "Taxonomy",
  allow_first_col = FALSE
)

ASV_table <- rename_or_use_first_col(
  ASV_table,
  candidates = c("asv_id", "asv_id_alias"),
  target = "asv_id_alias",
  dt_name = "ASV-table",
  allow_first_col = FALSE
)

Taxonomy[, DNA_sequence := as.character(DNA_sequence)]

required_tax_cols <- c("asv_id_alias", "DNA_sequence")

if (!all(required_tax_cols %in% names(Taxonomy))) {
  stop(
    paste0(
      "Taxonomy is missing required column(s): ",
      paste(setdiff(required_tax_cols, names(Taxonomy)), collapse = ", ")
    )
  )
}

################################################################################
# 6. Build event from Samples + Study
################################################################################

event_std <- c(
  "eventID", "materialSampleID", "associatedSequences", "eventDate",
  "samplingProtocol", "locationID", "decimalLatitude", "decimalLongitude",
  "geodeticDatum", "coordinateUncertaintyInMeters", "dataGeneralizations",
  "recordedBy", "country", "municipality", "verbatimLocality",
  "minimumElevationInMeters", "maximumElevationInMeters",
  "minimumDepthInMeters", "maximumDepthInMeters", "fieldNumber",
  "catalogNumber", "references"
)

missing_event_std <- setdiff(event_std, names(Samples))
if (length(missing_event_std) > 0) {
  Samples[, (missing_event_std) := NA]
}

event <- copy(Samples[, ..event_std])

event[, datasetID := dataset_id]
event[, datasetName := get_study_value("datasetName")]
event[, institutionCode := get_study_value("institutionCode")]
event[, institutionID := get_study_value("institutionID")]
event[, collectionCode := get_study_value("collectionCode")]

if ("recordedBy" %in% names(event)) {
  event[, recordedBy := gsub(", ", " | ", recordedBy, fixed = TRUE)]
}

event_order <- c(
  "eventID", "datasetID", "datasetName", "institutionCode", "institutionID",
  "collectionCode", "materialSampleID", "associatedSequences", "fieldNumber",
  "catalogNumber", "references", "eventDate", "samplingProtocol", "locationID",
  "decimalLatitude", "decimalLongitude", "geodeticDatum",
  "coordinateUncertaintyInMeters", "dataGeneralizations", "recordedBy",
  "country", "municipality", "verbatimLocality", "minimumElevationInMeters",
  "maximumElevationInMeters", "minimumDepthInMeters", "maximumDepthInMeters"
)

event <- event[, ..event_order]

################################################################################
# 7. Build dna from Study
################################################################################

dna_fields <- c(
  "sop", "target_gene", "target_subfragment", "lib_layout", "seq_meth",
  "pcr_primer_name_forward", "pcr_primer_name_reverse", "pcr_primer_forward",
  "pcr_primer_reverse", "denoising_appr", "env_broad_scale",
  "env_local_scale", "env_medium"
)

dna <- data.table(eventID = event$eventID)

for (fld in dna_fields) {
  dna[, (fld) := get_study_value(fld)]
}

env_cols <- intersect(c("env_broad_scale", "env_local_scale", "env_medium"), names(dna))
if (length(env_cols) > 0) {
  dna[, (env_cols) := lapply(.SD, function(x) {
    x <- as.character(x)
    x <- sub("(.)", "\\L\\1", perl = TRUE, x)
    x <- gsub("[(]", "[", gsub("[)]", "]", x))
    x <- gsub("_", ":", x)
    x
  }), .SDcols = env_cols]
}

################################################################################
# 8. Build emof from non-standard Sample columns
################################################################################

extra_cols <- setdiff(names(Samples), event_std)

if (length(extra_cols) > 0) {
  emof <- melt(
    Samples[, c("eventID", extra_cols), with = FALSE],
    id.vars = "eventID",
    variable.name = "measurementType",
    value.name = "measurementValue",
    variable.factor = FALSE
  )

  emof <- emof[!is.na(measurementValue) & measurementValue != ""]

  emof[, measurementUnit := NA_character_]
  emof[
    grepl(" \\([^()]+\\)$", measurementType),
    c("measurementType", "measurementUnit") :=
      tstrsplit(measurementType, " \\(|\\)$")
  ]

  emof[, `:=`(
    measurementTypeID = NA_character_,
    measurementValueID = NA_character_,
    measurementUnitID = NA_character_,
    measurementAccuracy = NA_character_,
    measurementDeterminedDate = NA_character_,
    measurementDeterminedBy = NA_character_,
    measurementMethod = NA_character_,
    measurementRemarks = NA_character_
  )]

  setcolorder(emof, c(
    "eventID", "measurementType", "measurementTypeID", "measurementValue",
    "measurementValueID", "measurementUnit", "measurementUnitID",
    "measurementAccuracy", "measurementDeterminedDate",
    "measurementDeterminedBy", "measurementMethod", "measurementRemarks"
  ))
} else {
  emof <- data.table(
    eventID = character(),
    measurementType = character(),
    measurementTypeID = character(),
    measurementValue = character(),
    measurementValueID = character(),
    measurementUnit = character(),
    measurementUnitID = character(),
    measurementAccuracy = character(),
    measurementDeterminedDate = character(),
    measurementDeterminedBy = character(),
    measurementMethod = character(),
    measurementRemarks = character()
  )
}

################################################################################
# 9. Build asv and occurrence from Taxonomy + ASV-table
################################################################################

taxonomy_dt <- copy(Taxonomy)
asv_table_dt <- copy(ASV_table)

tax_cols <- c(
  "asv_id_alias", "DNA_sequence", "associatedSequences",
  "kingdom", "phylum", "class", "order", "family",
  "genus", "specificEpithet", "infraspecificEpithet", "otu"
)

missing_tax_cols <- setdiff(tax_cols, names(taxonomy_dt))
if (length(missing_tax_cols) > 0) {
  taxonomy_dt[, (missing_tax_cols) := NA_character_]
}

if (!"associatedSequences" %in% names(taxonomy_dt)) {
  taxonomy_dt[, associatedSequences := NA_character_]
}

taxonomy_dt[, DNA_sequence := as.character(DNA_sequence)]
taxonomy_dt[, DNA_sequence := gsub("-", "", DNA_sequence, fixed = TRUE)]

count_cols <- intersect(names(asv_table_dt), event$eventID)

if (length(count_cols) == 0) {
  stop(
    paste0(
      "No ASV-table columns matched eventIDs.\n",
      "ASV-table columns: ", paste(names(asv_table_dt), collapse = ", "), "\n",
      "eventIDs: ", paste(event$eventID, collapse = ", ")
    )
  )
}

asv_table_dt <- asv_table_dt[, c("asv_id_alias", count_cols), with = FALSE]

asv_table_dt[, (count_cols) := lapply(.SD, function(x) {
  x <- as.numeric(as.character(x))
  x[is.na(x)] <- 0
  x
}), .SDcols = count_cols]

orig_asv_no <- nrow(asv_table_dt)
count_mat <- as.matrix(asv_table_dt[, ..count_cols])
asv_table_dt <- asv_table_dt[rowSums(count_mat != 0) > 0]
del_asv_no <- orig_asv_no - nrow(asv_table_dt)

prv_tax <- c(
  "kingdom", "phylum", "class", "order", "family", "genus",
  "specificEpithet", "infraspecificEpithet", "otu"
)

taxonomy_dt[, previous_identifications :=
              do.call(
                paste,
                c(
                  lapply(.SD, function(x) ifelse(is.na(x), "", as.character(x))),
                  sep = "|"
                )
              ),
            .SDcols = prv_tax]

asv <- unique(taxonomy_dt[, .(asv_id_alias, DNA_sequence)])

occurrence <- melt(
  asv_table_dt,
  id.vars = "asv_id_alias",
  variable.name = "eventID",
  value.name = "organism_quantity",
  variable.factor = FALSE
)

occurrence <- occurrence[!is.na(organism_quantity) & organism_quantity != 0]

occurrence <- merge(
  occurrence,
  unique(taxonomy_dt[, .(asv_id_alias, previous_identifications, associatedSequences)]),
  by = "asv_id_alias",
  all.x = TRUE
)

occurrence <- occurrence[, .(
  asv_id_alias,
  previous_identifications,
  associatedSequences,
  eventID,
  organism_quantity
)]

used_asvs <- unique(occurrence$asv_id_alias)
asv <- asv[asv_id_alias %in% used_asvs]

################################################################################
# 10. Dataset metadata
################################################################################

dataset <- data.frame(
  datasetID = dataset_id,
  datasetName = get_study_value("datasetName"),
  filename = basename(uploaded_file),
  bioatlas_resource_uid = bioatlas_resource_uid,
  ipt_resource_id = ipt_resource_id
)

event[, c("datasetName", "datasetID") := NULL]

################################################################################
# 11. Create fasta for annotation workflow
################################################################################

fasta_dt <- unique(taxonomy_dt[asv_id_alias %in% used_asvs, .(asv_id_alias, DNA_sequence)])
fasta_dt[, fasta := paste0(">", asv_id_alias, "\n", DNA_sequence)]

fwrite(
  fasta_dt[, .(fasta)],
  fasta_out,
  quote = FALSE,
  col.names = FALSE
)

################################################################################
# 12. Import and filter annotation
################################################################################

annotation <- fread(
  file = annotation_file,
  sep = "\t",
  header = TRUE,
  dec = ".",
  na.strings = ""
)

if (!"asv_id_alias" %in% names(annotation)) {
  stop("annotation.tsv must contain column 'asv_id_alias'.")
}

annotation <- annotation[asv_id_alias %in% used_asvs]

if ("kingdom" %in% names(annotation)) {
  annotation[is.na(kingdom) | kingdom == "", kingdom := "Unassigned"]
}

if ("annotation_algorithm" %in% names(annotation)) {
  annotation[, annotation_algorithm := gsub("\\s+", " ", annotation_algorithm)]
}

################################################################################
# 13. Flag ASVs based on target prediction outcome
################################################################################

annotation[, annotation_target := marker]
annotation[, target_criteria := target_criteria]

scores <- c("euk_eval", "bac_eval", "mito_eval", "arc_eval")

if (target_criteria == "None applied") {
  annotation[, target_prediction := TRUE]

} else if (target_criteria == "Kingdom = Fungi") {
  annotation[, target_prediction := kingdom == "Fungi"]

} else {
  scores_present <- intersect(scores, names(annotation))

  if (length(scores_present) > 0) {
    score_mat <- as.matrix(annotation[, ..scores_present])
    min_idx <- max.col(-score_mat, ties.method = "first")
    min_names <- scores_present[min_idx]
    annotation[, prob_domain := substr(min_names, 1, 3)]

    if (marker == "18S rRNA") {
      annotation[, target_prediction := prob_domain == "euk"]
    } else if (marker == "16S rRNA") {
      annotation[, target_prediction :=
                   (kingdom != "Unassigned" | prob_domain %in% c("arc", "bac"))]
    } else {
      annotation[, target_prediction := TRUE]
    }

    annotation[, prob_domain := NULL]
  } else {
    if (marker == "16S rRNA" && "kingdom" %in% names(annotation)) {
      annotation[, target_prediction := kingdom != "Unassigned"]
    } else {
      annotation[, target_prediction := TRUE]
    }
  }
}

annotation[, c(intersect(names(annotation), c(scores, "eval_method"))) := NULL]

################################################################################
# 14. Optional dataset-specific fixes
################################################################################

# Add dataset-specific fixes here if needed.

################################################################################
# 15. Export final files
################################################################################

wb <- createWorkbook()

final_sheets <- c("dataset", "event", "dna", "emof", "asv", "occurrence", "annotation")

for (sheet in final_sheets) {
  sheet_name <- if (sheet == "dna") "mixs" else sheet

  addWorksheet(wb, sheetName = sheet_name)
  writeData(wb, sheet_name, get(sheet), startRow = 1, startCol = 1)

  fwrite(
    get(sheet),
    paste0("output/", sheet_name, ".csv"),
    sep = ",",
    row.names = FALSE
  )
}

saveWorkbook(wb, file = excel_out, overwrite = TRUE)

tfiles <- paste0("output/", list.files("output", pattern = "\\.csv$"))
tar(tar_out, files = tfiles, compression = "gzip", tar = "tar")
unlink(tfiles)

print(paste("Deleted ASV without occurrences:", del_asv_no))

# Keep only objects that correspond to exported sheets
rm(list = setdiff(ls(), final_sheets))
