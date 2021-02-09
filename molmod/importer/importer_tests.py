#!/usr/bin/env python3
"""
Unit tests for the molmod importer db-mapper.
"""

import unittest

#pylint: disable=import-error
from db_mapper import as_snake_case

class AsSnakeCaseTest(unittest.TestCase):
    """
    Tests that the `as_snake_case` function behaves according to expectation.
    """

    def test_camel_case(self):
        """
        Checks that the function returns snake_case when given CamelCase.
        """
        self.assertEqual("this_is_snake_case", as_snake_case("ThisIsSnakeCase"))
        self.assertEqual("i_am_a_snake", as_snake_case("IAmASnake"))

    def test_snake_case(self):
        """
        Checks that the function returns the same string when given snake_case.
        """
        self.assertEqual("snake_case", as_snake_case("snake_case"))
