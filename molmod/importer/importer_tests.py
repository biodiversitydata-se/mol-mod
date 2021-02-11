#!/usr/bin/env python3
"""
Unit tests for the molmod importer db-mapper.
"""

import json
import math
import tempfile
import unittest

from pandas import DataFrame, Timestamp

#pylint: disable=import-error
from db_mapper import as_snake_case, DBMapper, order_tables

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


class DBMapperTests(unittest.TestCase):
    """
    Tests the functions of DBMapper.
    """

    MAPPINGS = {
        'simple': {"A": {"targetTable": "a_values",
                         "AId": {},
                         "AValue": {}},
                   "B": {"targetTable": "b_values",
                         "returning": "b_id",
                         "BId": {},
                         "val": {"field": "b_value"}}
                   }
    }

    def test_sheets(self):
        """
        Tests that the `sheets` property returns the correct data when a mapping
        is loaded.
        """
        for mapping in self.MAPPINGS.values():
            with tempfile.NamedTemporaryFile('w+') as mapping_file:
                json.dump(mapping, mapping_file)
                mapping_file.seek(0)
                mapper = DBMapper(mapping_file.name)
                self.assertEqual(mapper.sheets, list(mapping.keys()))

    def test_get_fields(self):
        """
        Tests the field formatting of the DBMapper. This function implicitly
        tests the `target_field` function as well.
        """
        mapping = self.MAPPINGS['simple']
        with tempfile.NamedTemporaryFile('w+') as mapping_file:
            json.dump(mapping, mapping_file)
            mapping_file.seek(0)
            mapper = DBMapper(mapping_file.name)
            self.assertEqual(mapper.get_fields("A"), ['a_id', 'a_value'])
            self.assertEqual(mapper.get_fields("B"), ['b_id', 'b_value'])

    def test_format_value(self):
        """
        Tests the `_format_value` function of DBMapper. This function is
        supposed to return values formatted for sql queries.
        """
        vals = [(1, 1), (1.5, 1.5), ('text', "'text'"), (None, 'NULL'),
                (Timestamp(year=2021, month=2, day=1), "'2021-02-01 00:00:00'"),
                ("", "''"), (math.nan, "'NaN'")
                ]

        mapping = self.MAPPINGS['simple']
        with tempfile.NamedTemporaryFile('w+') as mapping_file:
            json.dump(mapping, mapping_file)
            mapping_file.seek(0)
            mapper = DBMapper(mapping_file.name)
            for value, result in vals:
                self.assertEqual(mapper._format_value(value), result)
