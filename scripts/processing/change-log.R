# Log of changes made to the provider's data. Make corrections with
# change_value() (or note other changes with record_change()), so that they are
# listed in output/changes.txt and in the email asking the provider to confirm
# them before import.

library(data.table)

changes <- data.table(
  table = character(), field = character(), old = character(),
  new = character(), n = integer(), reason = character()
)

# Note a change made in another way, e.g. removed samples
record_change <- function(table, field, old, new, reason, n = NA_integer_) {
  changes <<- rbind(changes, data.table(
    table = table, field = field, old = as.character(old),
    new = as.character(new), n = as.integer(n), reason = reason
  ))
  invisible(changes)
}

# Replace old with new in column 'field' of table dt (optionally only in the
# rows where 'rows' is TRUE), and log the change
change_value <- function(dt, field, old, new, reason, rows = NULL,
                         table = deparse(substitute(dt))) {
  if (!field %in% names(dt)) {
    stop("change_value: column '", field, "' not found in ", table)
  }
  hit <- !is.na(dt[[field]]) & as.character(dt[[field]]) == as.character(old)
  if (!is.null(rows)) {
    hit <- hit & rows
  }
  n <- sum(hit)
  if (n == 0) {
    warning("change_value: no rows in ", table, " with ", field, " = '", old, "'")
    return(invisible(dt))
  }
  dt[which(hit), (field) := new]
  record_change(table, field, old, new, reason, n)
  invisible(dt)
}

# The provider's sheet name for a changed value. Values from Study are repeated
# for every sample, so no row count is shown for them.
study_fields <- c("datasetID", "datasetName", "institutionCode", "institutionID", "collectionCode")

from_study <- function(table, field) {
  table %in% c("dna", "dataset") | (table == "event" & field %in% study_fields)
}

change_sheet <- function(table, field) {
  labels <- c(event = "Samples", emof = "Samples", asv = "Taxonomy",
              annotation = "Taxonomy", occurrence = "ASV-table")
  ifelse(from_study(table, field), "Study",
         ifelse(table %in% names(labels), labels[table], table))
}

change_rows <- function(table, field, n) {
  ifelse(is.na(n) | from_study(table, field), "",
         sprintf(" (%d row%s)", n, ifelse(n == 1, "", "s")))
}

# Write the change log as plain text (no file if there are no changes)
write_changes <- function(file = "output/changes.txt") {
  if (nrow(changes) == 0) {
    message("No changes to the provider's data were recorded.")
    if (file.exists(file)) file.remove(file)
    return(invisible(NULL))
  }
  lines <- changes[, sprintf(
    "- %s, %s: '%s' -> '%s'%s. %s",
    change_sheet(table, field), field, old, new, change_rows(table, field, n), reason
  )]
  writeLines(lines, file)
  message("Wrote ", file, " (", nrow(changes), " change(s))")
  invisible(lines)
}
