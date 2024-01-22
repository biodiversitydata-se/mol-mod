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
ipt_server = 'ipt.gbif.org'  # Demo IPT
# ipt_server = 'www.gbif.se/ipt/'  # Swedish IPT instance
host_url = f'https://{ipt_server}/'
login_form_url = host_url + 'login.do'
login_url = host_url + 'login.do'
publish_url = host_url + 'manage/publish.do'

# Log in
session = requests.Session()
response = session.post(login_form_url, verify=True)  # retrieve token
payload = {
    'email': username,
    'password': password,
    'csrfToken': session.cookies.get('CSRFtoken')
}
session.post(login_url, data=payload)
# Unsure how to check success, as login failure also returns 200 here

login_check = 0
published = []
failed = []

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
    response = session.post(publish_url, data=params)

    # Check log-in for first resource only
    if login_check == 0:
        if 'login-button' not in response.text:
            print(f'Successfully logged in to {host_url}\n')
            login_check = 1
        else:
            print(f'Login to {host_url} failed\n')
            sys.exit()

    if 'success' in response.text:
        published.append(r)
    else:
        failed.append(r)

if len(published) > 0:
    print('The following resources were successfully republished:')
    for p in published:
        print(p)
    print()

if len(failed) > 0:
    print('The following resources could not be republished:')
    for f in failed:
        print(f)
    print()
