# This script can be used to process file uploads from data providers
# to make them ready for import into the asv db.
# See README.md for additional context.

# Assumes the following directory structure:
# ├── [datasetID - see tab/file event]
#   ├── input
#     ├── [filename].xlsx or [filename].tar.gz
#   ├── [this-script-name].R

# Edit dataset-specific sections 1 & 10!
# Then run script down to 'Add taxonomy' section, where you need to run ampliseq pipeline
# (https://nf-co.re/ampliseq) before finishing the script

################################################################################
# 1. Set dataset-specific variables - EDIT HERE, PLEASE!
################################################################################

# Start fresh
rm(list = ls())

# File uploaded by data provider
# uploaded_file <- 'input/jane.doe@univ.se_210902-212121_ampliseq.tar.gz'
uploaded_file <- 'input/jane.doe@univ.se_210902-212121_ampliseq.xlsx'

# Ampliseq output - see section '8. Add taxonomy'
annotation_file <- 'input/annotation.tsv'

# See section '9. Flag ASV:s based on target prediction outcome (Barrnap)'
marker <- '16S rRNA'
# target_criteria <- 'None applied'
target_criteria <- 'Assigned kingdom OR barrnap-positive'

dataset_id <- 'SBDI-ASV-1'

# Include as this is may be an update of dataset already imported into Bioatlas:
bioatlas_resource_uid <- NA
ipt_resource_id <- NA

################################################################################
# 2. Get required packages etc.
################################################################################

# install.packages('openxlsx')
# install.packages('data.table')
library(openxlsx)
library(data.table)
# Set work dir to script location
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))
# Manage output
dir.create('output', showWarnings = FALSE)
excel_out <- paste0('output/', dataset_id, "-adm.xlsx")
tar_out <- paste0('output/', dataset_id, "-adm.tar.gz")
fasta_out <- paste0('output/', dataset_id, '.fasta')

################################################################################
# 3. Import uploaded data into data tables
################################################################################

# Import Excel file
if(grepl('xlsx', uploaded_file, fixed = TRUE)){
  sheets <- getSheetNames(uploaded_file)
  for (sheet_name in sheets[sheets != 'guide']) {
    # Read the Excel sheet into a data.table using read.xlsx()
    assign(
      # Make asv-table & emof-simple R-friendly
      gsub("-", "_", sheet_name),
      data.table(read.xlsx(uploaded_file, sheet=sheet_name, detectDates = TRUE))
    )
  }

  # Or, import archived txt
} else {
  untar(uploaded_file, exdir='unpacked')
  for (xsv in list.files('unpacked', pattern="*.[ct]sv")) {
    name_parts <- strsplit(xsv, split="\\.")[[1]]
    if (name_parts[2] == 'tsv') sep = '\t' else sep = ','
    # Skip annotation that user may have submitted
    if (name_parts[1] != 'annotation')
      assign(
        # Make asv-table & emof-simple R-friendly
        gsub("-", "_", name_parts[1]),
        fread(paste0('unpacked/', xsv), sep = sep, dec=".", na.strings=""))
  }
  # Delete intermediary dir
  unlink(paste0(getwd(),'/unpacked'), recursive = TRUE)
}

################################################################################
# 4. Handle differences in data input template structure (version diffs etc.)
################################################################################

# Rename dt
if (exists('mixs')){
  dna <- mixs
  rm(mixs)
}

# Add new dt
if (!exists('emof_simple')){ emof_simple <- data.table() }

# Recreate emof, if missing (as data providers sometimes delete it)
if (!exists('emof')) {
  columns = c("eventID", "measurementType", "measurementTypeID", "measurementValue",
              "measurementValueID", "measurementUnit", "measurementUnitID", "measurementAccuracy",
              "measurementDeterminedDate", "measurementDeterminedBy", "measurementMethod", "measurementRemarks")
  emof = data.table(matrix(nrow = 0, ncol = length(columns)))
  colnames(emof) = columns
}

