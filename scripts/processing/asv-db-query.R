# Read-only queries to the ASV portal database, over ssh to the server named
# in ASV_DB_SSH_HOST (e.g. set in ~/.Renviron), or 'local' for a local copy.
# No passwords are needed: the database container's own settings are used.

library(data.table)

# Run a query and return the result as a table, or NULL (with a warning) if
# the database cannot be reached
query_asv_db <- function(sql, host = Sys.getenv("ASV_DB_SSH_HOST")) {
  if (host == "") {
    warning("ASV_DB_SSH_HOST is not set; the ASV portal database was not queried")
    return(NULL)
  }
  psql <- paste(
    "PGOPTIONS='-c default_transaction_read_only=on'",
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --csv -v ON_ERROR_STOP=1'
  )
  docker_cmd <- paste("docker exec -i asv-db sh -c", shQuote(psql))
  out <- tryCatch(
    if (host == "local") {
      system(docker_cmd, input = sql, intern = TRUE)
    } else {
      system2(
        "ssh",
        c("-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, shQuote(docker_cmd)),
        input = sql, stdout = TRUE
      )
    },
    error = function(e) NULL,
    warning = function(w) NULL
  )
  # A successful query returns at least the CSV header
  if (length(out) < 1) {
    warning("Could not query the ASV portal database on '", host, "'")
    return(NULL)
  }
  fread(text = paste(out, collapse = "\n"), colClasses = "character")
}
