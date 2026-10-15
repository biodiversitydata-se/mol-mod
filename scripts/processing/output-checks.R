# Compares the number of events and ASVs in related parts of output
check_output <- function(ds) {
  archive <- paste0('output/', ds, '-adm.tar.gz')
  occ <- fread(cmd = paste('tar -xOzf', archive, 'output/occurrence.csv'))
  annot <- fread(cmd = paste('tar -xOzf', archive, 'output/annotation.csv'))
  emof <- fread(cmd = paste('tar -xOzf', archive, 'output/emof.csv'))
  mixs <- fread(cmd = paste('tar -xOzf', archive, 'output/mixs.csv'))
  asv <- fread(cmd = paste('tar -xOzf', archive, 'output/asv.csv'))
  
  event_counts <- c(
    occurrence = length(unique(occ$eventID)),
    emof = length(unique(emof$eventID)),
    mixs = length(unique(mixs$eventID))
  )
  
  asv_counts <- c(
    occurrence = length(unique(occ$asv_id_alias)),
    annotation = length(unique(annot$asv_id_alias)),
    asv = length(unique(asv$asv_id_alias))
  )
  
  print(list(event_counts = event_counts, asv_counts = asv_counts))
}

# Run from the dataset folder after section 15 of asv-input-processing.R:
# check_output(dataset$datasetID)
