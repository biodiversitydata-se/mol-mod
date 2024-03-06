import requests
import json
from bs4 import BeautifulSoup
from typing import Optional, List


def login(username: str, password: str) -> requests.Session:
    """Logs in user and returns a session"""
    login_url = "https://auth.biodiversitydata.se/cas/login"
    soup = BeautifulSoup(requests.get(login_url).content, 'html.parser')
    # First get token
    execution_value = soup.find('input', {'name': 'execution'}).get('value')
    # Then log in
    payload = {
        'username': username,
        'password': password,
        '_eventId': 'submit',
        'submit': 'LOGIN',
        'execution': execution_value
    }
    with requests.Session() as session:
        response = session.post(login_url, data=payload)
        if response.status_code == 200:
            return session
        else:
            raise Exception("Login failed")


def get_dataset_list(session: requests.Session) -> List[dict]:
    """Gets list of datasets available for download from ASV portal"""
    url = 'https://asv-portal.biodiversitydata.se/list_datasets'
    response = session.get(url)
    if response.status_code == 200:
        dataset_list = json.loads(response.text)
        return dataset_list
    else:
        raise Exception("Failed to fetch dataset list")


def filter_datasets(dataset_list: List[dict], key: str,
                    values: Optional[List[str]]) -> List[dict]:
    """Filters datasets on some parameter and value(s), if supplied"""
    if values is None:
        return dataset_list
    filtered_datasets = [ds for ds in dataset_list
                         if key in ds and ds[key] in values]
    return filtered_datasets


def download_datasets(session: requests.Session, datasets: List[dict]):
    """Download dataset zip(s) from ASV portal"""
    for dataset in datasets:
        try:
            link = dataset['zip_link']
            response = session.get(link)
            if response.status_code == 200:
                filename = f"{dataset['dataset_id']}.zip"
                with open(filename, 'wb') as file:
                    file.write(response.content)
                    print(f"Downloaded: {filename}")
            else:
                print(f"Failed to download {link}")
        except Exception as e:
            print(f"An error occurred while downloading {link}: {str(e)}")


def main():
    try:
        with open('.cas.cred') as json_file:
            credentials = json.load(json_file)

        username = credentials["username"]
        password = credentials["password"]

        session = login(username, password)

        dataset_list = get_dataset_list(session)
        print('\nAVAILABLE DATASETS:\n\n')
        print(json.dumps(dataset_list, indent=4))

        filtered_list = filter_datasets(dataset_list, 'target_gene',
                                        ['COI'])
        print('\nSELECTED DATASETS:\n\n')
        print(json.dumps(filtered_list, indent=4))

        print('\nSTARTING DOWNLOAD:\n\n')
        download_datasets(session, filtered_list)

    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
