# Script for generating an email draft (.eml) telling the data provider that
# their dataset is published, with links to it in GBIF (incl. DOI) and the
# ASV portal. Run it from the dataset folder once the dataset is flagged as
# public (make status) and exported (make export):
#   Rscript <path-to-mol-mod>/scripts/processing/published-email-generator.R [ipt-short-name]
# The IPT short name defaults to the folder name in lower case. The provider's
# address is taken from the uploaded file name in input/.
# To send: open the draft in Mac Mail, choose Message > Send Again (shift-cmd-D),
# check it and send.
#
# Only public endpoints are used (IPT EML, GBIF API).
# Sender details are read from environment variables (e.g. set in ~/.Renviron):
#   MOLMOD_SENDER_NAME   name used in the signature (required)
#   MOLMOD_SENDER_EMAIL  sender address (required)

ipt_base_url <- "https://www.gbif.se/ipt"
gbif_api_url <- "https://api.gbif.org/v1/dataset"
portal_url <- "https://asv-portal.biodiversitydata.se"

uuid_re <- "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Folder of this script (and of the template)
script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", args[grepl("^--file=", args)])
  if (length(f) == 1) return(dirname(f))
  for (i in rev(seq_len(sys.nframe()))) {
    f <- sys.frame(i)$ofile
    if (!is.null(f)) return(dirname(f))
  }
  "."
})

# Dataset UUID (from the EML packageId) and title, as published in the IPT
get_ipt_info <- function(ipt_resource_id) {
  url <- paste0(ipt_base_url, "/eml.do?r=", ipt_resource_id)
  eml <- tryCatch(paste(readLines(url, warn = FALSE, encoding = "UTF-8"), collapse = "\n"),
                  error = function(e) stop("Could not read EML from ", url))
  package_id <- regmatches(eml, regexpr('packageId="[^"]*"', eml))
  uuid <- regmatches(package_id, regexpr(uuid_re, package_id))
  if (length(uuid) == 0) stop("No dataset UUID in the EML of ", ipt_resource_id)
  uuid
}

# Title and DOI from GBIF; fails if the dataset is not registered
get_gbif_info <- function(uuid) {
  url <- paste0(gbif_api_url, "/", uuid)
  info <- tryCatch(jsonlite::fromJSON(url),
                   error = function(e) stop("Dataset ", uuid, " not found in GBIF (registered?)"))
  if (is.null(info$doi)) stop("GBIF has no DOI for dataset ", uuid)
  list(title = info$title, doi = info$doi)
}

# Provider address from the uploaded file name (<email>_<YYMMDD-HHMMSS>_...)
get_provider_email <- function(input_dir = "input") {
  files <- list.files(input_dir, pattern = "^[^_]+@[^_]+_[0-9]{6}-[0-9]{6}_")
  emails <- unique(sub("_.*", "", files))
  if (length(emails) != 1) {
    stop("Expected one uploaded file with a provider address in ", input_dir,
         ", found: ", paste(emails, collapse = ", "))
  }
  emails
}

html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  gsub(">", "&gt;", x, fixed = TRUE)
}

generate_published_email <- function(ipt_resource_id = tolower(basename(getwd())),
                                     template_file = file.path(script_dir, "published-email-template.html"),
                                     out_file = "draft_published_email.eml") {
  sender_name <- Sys.getenv("MOLMOD_SENDER_NAME")
  sender <- Sys.getenv("MOLMOD_SENDER_EMAIL")
  if (sender_name == "" || sender == "") {
    stop("Set environment variables MOLMOD_SENDER_NAME and MOLMOD_SENDER_EMAIL (e.g. in ~/.Renviron)")
  }

  provider_email <- get_provider_email()
  uuid <- get_ipt_info(ipt_resource_id)
  gbif <- get_gbif_info(uuid)

  replacements <- list(
    "%title%" = html_escape(gbif$title),
    "%gbif-link%" = paste0("https://www.gbif.org/dataset/", uuid),
    "%doi-link%" = paste0("https://doi.org/", gbif$doi),
    "%portal-link%" = portal_url,
    "%download-link%" = paste0(portal_url, "/download"),
    "%sender-name%" = sender_name,
    "%sender-email%" = sender
  )
  body <- paste(readLines(template_file, encoding = "UTF-8"), collapse = "\n")
  for (key in names(replacements)) {
    body <- gsub(key, replacements[[key]], body, fixed = TRUE)
  }
  header <- sprintf(
    "From: %s\nTo: %s\nSubject: %s\nContent-Type: text/html; charset=UTF-8\n",
    sender, provider_email, "Your ASV portal dataset is published"
  )
  writeLines(c(header, body), out_file, useBytes = TRUE)
  message("Wrote ", out_file, " (", gbif$title, ", doi:", gbif$doi, ")")
}

if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) > 1) {
    stop("Usage: Rscript published-email-generator.R [ipt-short-name]")
  }
  do.call(generate_published_email, as.list(args))
}
