library(httr)
library(rvest)
library(jsonlite)

login <- function(username, password) {
  login_url <- "https://auth.biodiversitydata.se/cas/login"
  session <- html_session(login_url)
  form <- html_form(session)[[1]]
  execution_value <- html_nodes(form, xpath = "//input[@name='execution']") %>% html_attr("value")
  payload <- list(
    username = username,
    password = password,
    `_eventId` = 'submit',
    submit = 'LOGIN',
    execution = execution_value
  )
  response <- rvest::submit_form(session, form = form, values = payload)
  if (response$status_code == 200) {
    return(response)
  } else {
    stop("Login failed")
  }
}

get_dataset_list <- function(session) {
  url <- 'https://asv-portal.biodiversitydata.se/list_datasets'
  response <- httr::GET(url)
  if (response$status_code == 200) {
    dataset_list <- jsonlite::fromJSON(content(response, "text"))
    return(dataset_list)
  } else {
    stop("Failed to fetch dataset list")
  }
}

filter_datasets <- function(dataset_list, key, values) {
  if (is.null(values)) {
    return(dataset_list)
  }
  filtered_datasets <- dataset_list[which(dataset_list[[key]] %in% values)]
  return(filtered_datasets)
}

download_datasets <- function(session, datasets) {
  for (dataset in datasets) {
    tryCatch({
      link <- dataset$zip_link
      response <- httr::GET(link)
      if (response$status_code == 200) {
        filename <- paste0(dataset$dataset_id, ".zip")
        writeBin(content(response, "raw"), filename)
        cat("Downloaded:", filename, "\n")
      } else {
        cat("Failed to download", link, "\n")
      }
    }, error = function(e) {
      cat("An error occurred while downloading", link, ":", conditionMessage(e), "\n")
    })
  }
}

main <- function() {
  tryCatch({
    credentials <- jsonlite::read_json('.cas.cred')

    username <- credentials$username
    password <- credentials$password

    session <- login(username, password)

    dataset_list <- get_dataset_list(session)
    cat('\nAVAILABLE DATASETS:\n\n')
    print(dataset_list)

    filtered_list <- filter_datasets(dataset_list, 'target_gene', c('COI'))
    cat('\nSELECTED DATASETS:\n\n')
    print(filtered_list)

    cat('\nSTARTING DOWNLOAD:\n\n')
    download_datasets(session, filtered_list)

  }, error = function(e) {
    cat("An error occurred:", conditionMessage(e), "\n")
  })
}

main()
