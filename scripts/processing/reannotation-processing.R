# This script uses Barrnap prediction scores in Ampliseq (SBDI) annotation
# output, together with user-provided prediction criteria, to determine whether
# annotated ASVs derive from a user-specified marker gene

# Assumes the following directory structure:
#   ├── input
#     ├── reannotation.tsv  # nf-core/ampliseq output file (renamed)
#   [this-script]

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
# Manage output
dir.create('output', showWarnings = FALSE)
# Import Ampliseq output
annotation = fread(file = annotation_file, sep = '\t', header = TRUE,
                   dec = '.', na.strings="")
# Add 'Unassigned' to kingdom until fixed in ampliseq SBDI-export
annotation[is.na(kingdom) | kingdom == "", kingdom := 'Unassigned']
# Drop unused col
annotation[, asv_id_alias := NULL]

annotation[, annotation_target := marker]
annotation[, target_criteria := target_criteria]

# Replace double spaces in ampliseq output
annotation[, annotation_algorithm := gsub("\\s{2,}", " ", annotation_algorithm)]

################################################################################
# Evaluate
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
# Correct genus/specificEpithet errors introduced by Ampliseq
################################################################################

if (marker == "18S rRNA" && !is.na(lookup_file) && file.exists(lookup_file)) {

  lookup <- fread(lookup_file)
  lookup[, scientific_name_key := paste(genus, species)]

  annotation[lookup,
    `:=`(
      genus                 = i.correct_genus,
      specific_epithet      = i.correct_specific_epithet,
      infraspecific_epithet = i.correct_infraspecific_epithet,
      scientific_name       = i.correct_scientific_name
    ),
    on = .(genus, scientific_name = scientific_name_key)
  ]

  if (!is.na(dada2_file) && file.exists(dada2_file)) {
    dada2 <- fread(dada2_file)

    if (all(c("Genus", "Species") %in% names(dada2))) {
      dada2[, genus_in_species := sub("_[^_]+$", "", Species)]

      new_mismatches <- dada2[
        genus_in_species != Genus &
          Species != "" &
          !paste(Genus, Species) %in% lookup[, paste(genus, species)],
        .(Genus, Species)
      ] |> unique()

      if (nrow(new_mismatches) > 0) {
        warning(
          "New genus/species mismatches not in correction_lookup.tsv",
          " - please add and re-run:\n"
        )
        print(new_mismatches)
      }
    }
  }

} else if (marker == "COI") {

  is_unresolved <- grepl("_X+$", annotation$genus)

  annotation[is_unresolved, specific_epithet      := "X"]
  annotation[is_unresolved, infraspecific_epithet := ""]
  annotation[
    is_unresolved & (is.na(otu) | otu == ""),
    scientific_name := sub("(X+)$", "\\1X", genus)
  ]

  cat(sprintf("COI _X-correction: %d rows corrected.\n", sum(is_unresolved)))
}

################################################################################
# Output
################################################################################

# # For smaller data sets only, create excel file
# WriteXLS(annotation, 'output/reannotation.xlsx')

# Write same data to csv
fwrite(annotation, 'output/reannotation.csv', sep=',', row.names=FALSE)