# Rename cols
setnames(event, 'catalogueNumber', 'catalogNumber', skip_absent=TRUE)
dts <- list(event, dna, emof, emof_simple)
dts <- lapply(dts, function(dt) setnames(dt, "event_id_alias", "eventID",
                                         skip_absent=TRUE))

# Add new cols, if missing
event_new <- c('datasetID', 'datasetName', 'collectionCode', 'fieldNumber', 'catalogNumber',
               'references', 'institutionCode', 'institutionID', 'dataGeneralizations')
event[, (event_new[!event_new %in% names(event)]) := NA_character_]
dna_new <- c('seq_meth', 'denoising_appr')
dna[, (dna_new[!dna_new %in% names(dna)]) := NA_character_]

# Remove obsolete cols, if present
obsolete <- c('sampleSizeValue')
event[, (obsolete[obsolete %in% names(event)]) := NULL]

################################################################################
# 5. Clean up data
################################################################################

dt_names <- list('event', 'dna', 'emof', 'emof_simple', 'asv_table')
for (nm in dt_names) {
  dt <- get(nm)
  # Remove whitespace
  dt[, names(dt) := lapply(.SD, trimws, whitespace="[\\h\\v]")]

  # Make cols numeric, if possible
  dt[, names(dt) := lapply(.SD, function(col) tryCatch(as.numeric(col), warning=function(w) col))]

  # Drop empty rows (all NA:s)
  if (ncol(dt) > 1) { dt <- dt[rowSums(is.na(dt)) != ncol(dt)] }

  assign(nm, dt)
}

# Standardize values in environment cols (as these tend to vary a bit)
env_cols <- c('env_broad_scale', 'env_local_scale', 'env_medium')
dna[, (env_cols) := lapply(.SD, function(x) {
  # Use lowercase for names
  x <- sub("(.)", "\\L\\1", perl = TRUE, x)
  # Replace (...) with [...]
  x <- gsub("[(]", "[", gsub("[)]", "]", x))
  # Replace _ with :  # To comply with GBIF recommendations
  x <- gsub("_", "[:]", x)
  x
}), .SDcols = env_cols]

# Use pipe '|' to separate multiple values
event[, recordedBy := gsub(', ', ' | ', recordedBy)]

################################################################################
# 6. Add dataset metadata
################################################################################

dataset <- data.frame(datasetID = dataset_id,
                      datasetName = event[1, datasetName],
                      filename = basename(uploaded_file),
                      bioatlas_resource_uid,
                      ipt_resource_id)
# And remove datasetID & datasetName from event tab/file
event[, c("datasetName", "datasetID") := NULL]

################################################################################
# 7. Handle emof data
################################################################################

# If emof-simple is used, transfer data to regular emof
if (nrow(emof) == 0 & nrow(emof_simple) > 0){
  # Convert all cols to char, to not add decimals during melt
  # (melting coerces all values to same data type)
  emof_simple[, names(emof_simple) := lapply(.SD, as.character)]
  # Use data.table (!) melt
  emof <- melt(emof_simple, id.vars = c("eventID"), na.rm = T,
               value.name = "measurementValue",
               variable.name = c("measurementType"))
  # Separate parameter and unit
  emof[, c("measurementType", "measurementUnit"):=
         tstrsplit(measurementType, '[.]?[()]', "")]
  # Add remaining cols
  more_emof <- c('measurementTypeID', 'measurementUnitID', 'measurementValueID',
                 'measurementMethod', 'measurementDeterminedDate',
                 'measurementAccuracy', 'measurementRemarks',
                 'measurementDeterminedBy')
  emof[, (more_emof) := NA]
}
rm(emof_simple)

################################################################################
# 8. Add taxonomy
################################################################################

# Make fasta for Ampliseq input
asv_table[, fasta := paste0('>', asv_id_alias, '\n', DNA_sequence)]
fwrite(asv_table[, .(fasta)], fasta_out, quote = FALSE, col.names = FALSE)
asv_table[,fasta := NULL]

# [Run Ampliseq pipeline, and then add tsv output to input dir]

# Import Ampliseq output
annotation = fread(file = annotation_file, sep = '\t', header = TRUE,
                   dec = '.', na.strings="")
