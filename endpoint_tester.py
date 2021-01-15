#!/usr/bin/env python3
"""
This script can be used to test-fetch system endpoints and get time statistics
for the retrieval time.
"""

import sys
import timeit
from functools import partial
from html.parser import HTMLParser

try:
    import requests
except ModuleNotFoundError:
    sys.stderr.write("ERROR: Couldn't find the requests module.\n\n")
    sys.stderr.write("Install it in a virtual environment using:\n")
    sys.stderr.write(" $ python3 -m venv venv\n")
    sys.stderr.write("activate the virtual environment with:\n")
    sys.stderr.write(" $ source venv/bin/activate\n")
    sys.stderr.write("and install the app requirements with:\n")
    sys.stderr.write(" $ pip3 install -r molmod/requirements.txt\n")
    sys.exit(1)

# There is an abstract method for error reporting in HTMLParser,
# but it wouldn't help us to implement it.
# pylint: disable=abstract-method


class CSRFFinder(HTMLParser):
    """
    Simple HTMLParser that reports the `value` of any tag that has
    `id='csrf_token'`.
    """
    def __init__(self):
        super().__init__()
        self.csrf_token = None

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if attr_dict.get('id', None) == 'csrf_token':
            self.csrf_token = attr_dict.get('value', None)


class EndpointTester():
    """
    This class keeps track of an endpoint, it's current statistics, and the
    tokens needed to make proper requests to the endpoint.
    """

    # Pylint prefers to have a max of 5 arguments, but I think we need all 6 to
    # keep the class easy to use.
    # pylint: disable=too-many-arguments
    def __init__(self, host, endpoint, protocol='GET', data=None, csrf=''):
        """
        Sets the endpoint, protocol, and optional data for the request to test.
        """
        self.host = host
        self.endpoint = endpoint
        self.protocol = protocol
        self.data = data
        self.csrf_url = csrf
        self.headers = {}
        self.mean_time = None
        self._prepare_headers()

    def _prepare_headers(self):
        """
        Prepares the neccessary headers needed to make requests to the host.
        This is done by sending a GET request to `self.host/self.csrf_url` and
        extracting a session cookie and a csrf token.
        """
        csrf_url = f'{self.host}/{self.csrf_url}'
        req = requests.get(csrf_url)
        if req.ok:
            # save cookies for reuse
            session = req.cookies.get('session', None)
            if session:
                self.headers['Cookie'] = f'session={session}'

            # find csrf token.
            csrf_finder = CSRFFinder()
            csrf_finder.feed(req.text)
            self.headers['X-CSRFToken'] = csrf_finder.csrf_token

    def run_test(self, num_requests=10):
        """
        Sends the prepared request `num_requests` times, and reports statistics
        for the request times.
        """
        req_type = {'GET': requests.get, 'POST': requests.post}[self.protocol]
        endpoint = f'{self.host}/{self.endpoint}'
        func = partial(req_type, endpoint, headers=self.headers,
                       data=self.data)

        # test to see that we're testing a valid request
        test = func()
        if test.ok:
            self.mean_time = 1000*timeit.timeit(func, number=num_requests)
        else:
            print("Error: invalid request")

    def __repr__(self):
        """
        Print formatting for the class. Prints the protocol and endpoint, and
        the mean request time if available.
        """
        output = f'{self.protocol} /{self.endpoint}'
        if self.mean_time:
            output += f', mean: {round(self.mean_time)} ms'
        return output


if __name__ == '__main__':
    HOST = 'http://localhost:5000'
    ENDPOINTS = [('request_drop_options/gene', 'POST', {'term': '', 'page': 1},
                  'filter')]
    TESTERS = [EndpointTester(HOST, *e) for e in ENDPOINTS]

    for tester in TESTERS:
        tester.run_test(10)
        print(tester)
