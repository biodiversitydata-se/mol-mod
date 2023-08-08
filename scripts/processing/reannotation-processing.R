# This script uses Barrnap prediction scores in Ampliseq (SBDI) annotation
# output, together with user-provided prediction criteria, to determine whether
# annotated ASVs derive from a user-specified marker gene

################################################################################
# Edit here, please!
################################################################################

annotation_file <- 'input/reannotation.tsv'
target_criteria <- 'Assigned kingdom OR barrnap-positive'
marker <- '16S rRNA'

################################################################################
# Set up
################################################################################

# Use instead of openxl as some output format is not understood by
# update.annotation.sh
# install.packages('WriteXLS')
# install.packages('data.table')
library(WriteXLS)
library(data.table)
# Set work dir to script location
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Import Ampliseq output
annotation = fread(file = annotation_file, sep = '\t', header = TRUE,
                   dec = '.', na.strings="")
# Add 'Unassigned' to kingdom until fixed in ampliseq SBDI-export
annotation[is.na(kingdom) | kingdom == "", kingdom := 'Unassigned']
# Drop unused col
annotation[, asv_id_alias := NULL]

annotation[, annotation_target := marker]
annotation[, target_criteria := target_criteria]

################################################################################
# Evaluate
################################################################################

scores <- c('euk_eval','bac_eval', 'mito_eval', 'arc_eval')
if (target_criteria == 'None applied') {
  annotation[, target_prediction := TRUE]
} else {
  # Find domain with lowest p value
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
# Output
################################################################################

# For smaller data sets only, create excel file
WriteXLS(annotation, 'output/reannotation.xlsx')

# Write same data to csv
fwrite(annotation, 'output/reannotation.csv', sep=',', row.names=FALSE)
