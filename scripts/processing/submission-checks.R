# Checks submitted data for likely mistakes, such as a primer name that does
# not match its sequence, new marker or institution values, signs of Excel
# autofill, or IDs that differ between sheets. Nothing is changed: findings are
# listed in output/submission-checks.txt for you to review.
#   WARN    probably wrong
#   REVIEW  new or unusual value, check by hand
# Marker, primer and institution values are compared with those already in the
# ASV portal database, and new institution IDs are looked up in ROR.
# Errors that rule out a valid import stop asv-input-processing.R instead.

library(data.table)

# Folder of this script, to find asv-db-query.R
submission_checks_dir <- local({
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
source(file.path(submission_checks_dir, "asv-db-query.R"))

# Search pattern for a primer (with ambiguity codes) at the start of a sequence
iupac_regex <- function(primer) {
  codes <- c(
    A = "A", C = "C", G = "G", T = "T", U = "T", R = "[AG]", Y = "[CT]",
    S = "[CG]", W = "[AT]", K = "[GT]", M = "[AC]", B = "[CGT]", D = "[AGT]",
    H = "[ACT]", V = "[ACG]", N = ".", I = "."
  )
  chars <- strsplit(toupper(primer), "")[[1]]
  paste0("^", paste(ifelse(chars %in% names(codes), codes[chars], chars), collapse = ""))
}

# Suggested correction for section 14 of the dated script
fix_line <- function(table, field, old, new, reason) {
  sprintf('change_value(%s, "%s", "%s", "%s", "%s")', table, field, old, new, reason)
}

# Compare a pair of submitted values (e.g. primer name and sequence) with the
# pairs already in the database (ignoring upper/lower case in names). 'fields'
# are the column names in 'table'; 'labels' are readable names for messages
# and for the reasons shown to the provider, e.g. c("primer name", "primer sequence").
check_pair <- function(in_name, in_value, known, check, table, fields, labels) {
  finding <- function(level, message, fix = "") {
    data.table(level = level, check = check, message = message, fix = fix)
  }
  cap <- function(x) paste0(toupper(substr(x, 1, 1)), substring(x, 2))
  if (is.na(in_name) && is.na(in_value)) {
    return(NULL)
  }
  if (is.null(known)) {
    return(finding("REVIEW", sprintf(
      "%s '%s' / %s '%s' not compared with the database (no connection)",
      cap(labels[1]), in_name, labels[2], in_value
    )))
  }
  same_name_rows <- !is.na(known$name) & !is.na(in_name) & toupper(known$name) == toupper(in_name)
  same_value_rows <- !is.na(known$value) & !is.na(in_value) & known$value == in_value
  same_pair <- known[same_name_rows & same_value_rows]
  if (nrow(same_pair) > 0) {
    if (!in_name %in% same_pair$name) {
      db_name <- same_pair$name[1]
      return(finding("REVIEW", sprintf(
        "%s '%s' is spelled '%s' in the database", cap(labels[1]), in_name, db_name
      ), fix_line(table, fields[1], in_name, db_name,
                  "Spelling harmonised with existing datasets")))
    }
    return(NULL)
  }
  if (any(same_value_rows)) {
    # The value is known under another name: suggest that name
    db_name <- known$name[same_value_rows][1]
    return(finding("WARN", sprintf(
      "%s '%s' does not match %s '%s' (in the database, '%s' goes with '%s')",
      cap(labels[1]), in_name, labels[2], in_value, in_value, db_name
    ), fix_line(table, fields[1], in_name, db_name,
                sprintf("%s did not match %s %s", cap(labels[1]), labels[2], in_value))))
  }
  if (any(same_name_rows)) {
    db_value <- known$value[same_name_rows][1]
    return(finding("WARN", sprintf(
      "%s '%s' does not match %s '%s' (in the database, '%s' goes with '%s')",
      cap(labels[2]), in_value, labels[1], in_name, in_name, db_value
    ), paste0(
      "# Either the ", labels[1], " or the ", labels[2],
      " is wrong; check with the provider, e.g.:\n",
      fix_line(table, fields[2], in_value, db_value,
               sprintf("%s did not match %s %s", cap(labels[2]), labels[1], in_name))
    )))
  }
  finding("REVIEW", sprintf(
    "New %s '%s' / %s '%s' (not in the database)", labels[1], in_name, labels[2], in_value
  ))
}

# Organisation name for a ROR ID, or NA if ROR cannot be reached
ror_name <- function(ror_id) {
  id <- sub("^https?://ror.org/", "", ror_id)
  old <- options(timeout = 10)
  on.exit(options(old))
  org <- tryCatch(
    jsonlite::fromJSON(paste0("https://api.ror.org/v2/organizations/", id)),
    error = function(e) NULL
  )
  if (is.null(org)) {
    return(NA_character_)
  }
  shown <- vapply(org$names$types, function(x) "ror_display" %in% x, logical(1))
  if (any(shown)) org$names$value[shown][1] else org$names$value[1]
}

# IDs that differ between the sheets; such samples and ASVs would otherwise be
# left out without notice
check_sheet_ids <- function(Samples, Taxonomy, ASV_table) {
  out <- list()
  add <- function(level, message) {
    out[[length(out) + 1]] <<- data.table(level = level, check = "sheet IDs", message = message,
                                          fix = "")
  }
  show <- function(x) paste0(paste(head(x, 5), collapse = ", "), if (length(x) > 5) ", ...")

  sample_ids <- as.character(Samples$eventID)
  count_cols <- setdiff(names(ASV_table), "asv_id_alias")
  tax_ids <- as.character(Taxonomy$asv_id_alias)
  tab_ids <- as.character(ASV_table$asv_id_alias)

  only_table <- setdiff(count_cols, sample_ids)
  if (length(only_table) > 0) add("WARN", sprintf(
    "%d ASV-table column(s) not in Samples (dropped): %s", length(only_table), show(only_table)))
  only_samples <- setdiff(sample_ids, count_cols)
  if (length(only_samples) > 0) add("WARN", sprintf(
    "%d sample(s) in Samples without ASV-table column: %s", length(only_samples), show(only_samples)))
  only_tax <- setdiff(tax_ids, tab_ids)
  if (length(only_tax) > 0) add("REVIEW", sprintf(
    "%d ASV(s) in Taxonomy but not in ASV-table (dropped): %s", length(only_tax), show(only_tax)))

  counts <- ASV_table[, intersect(count_cols, sample_ids), with = FALSE]
  if (ncol(counts) > 0) {
    raw <- unlist(counts, use.names = FALSE)
    raw <- raw[!is.na(raw) & as.character(raw) != ""]
    bad <- unique(raw[is.na(suppressWarnings(as.numeric(as.character(raw))))])
    if (length(bad) > 0) add("WARN", sprintf(
      "Non-numeric values in ASV-table (read as 0): %s", show(bad)))
    totals <- colSums(as.data.frame(lapply(counts, function(x) {
      x <- suppressWarnings(as.numeric(as.character(x)))
      x[is.na(x)] <- 0
      x
    })))
    empty <- names(totals)[totals == 0]
    if (length(empty) > 0) add("WARN", sprintf(
      "%d sample(s) without any reads: %s", length(empty), show(empty)))
  }
  rbindlist(out)
}

run_submission_checks <- function(event, dna, asv, occurrence, marker,
                                Samples = NULL, Taxonomy = NULL, ASV_table = NULL,
                                file = "output/submission-checks.txt") {
  findings <- list()
  add <- function(level, check, message, fix = "") {
    findings[[length(findings) + 1]] <<- data.table(level = level, check = check,
                                                    message = message, fix = fix)
  }
  first <- function(x) {
    x <- unique(na.omit(as.character(x)))
    if (length(x) == 0) NA_character_ else x[1]
  }

  # --- IDs across the input sheets (first pass only) ------------------------
  if (!is.null(Samples) && !is.null(Taxonomy) && !is.null(ASV_table)) {
    findings[[length(findings) + 1]] <- check_sheet_ids(Samples, Taxonomy, ASV_table)
  }

  # --- Marker, primers and institution, compared with the database ---------
  mixs_db <- query_asv_db(paste(
    "SELECT DISTINCT target_gene, target_subfragment, pcr_primer_name_forward,",
    "pcr_primer_forward, pcr_primer_name_reverse, pcr_primer_reverse FROM mixs;"
  ))
  inst_db <- query_asv_db(
    "SELECT DISTINCT institution_code, institution_id FROM sampling_event;"
  )
  # psql writes NULL as an empty field
  for (db in list(mixs_db, inst_db)) {
    if (!is.null(db)) {
      for (col in names(db)) set(db, which(db[[col]] == ""), col, NA_character_)
    }
  }

  target_gene <- first(dna$target_gene)
  if (!is.na(target_gene) && target_gene != marker) {
    add("WARN", "marker", sprintf(
      "Target gene '%s' (Study) does not match marker '%s' (section 1)", target_gene, marker
    ), paste0("# Correct marker in section 1, or:\n", fix_line(
      "dna", "target_gene", target_gene, marker, sprintf("Target gene did not match marker %s", marker))))
  }

  pairs <- list(
    list(check = "target gene", name = target_gene, value = first(dna$target_subfragment),
         fields = c("target_gene", "target_subfragment"),
         labels = c("target gene", "target subfragment")),
    list(check = "forward primer", name = first(dna$pcr_primer_name_forward),
         value = toupper(first(dna$pcr_primer_forward)),
         fields = c("pcr_primer_name_forward", "pcr_primer_forward"),
         labels = c("forward primer name", "forward primer sequence")),
    list(check = "reverse primer", name = first(dna$pcr_primer_name_reverse),
         value = toupper(first(dna$pcr_primer_reverse)),
         fields = c("pcr_primer_name_reverse", "pcr_primer_reverse"),
         labels = c("reverse primer name", "reverse primer sequence"))
  )
  for (p in pairs) {
    known <- if (is.null(mixs_db)) NULL else
      setnames(unique(mixs_db[, p$fields, with = FALSE]), c("name", "value"))
    if (!is.null(known)) known[, value := toupper(value)]
    findings[[length(findings) + 1]] <- check_pair(p$name, p$value, known, p$check,
                                                   "dna", p$fields, p$labels)
  }

  inst_code <- first(event$institutionCode)
  inst_id <- first(event$institutionID)
  known_inst <- if (is.null(inst_db)) NULL else
    setnames(copy(inst_db), c("name", "value"))
  inst_finding <- check_pair(inst_code, inst_id, known_inst, "institution", "event",
                             c("institutionCode", "institutionID"),
                             c("institution code", "institution ID"))
  findings[[length(findings) + 1]] <- inst_finding
  if (!is.null(inst_finding) && !is.na(inst_id) && grepl("ror.org", inst_id)) {
    add("REVIEW", "institution", sprintf("ROR %s is '%s'", inst_id, ror_name(inst_id)))
  }

  # --- Samples: values that should be the same, IDs that should be unique ---
  for (col in c("geodeticDatum", "country", "samplingProtocol", "references",
                "dataGeneralizations", "coordinateUncertaintyInMeters")) {
    vals <- unique(na.omit(as.character(event[[col]])))
    if (length(vals) > 1) {
      add("REVIEW", "samples", sprintf(
        "%s has %d different values (possible Excel autofill?): %s", col, length(vals),
        paste(head(vals, 5), collapse = " | ")
      ), sprintf('# If wrong: change_value(event, "%s", <old>, <new>, <reason>)', col))
    }
  }
  for (col in c("materialSampleID", "associatedSequences")) {
    vals <- na.omit(as.character(event[[col]]))
    dups <- unique(vals[duplicated(vals)])
    if (length(dups) > 0) {
      add("WARN", "samples", sprintf(
        "%s has %d duplicated value(s), e.g. %s", col, length(dups), dups[1]
      ), sprintf('# change_value(event, "%s", "%s", <new>, <reason>, rows = event$eventID == <sample>)', col, dups[1]))
    }
  }

  dates <- as.character(event$eventDate)
  if (any(grepl("^[0-9]{5}$", dates))) {
    add("WARN", "eventDate", "Five-digit eventDate values (Excel date serial numbers?)",
        '# change_value(event, "eventDate", <old>, <YYYY-MM-DD>, "Date converted from Excel format")')
  }
  years <- suppressWarnings(as.integer(substr(dates, 1, 4)))
  if (any(years > as.integer(format(Sys.Date(), "%Y")), na.rm = TRUE)) {
    add("WARN", "eventDate", "eventDate in the future")
  }

  lat <- suppressWarnings(as.numeric(event$decimalLatitude))
  lon <- suppressWarnings(as.numeric(event$decimalLongitude))
  if (any(abs(lat) > 90 | abs(lon) > 180, na.rm = TRUE)) {
    add("WARN", "coordinates", "Latitude or longitude out of range")
  }
  # GBIF requires at least the country of origin for DNA-derived records
  no_country <- is.na(event$country) | !nzchar(trimws(as.character(event$country)))
  if (any(no_country)) {
    add("WARN", "location", sprintf(
      "%d sample(s) without country, e.g. %s", sum(no_country),
      event$eventID[no_country][1]
    ), paste(
      "# Ask the provider, then add and log, e.g.:",
      "# miss <- is.na(event$country) | !nzchar(trimws(event$country))",
      "# event[miss, country := <country>]",
      "# record_change(\"event\", \"country\", NA, <country>, <reason>, sum(miss))",
      sep = "\n"
    ))
  }
  in_sweden <- !is.na(event$country) & grepl("^(Sweden|SE)$", event$country)
  if (any(in_sweden & lat < lon, na.rm = TRUE)) {
    add("WARN", "coordinates", sprintf(
      "%d Swedish sample(s) with latitude < longitude (swapped coordinates?)",
      sum(in_sweden & lat < lon, na.rm = TRUE)
    ), paste(
      "# Swap and log, e.g.:",
      "# swap <- event$country %in% c(\"Sweden\", \"SE\") &",
      "#   as.numeric(event$decimalLatitude) < as.numeric(event$decimalLongitude)",
      "# event[swap, c(\"decimalLatitude\", \"decimalLongitude\") := .(decimalLongitude, decimalLatitude)]",
      "# record_change(\"event\", \"decimalLatitude/decimalLongitude\", \"swapped\", \"corrected\",",
      "#               \"Latitude and longitude were swapped\", sum(swap))",
      sep = "\n"
    ))
  }

  # --- Counts and sequences -------------------------------------------------
  q <- suppressWarnings(as.numeric(occurrence$organism_quantity))
  if (any(q != round(q), na.rm = TRUE)) {
    add("WARN", "counts", "Non-integer read counts (relative abundances instead of counts?)")
  }
  primer <- first(dna$pcr_primer_forward)
  if (!is.na(primer) && nrow(asv) > 0) {
    share <- mean(grepl(iupac_regex(primer), toupper(asv$DNA_sequence)))
    if (share > 0.1) {
      add("WARN", "sequences", sprintf(
        "%.0f %% of ASV sequences start with the forward primer (primers not removed?)",
        100 * share
      ))
    }
  }

  # --- Report ----------------------------------------------------------------
  report <- rbindlist(findings)
  if (nrow(report) == 0) {
    message("Submission checks: no findings.")
    if (file.exists(file)) file.remove(file)
    return(invisible(report))
  }
  report <- report[order(match(level, c("WARN", "REVIEW")))]
  lines <- report[, sprintf("%-6s %-15s %s", level, check, message)]
  # Drop repeated suggestions for the same change (same table, field, old, new)
  fixes <- report[fix != "", fix]
  key_of <- function(f) {
    m <- regmatches(f, regexpr('change_value\\([^,]+, "[^"]*", "[^"]*", "[^"]*"', f))
    if (length(m) == 0) f else m
  }
  fixes <- fixes[!duplicated(vapply(fixes, key_of, character(1)))]
  if (length(fixes) > 0) {
    lines <- c(lines, "", "Fix in section 14 with change_value(), e.g.:", fixes)
  } else {
    lines <- c(lines, "", "Fix in section 14 with change_value().")
  }
  writeLines(lines, file)
  message(
    "\nSubmission checks (", nrow(report), " finding(s), also in ", file, "):\n",
    paste(lines, collapse = "\n"), "\n"
  )
  invisible(report)
}
