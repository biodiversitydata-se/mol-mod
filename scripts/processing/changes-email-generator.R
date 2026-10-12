# Drafts an email (draft_changes_email.eml) listing the changes made to the
# provider's data, for them to confirm before import. Run at the end of
# asv-input-processing.R; nothing is drafted if no change was logged.
# Open the draft in Mac Mail, move it to Drafts, check it and send.
#
# Sender details are read from environment variables (e.g. set in ~/.Renviron):
#   MOLMOD_SENDER_NAME   name used in the signature (required)
#   MOLMOD_SENDER_EMAIL  sender address (required)

# Folder of this script, to find the email template
changes_email_dir <- local({
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

html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  gsub(">", "&gt;", x, fixed = TRUE)
}

generate_changes_email <- function(dataset, changes,
                                   template_file = file.path(changes_email_dir, "changes-email-template.html")) {
  if (nrow(changes) == 0) {
    message("No changes recorded; no change email drafted.")
    return(invisible(NULL))
  }
  sender_name <- Sys.getenv("MOLMOD_SENDER_NAME")
  sender <- Sys.getenv("MOLMOD_SENDER_EMAIL")
  if (sender_name == "" || sender == "") {
    stop("Set environment variables MOLMOD_SENDER_NAME and MOLMOD_SENDER_EMAIL (e.g. in ~/.Renviron)")
  }

  filename <- dataset$filename
  provider_email <- sub("_.*", "", filename)
  date_time <- sub("_", "", regmatches(filename, regexpr("_[0-9]{6}-[0-9]{6}", filename)))
  orig_name <- sub(".*_[0-9]{6}-[0-9]{6}_", "", filename)

  items <- changes[, sprintf(
    "        <li>%s, <i>%s</i>: '%s' &rarr; '%s'%s. %s</li>",
    html_escape(change_sheet(table, field)), html_escape(field), html_escape(old),
    html_escape(new), change_rows(table, field, n), html_escape(reason)
  )]

  replacements <- list(
    "%dataset-file%" = orig_name,
    "%date-time%" = date_time,
    "%changes%" = paste(items, collapse = "\n"),
    "%sender-name%" = sender_name,
    "%sender-email%" = sender
  )
  email <- paste(readLines(template_file), collapse = "\n")
  for (i in seq_along(replacements)) {
    email <- gsub(names(replacements)[i], replacements[[i]], email, fixed = TRUE)
  }
  header <- sprintf(
    "From: %s\nTo: %s\nSubject: %s\nContent-Type: text/html; charset=UTF-8\n",
    sender, provider_email, "Changes to your ASV portal submission before import"
  )
  writeLines(c(header, email), "draft_changes_email.eml")
  message("Wrote draft_changes_email.eml (", nrow(changes), " change(s))")
  invisible(email)
}

generate_changes_email(dataset, changes)
