# Script for generating an email draft (.eml) with dataset-specific details and links
# Expects email-template.html in the same folder as this script, and dataset object
# from asv-input-processing.R. Source it from the dataset folder, e.g.:
#   source("<path-to-mol-mod>/scripts/processing/email-generator.R")
# Open in Mac mail and move to Draft to edit pwd and send
#
# Sender details are read from environment variables (e.g. set in ~/.Renviron),
# so that no personal data is stored in the repo:
#   MOLMOD_SENDER_NAME   name used in the signature (required)
#   MOLMOD_SENDER_EMAIL  sender address (required)

# IPT instance used for resource and metadata links
ipt_base_url <- "https://www.gbif.se/ipt"

# Folder of this script (and of the template) when sourced (innermost
# source() call), else the working directory
script_dir <- local({
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

generate_email <- function(dataset, template_file = file.path(script_dir, "email-template.html")) {
  sender_name <- Sys.getenv("MOLMOD_SENDER_NAME")
  sender <- Sys.getenv("MOLMOD_SENDER_EMAIL")
  if (sender_name == "" || sender == "") {
    stop("Set environment variables MOLMOD_SENDER_NAME and MOLMOD_SENDER_EMAIL (e.g. in ~/.Renviron)")
  }

  # Get data from ASV input processing
  filename <- dataset$filename
  provider_email <- sub("_.*", "", filename)
  date_time <- regmatches(filename, regexpr("_[0-9]{6}-[0-9]{6}", filename))
  date_time <- sub("_", "", date_time)
  orig_name <- sub(".*_[0-9]{6}-[0-9]{6}_", "", filename)

  # Fill data into template
  replacements <- list(
    "%dataset-file%" = orig_name,
    "%date-time%" = date_time,
    "%provider-email%" = provider_email,
    "%resource-link%" = paste0(ipt_base_url, "/manage/resource.do?r=", dataset$datasetID),
    "%metadata-link%" = paste0(ipt_base_url, "/manage/resource.do?r=", dataset$datasetID, "#anchor-metadata"),
    "%sender-name%" = sender_name,
    "%sender-email%" = sender
  )
  email_template <- paste(readLines(template_file), collapse = "\n")
  for (i in 1:length(replacements)) {
    email_template <- gsub(names(replacements)[i], replacements[[i]], email_template, fixed = TRUE)
  }
  # Add header
  subject <- "Your ASV portal submission"
  email_header <- sprintf(
    "From: %s\nTo: %s\nSubject: %s\nContent-Type: text/html; charset=UTF-8\n",
    sender, provider_email, subject
  )
  writeLines(c(email_header, email_template), "draft_email.eml")
}

generate_email(dataset)
