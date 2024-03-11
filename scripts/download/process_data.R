library(data.table)

build_emof_table <- function(zip) {
# Reads & reshapes emof.tsv into wide (measurement x sample) format
  emof <- fread(cmd = paste('unzip -p', zip, 'emof.tsv'))
  if (nrow(emof) == 0) {
    message("Adding empty emof table for ", gsub(".zip", "", zip))
    return(data.table("measurementType (measurementUnit)" = character()))
  }
  # Convert all cols to char, to not add decimals during dcast
  emof[, names(emof) := lapply(.SD, as.character)]
  emof_table <- dcast(emof, paste0(measurementType, " (", measurementUnit, ")")
                      ~ eventID, value.var = "measurementValue")
  setnames(emof_table, "measurementType", "measurementType (measurementUnit)")

  return(emof_table)
}

build_asv_table <- function(zip) {
# Reads & reshapes occurrence.tsv into wide (ASV x sample) format
  occurrence <- fread(cmd = paste('unzip -p', zip, 'occurrence.tsv'))
  asv_table <- dcast(occurrence, taxonID ~ eventID,
                     value.var = "organismQuantity", fill = 0)
  return(asv_table)
}

get_asvs <- function(zip) {
# Reads asv.tsv
  asv <- fread(cmd = paste('unzip -p', zip, 'asv.tsv'))
  return(asv)
}

script_dir <- dirname(rstudioapi::getActiveDocumentContext()$path)
setwd(paste0(script_dir, '/datasets'))
zip_files <- list.files(pattern = "\\.zip$")
dirs <- gsub(".zip", "", zip_files)

# Save tsv data to data.table:s in lists
emof_tables <- setNames(lapply(zip_files, build_emof_table), dirs)
asv_tables <- setNames(lapply(zip_files, build_asv_table), dirs)
asvs <- setNames(lapply(zip_files, get_asvs), dirs)

# Merge tables from different datasets iteratively
merged_asv_table <- Reduce(function(x, y)
  merge(x, y, by = "taxonID", all = TRUE), asv_tables)
merged_emof_table <- Reduce(function(x, y)
  merge(x, y, by = "measurementType (measurementUnit)", all = TRUE), emof_tables)
merge_cols <- c("taxonID", "asv_sequence", "scientificName", "taxonRank",
                "kingdom" ,"phylum", "order", "class", "family", "genus",
                "specificEpithet", "infraspecificEpithet", "otu",
                "identificationReferences", "identificationRemarks")
merged_asvs <- Reduce(function(x, y) {
  merge(x[, merge_cols, with = FALSE], y[, merge_cols, with = FALSE],
        by = merge_cols, all = TRUE)
}, asvs)

# Drop intermediary objects
keep <- c('emof_tables', 'asv_tables', 'asvs', grep("^merged", ls(), value = TRUE))
rm(list=setdiff(ls(), keep))

# Inspect with:
# View(asv_tables$`GU-2022-Wallhamn-18S`)
# View(emof_tables[['PRJEB55296-18S-sub1']])
