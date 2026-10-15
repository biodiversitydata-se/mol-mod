# Corrections of genus/species splitting errors in ampliseq's SBDI export.
# Expects the annotation data.table from asv-input-processing.R (section 13),
# with ampliseq column names (genus, specificEpithet, infraspecificEpithet,
# otu, scientificName, reference_db), and is sourced from the dataset folder.
# The reference database is taken from reference_db, so the corrections apply
# whatever the marker is called:
#
# - PR2: ampliseq derives specificEpithet by stripping the genus from PR2's
#   species string, which fails when PR2's genus differs from the genus part of
#   the species, or when names contain underscores (see
#   https://github.com/pr2database/pr2database/issues/56 and
#   https://github.com/nf-core/ampliseq/issues/921). As this cannot be fixed by
#   rules, known cases are corrected from pr2-correction-lookup.tsv. If a DADA2
#   taxonomy file from the run (input/ASV_tax.pr2_*.tsv) is present, PR2
#   genus/species combinations missing from the lookup table are reported.
#
# - COIDB: for genera unresolved below a higher rank (e.g. Naididae_X),
#   specificEpithet gets the parent name and infraspecificEpithet the X's
#   (see https://github.com/nf-core/ampliseq/issues/923). specificEpithet is
#   set to "X", infraspecificEpithet cleared, and scientificName (unless it is
#   a BOLD BIN from otu) set to the genus with one more X (Naididae_XX).

library(data.table)

# Folder of this script (and of the lookup table) when sourced (innermost
# source() call), else the working directory
taxonomy_corrections_dir <- local({
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

correct_pr2 <- function(annotation, lookup_file, dada2_files) {
  lookup <- fread(lookup_file, sep = "\t", na.strings = "")
  required <- c(
    "genus", "species", "correct_genus", "correct_specific_epithet",
    "correct_infraspecific_epithet", "correct_scientific_name"
  )
  missing <- setdiff(required, names(lookup))
  if (length(missing) > 0) {
    stop(basename(lookup_file), " is missing column(s): ", paste(missing, collapse = ", "))
  }
  # Ampliseq's failed scientificName is "<genus> <PR2 species string>"
  lookup[, scientific_name_key := paste(genus, species)]

  matched <- annotation[lookup, on = .(genus, scientificName = scientific_name_key), which = TRUE, nomatch = NULL]
  annotation[lookup,
    `:=`(
      genus                = i.correct_genus,
      specificEpithet      = i.correct_specific_epithet,
      infraspecificEpithet = i.correct_infraspecific_epithet,
      scientificName       = i.correct_scientific_name
    ),
    on = .(genus, scientificName = scientific_name_key)
  ]
  message(sprintf("PR2 genus/species correction: %d rows corrected.", length(matched)))

  # Report PR2 genus/species mismatches not covered by the lookup table
  for (f in dada2_files) {
    dada2 <- fread(f, sep = "\t", na.strings = "")
    if (!all(c("Genus", "Species") %in% names(dada2))) {
      warning(basename(f), " has no Genus/Species columns; skipping mismatch check")
      next
    }
    dada2[, genus_in_species := sub("_[^_]+$", "", Species)]
    new_mismatches <- unique(dada2[
      !is.na(Species) & genus_in_species != Genus &
        !paste(Genus, Species) %in% lookup[, paste(genus, species)],
      .(Genus, Species)
    ])
    if (nrow(new_mismatches) > 0) {
      warning(
        "PR2 genus/species mismatches in ", basename(f), " not covered by ",
        basename(lookup_file), "; check them and add corrections if needed:\n",
        paste(capture.output(print(new_mismatches)), collapse = "\n")
      )
    }
  }
  if (length(dada2_files) == 0) {
    message("No input/ASV_tax.pr2_*.tsv found; skipped check for PR2 mismatches not in the lookup table.")
  }
  invisible(annotation)
}

correct_coidb <- function(annotation) {
  is_unresolved <- !is.na(annotation$genus) & grepl("_X+$", annotation$genus)
  annotation[is_unresolved, `:=`(specificEpithet = "X", infraspecificEpithet = NA_character_)]
  # Rows without a BOLD BIN in otu (it may also hold blanks)
  annotation[
    is_unresolved & !grepl("^BOLD:", otu),
    scientificName := sub("(X+)$", "\\1X", genus)
  ]
  message(sprintf("COIDB _X correction: %d rows corrected.", sum(is_unresolved)))
  invisible(annotation)
}

correct_taxonomy <- function(annotation) {
  ref_dbs <- unique(na.omit(annotation$reference_db))
  if (any(grepl("^PR2", ref_dbs))) {
    correct_pr2(
      annotation,
      lookup_file = file.path(taxonomy_corrections_dir, "pr2-correction-lookup.tsv"),
      dada2_files = Sys.glob("input/ASV_tax.pr2_*.tsv")
    )
  }
  if (any(grepl("^COIDB", ref_dbs))) {
    correct_coidb(annotation)
  }
  invisible(annotation)
}

correct_taxonomy(annotation)
