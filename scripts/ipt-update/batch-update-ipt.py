#!/usr/bin/env python3
"""
This script can be used for batch re-publishing of datasets in the IPT when
only data or metadata values have been updated. It assumes that credentials
and SQL for accessing data in ASV-DB, or column mapping between ASV-DB and DwC,
have not changed since the last publication.

To use the script, add IPT login credentials in in .ipt.cred, (or uncomment a
section of the script to type these at prompt instead). Also add IPT resource
ID:s and version update summaries in resources.tsv.
 """

import csv
import json  # If getting usr/pwd from file
import sys
import requests
# import getpass  # If typing usr/pwd at prompt
import re

# Load credentials
with open('.ipt.cred') as json_file:
    credentials = json.load(json_file)
username = credentials['username']
password = credentials['password']

# # Alternatively, to type usr/pwd at prompt:
# username = input('IPT user: ')
# password = getpass.getpass('IPT password: ')

# Load update info
resources = []
with open('resources.tsv', mode='r', newline='') as tsv_file:
    tsv_reader = csv.DictReader(tsv_file, delimiter='\t')
    for row in tsv_reader:
        resources.append({'id': row['id'], 'summary': row['summary']})

# Construct URLs
ipt_server = 'www.gbif.se/ipt'  # Swedish IPT instance
# ipt_server = 'ipt.gbif.org'  # Demo IPT
host_url = f'https://{ipt_server}/'
login_form_url = host_url + 'login.do'
login_url = host_url + 'login.do'
publish_url = host_url + 'manage/publish.do'

# Log in
# IPT >= 3.3 puts the login token in a hidden 'csrfToken' input on the login
# form; older versions set it as a 'CSRFtoken' cookie.
session = requests.Session()
response = session.get(login_form_url, verify=True)  # retrieve token
match = re.search(r'name="csrfToken"[^>]*value="([^"]+)"', response.text)
payload = {
    'email': username,
    'password': password,
    'csrfToken': match.group(1) if match else session.cookies.get('CSRFtoken'),
    'login': 'Login'
}
session.post(login_url, data=payload)
# Unsure how to check success, as login failure also returns 200 here

# IPT >= 3.3 also requires the session token from the 'ipt-csrf-token' meta
# tag (shown to logged-in users) on every state-changing request.
response = session.get(host_url + 'manage/resources.do')
meta = re.search(r'<meta[^>]*name="ipt-csrf-token"[^>]*>', response.text)
match = re.search(r'content="([^"]+)"', meta.group(0)) if meta else None
session_csrf = match.group(1) if match else None
if session_csrf:
    session.headers['X-CSRF-Token'] = session_csrf

login_check = 0
pub_info = []

for r in resources:
    # Send publish request (assuming login was successful)
    params = {
        'r': r['id'],
        'autopublish': '',
        'currPubMode': 'AUTO_PUBLISH_OFF',
        'pubMode': '',
        'currPubFreq': '',
        'pubFreq': '',
        'publish': 'Publish',
        'summary': r['summary']
    }
    if session_csrf:
        params['iptCsrfToken'] = session_csrf
    response = session.post(publish_url, data=params)

    # Check log-in for first resource only
    if login_check == 0:
        if 'login-button' not in response.text:
            print(f'Successfully logged in to {host_url}\n')
            login_check = 1
        else:
            print(f'Login to {host_url} failed\n')
            sys.exit()

    pattern = r'Publishing version #([\d.]+) of resource \S+ started'
    match = re.search(pattern, response.text)
    if match:
        version = match.group(1)
        pub_info.append({'resource_id': r['id'],
                         'version': version,
                         'status': 'Started'})
        print(f'Starting republication of version {version} ' +
              f"of resource {r['id']}")
    else:
        epattern = r'<h1 class="pb-2 mb-0 pt-2 text-gbif-header.*?">(.*?)</h1>'
        match = (re.search(epattern, response.text, re.DOTALL)
                 or re.search(r'<title>(.*?)</title>', response.text,
                              re.DOTALL))
        error = (match.group(1).strip() if match
                 else f'HTTP {response.status_code}')
        # IPT >= 3.3 answers an accepted publish request with the resource
        # overview page instead of a "Publishing version ... started" message
        if error.startswith('Overview'):
            pub_info.append({'resource_id': r['id'],
                             'version': None,
                             'status': 'Started'})
            print(f"Starting republication of resource {r['id']}")
            continue
        if (error == 'Publication'):
            error = 'Already busy'
        pub_info.append({'resource_id': r['id'],
                         'version': None,
                         'status': error})
        print(f"Failed to start republication of resource {r['id']} " +
              f'due to {error}')

with open('pub_info.tsv', mode='w', newline='') as tsv_file:
    cols = ['resource_id', 'version', 'status']
    tsv_writer = csv.DictWriter(tsv_file, fieldnames=cols, delimiter='\t')
    tsv_writer.writeheader()
    tsv_writer.writerows(pub_info)

if len(pub_info) > 0:
    print("Publication information written to 'pub_info.tsv'")
