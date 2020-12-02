#!/usr/bin/env python3
"""
Example unit tests for the mol-mod system.

This system should be used to test that as much of the python code as possible
is working as intended.
"""

import os
import sys
import unittest

# set some environment variables as they will be needed when we import
# create_app

os.environ['FLASK_ENV'] = 'develop'
os.environ['SECRET_KEY'] = 'testing'
os.environ['POSTGREST_HOST'] = 'localhost'

try:
    from molmod import create_app
except ImportError:
    print("Error: Couldn't import flask. Make sure that you have activated your"
          " conda or virtual environment.")
    sys.exit(1)

APP = create_app()

class FlaskTest(unittest.TestCase):
    """
    Starts and stops the flask application so that endpoints can be tested.
    """

    def setUp(self):
        """
        Starts the flask APP on port `self.PORT`.
        """
        APP.config["TESTING"] = True
        APP.config["WTF_CSRF_ENABLED"] = False
        APP.config["DEBUG"] = False
        APP.static_folder = "./static/"
        self.app = APP.test_client()
        super().setUp()


class EndpointTest(FlaskTest):
    """
    Tests flask endpoints.

    More info on testing flask applications is available at:
    https://flask.palletsprojects.com/en/1.1.x/testing/

    Example:
    """

    def test_index(self):
        """
        Checks that the main endpoint (/) is available.
        """
        self.assertEqual(self.app.get("/").status_code, 200)

    def test_blast(self):
        """
        Checks that the blast endpoint (/blast) is available.
        """
        self.assertEqual(self.app.get("/blast").status_code, 200)

class BlastTest(FlaskTest):
    """
    These are also flask endpoints, so they could be in the same class as the
    other tests above, but it can be good to structure tests in more classes.
    The BLAST functionality is a central part of the application so it makes
    sense to have a separate testing class for that.

    Example:
    """

    def test_blast_post(self):
        """
        Checks that the blast endpoint accepts blast forms.
        """
        correct_form = {'sequence': '>test\nATGTCGATGT',
                        'min_identify': 99, 'min_qry_cover': 100,}

        success = self.app.post("/blast", data=correct_form)
        self.assertEqual(success.status_code, 200)

        # This should include more tests to see that the form doesn't accept
        # malformed forms, and returns the appropriate errors and status codes.

if __name__ == "__main__":
    unittest.main()
