library(data.table)

#' This function reads and reshapes data from condensed DwC datasets downloaded
#' from the Swedish ASP portal,
#' [https://asv-portal.biodiversitydata.se/](https://asv-portal.biodiversitydata.se/).
#'
#' @details
#' The script reads text files (occurrence/asv/emof.tsv) from compressed
#' archives, assuming the following directory structure:
#' ```
#' ├── [this-script].R
#' ├── datasets
#'   ├── [datasetID-1].zip
#'   ├── [datasetID-2].zip
#'   ...
#' ```
#'
#' Data are repackaged into three data.table:s per dataset:
#'
#' 1. ASV-table:    Read counts in a taxonID [row] x eventID [col] matrix
#' 2. EMOF-table:   Contextual parameter values (measurementValue) in a
#'                  measurementType (measurementUnit) x eventID matrix
#' 3. asvs:         taxonID, ASV sequence and taxonomy per ASV
#'
#' Tables from different datasets are indexed by their respective datasetID,
#' and organized into three lists: `asv-tables`, `emof-tables`, `asvs`.
#' These lists are returned as elements of a parent list, `data_tables`.
#'
#' @return
#' A list of sublists containing data.table:s.
#' ```
#' ├── (list)
#'    ├── asv_tables (list)
#'      ├── [datasetID-1] (data.table)
#'      ├── [datasetID-2] (data.table)
#'      ...
#'    ├── emof_tables (list)
#'      ├── [datasetID-1] (data.table)
#'      ├── [datasetID-2] (data.table)
#'      ...
#'    ├── asvs (list)
#'      ├── [datasetID-1] (data.table)
#'      ├── [datasetID-2] (data.table)
#'      ...
#' ```
#'
#' @examples
#' loaded <- load_data()
#' # Access ASV table of individual dataset 'PRJEB55296-18S' like so:
#' loaded$asv_tables$`PRJEB55296-18S`
#' # Inspect in RStudio with
#' View(loaded$asv_tables$`PRJEB55296-18S`)
#'
load_data <- function() {
  # Locate datasets
  script_dir <- dirname(rstudioapi::getActiveDocumentContext()$path)
  data_dir <- file.path(script_dir, 'datasets')
  if (!dir.exists(data_dir)) {
    stop("'datasets' directory not found. Please ensure that your ZIP files
         are located in a subdirectory named 'datasets'.")
  }
  zip_files <- list.files(data_dir, pattern = "\\.zip$", full.names = TRUE)
  if (length(zip_files) == 0) {
    stop("No ZIP files found in the 'datasets' directory.")
  }
  dirs <- gsub(".zip", "", basename(zip_files))

  #' Reads & reshapes occurrence.tsv into wide (ASV x eventID) format
  build_asv_table <- function(zip) {
    occurrence <- fread(cmd = paste('unzip -p', zip, 'occurrence.tsv'))
    asv_table <- dcast(occurrence, taxonID ~ eventID,
                       value.var = "organismQuantity", fill = 0)
    return(asv_table)
  }

  #' Reads ASV sequence and taxonomy from asv.tsv
  get_asvs <- function(zip) {
    asv <- fread(cmd = paste('unzip -p', zip, 'asv.tsv'))
    return(asv)
  }

  #' Reads & reshapes emof.tsv into wide format
  #' (measurementType [measurementUnit] x eventID)
  #' and drops remaining fields, e.g.measurementMethod & measurementRemarks!
  build_emof_table <- function(zip) {
    emof <- fread(cmd = paste('unzip -p', zip, 'emof.tsv'))
    # Handle datasets that have no contextual data
    if (nrow(emof) == 0) {
      message("Adding empty emof table for ", gsub(".zip", "", zip))
      return(data.table("measurementType (measurementUnit)" = character()))
    }
    # Convert all cols to char, to not add unwanted decimals during dcast
    emof[, names(emof) := lapply(.SD, as.character)]
    emof_table <- dcast(emof, paste0(measurementType, " (", measurementUnit, ")")
                        ~ eventID, value.var = "measurementValue")
    setnames(emof_table, "measurementType", "measurementType (measurementUnit)")
    return(emof_table)
  }

  # Process data into data.table:s in (sub)lists, and return in parent list
  loaded <- list()
  loaded$asv_tables <- setNames(lapply(zip_files, build_asv_table), dirs)
  loaded$asvs <- setNames(lapply(zip_files, get_asvs), dirs)
  loaded$emof_tables <- setNames(lapply(zip_files, build_emof_table), dirs)
  return(loaded)
}

#' This function merges ASV/EMOF tables and asvs from different datasets
#'
#' @param loaded A list containing sublists of ASV tables, EMOF tables,
#' and ASV metadata obtained from the load_data function.
#'
#' @return
#' A list containing merged ASV tables, EMOF tables, and ASV metadata.
#' ```
#' ├──  (list)
#'    ├── asv_table (data.table)
#'    ├── emof_table (data.table)
#'    ├── asvs (data.table)
#' ```
#'
#' @examples
#' loaded <- load_data()
#' merged <- merge_tables(loaded)
#' View(merged$asv_table)
#'
merge_tables <- function(loaded) {
  merged <- list()
  merged$asv_table <- Reduce(function(x, y)
    merge(x, y, by = "taxonID", all = TRUE), loaded$asv_tables)
  merged$emof_table <- Reduce(function(x, y)
    merge(x, y, by = "measurementType (measurementUnit)", all = TRUE),
    loaded$emof_table)
  # We want 1 row/ASV, so only merge non-dataset-specific cols here
  merge_cols <- c("taxonID", "asv_sequence", "scientificName", "taxonRank",
                  "kingdom" ,"phylum", "order", "class", "family", "genus",
                  "specificEpithet", "infraspecificEpithet", "otu",
                  "identificationReferences", "identificationRemarks")
  merged$asvs <- Reduce(function(x, y) {
  merge(x[, ..merge_cols], y[, ..merge_cols], by = merge_cols, all = TRUE)
  }, loaded$asvs)
  return(merged)
}

loaded <- load_data()
merged <- merge_tables(loaded)
rm(list=setdiff(ls(), c('loaded', 'merged')))