# Add 'Unassigned' to kingdom until fixed in ampliseq SBDI-export
annotation[is.na(kingdom) | kingdom == "", kingdom := 'Unassigned']

################################################################################
# 9. Flag ASV:s based on target prediction outcome (Barrnap)
################################################################################


annotation[, annotation_target := marker]
annotation[, target_criteria := target_criteria]

scores <- c('euk_eval','bac_eval', 'mito_eval', 'arc_eval')

if (target_criteria == 'None applied') {  # E.g. COI
  annotation[, target_prediction := TRUE]
} else if (target_criteria == 'Kingdom = Fungi') {
  annotation[, target_prediction := kingdom == 'Fungi']
  # Use Barrnap cols (but skip for older files that use list instead)
} else if (!exists('non_target') & !exists('target_list')) {
  annotation[, prob_domain := substr(apply(.SD, 1, which.min),3,5),
             .SDcols = scores]
  if (marker == '18S rRNA'){
    # 'Barrnap positive'
    annotation[, target_prediction := prob_domain == 'euk']
  } else if (marker == '16S rRNA'){
    annotation[, target_prediction :=
                 # 'Assigned kingdom OR barrnap-positive'
                 (kingdom != 'Unassigned' | prob_domain %in% c('arc', 'bac'))]
  }
  annotation[, prob_domain := NULL]
}
annotation[, c(scores, 'eval_method') := NULL]

################################################################################
# 10. Fix dataset-specific problems, if any  - EDIT HERE, PLEASE!
################################################################################

################################################################################
# 11. Derive asv and occurrence sheets from asv-table
################################################################################

# Taxonomy from data provider
prv_tax<- c("kingdom", "phylum", "class", "order", "family", "genus",
            "specificEpithet", "infraspecificEpithet", "otu")
asv_table[, previous_identifications :=
            do.call(paste, c(lapply(.SD, function(x) ifelse(is.na(x), '', x)),
                             sep = '|')), .SDcols = prv_tax]
asv_table[, c(prv_tax) := NULL]
setcolorder(asv_table, c('previous_identifications',
                         names(asv_table)[-ncol(asv_table)]))

asv <- asv_table[, c('asv_id_alias','DNA_sequence')]
asv_table[, c('DNA_sequence') := NULL]

labels <- c('asv_id_alias', 'previous_identifications', 'associatedSequences')
counts <- names(asv_table)[!(names(asv_table) %in% labels)]
# Set zero counts to NA so that we can drop them during melting
asv_table[, (counts) := lapply(.SD, function(x) ifelse(x == 0, NA, x)),
          .SDcols = counts]
occurrence <- melt(asv_table, id.vars = labels, na.rm = T,
                   value.name = "organism_quantity",
                   variable.name = c("eventID"))
rm(asv_table)

################################################################################
# 12. Create Excel file & compressed archive for import to asv-db
################################################################################

# For smaller data sets only, create excel file
wb <- createWorkbook()

final_sheets <- c('dataset', 'event', 'dna', 'emof', 'asv', 'occurrence', 'annotation')
for (sheet in final_sheets)
{
  # Revert renaming in output (see above)
  if (sheet == 'asv_table') sheet_name <- 'asv-table'
  else if (sheet == 'dna') sheet_name <- 'mixs'
  else sheet_name <- sheet

  # Write df data to Excel workbook
  addWorksheet(wb, sheetName = sheet_name)
  writeData(wb, sheet_name, get(sheet), startRow = 1, startCol = 1)

  # and write same data to csv:s
  fwrite(get(sheet), paste0('output/', sheet_name, ".csv"), sep=",",
         row.names=FALSE)}
# Export [dataset_id]-adm.xlsx
saveWorkbook(wb, file = excel_out, overwrite = TRUE, )

# Also pack csv:s into [dataset_id]-adm.tar.gz
tfiles <- paste0('output/', list.files('output', pattern="*.csv"))
tar(tar_out, files = tfiles, compression = "gzip", tar='tar')
# Delete csv:s
unlink(tfiles)

rm(list=setdiff(ls(), final_sheets))
