#!/usr/bin/env python3
"""
Unit tests for the molmod importer db-mapper.
"""

import unittest

#pylint: disable=import-error
from db_mapper import as_snake_case, order_tables

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


class OrderTabledTest(unittest.TestCase):
    """
    Tests that the `order_tables` function behaves according to expectation.
    """

    def test_valid_paths(self):
        """
        Checks that the function returns valid orders for valid paths. Note that
        there can be multiple correct solutions.
        """
        tables = list('ABCDEFGHIJ')
        references = [('B', 'A'), ('D', 'B'), ('C', 'A'), ('D', 'E')]
        result = order_tables(tables, references)
        # check that all references are in order
        for source, target in references:
            self.assertGreater(result.index(source), result.index(target))
        # check that all tables are present in the output
        for table in tables:
            self.assertGreaterEqual(result.index(table), 0)
        # check that no tables are present more than once
        self.assertEqual(len(result), len(tables))

    def test_circular_paths(self):
        """
        Checks that the function raises the correct exceptions when given
        circular paths.
        """
        tests = [(list('ABCD'),
                  [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]),
                 (list('ABCDE'),
                  [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'B'), ('C', 'E')])
                 ]
        for table, ref in tests:
            self.assertRaises(ValueError, order_tables, table, ref)
