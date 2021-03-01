#!/usr/bin/env python3
"""
The DBMapper class takes a dictionary of pandas data frames and a json mapping
file, and uses these to generate sql insert queries.
"""

import json
import logging
import math
import re
import sys
from collections import OrderedDict
from typing import List, Mapping, Tuple

import numpy
import pandas
from pandas import Timestamp

# Define pandas dict of sheets type. This is what's returned from read_excel()
PandasDict = Mapping[str, pandas.DataFrame]


def as_snake_case(text: str) -> str:
    """
    Converts CamelCase to snake_case.

    As a special case, this function converts `ID` to `_id` instead of `_i_d`.
    """
    output = ""
    for i, char in enumerate(text):
        if char.isupper() and i != 0:
            # preserve _id
            if not (char == 'D' and text[i-1] == 'I'):
                output += "_"
        output += char.lower()
    return output


def order_tables(tables: list, references: List[Tuple[str, str]]) -> list:
    """
    Orders the `tables` list so that no table is before a table it references,
    according to the `references` dict (using  Kahn's algorithm).
    """
    if not references:
        return tables

    # copy references into a list of edges
    edges = list(references)

    # make sets of origin and target nodes
    origin_nodes = {o for o, t in edges}
    target_nodes = {t for o, t in edges}

    # figure out isolated nodes
    isolated = set(tables).difference(origin_nodes, target_nodes)

    # figure out all start-only nodes
    start_nodes = {o for o, t in edges}.difference({t for o, t in edges})
    if not start_nodes:
        raise ValueError("Cyclic references")

    sorted_tables = []
    while start_nodes:
        # add start node to sorted list
        start = start_nodes.pop()
        sorted_tables += [start]
        to_remove = []

        # remove all edges from start node
        for i, edge in enumerate(edges):
            if edge[0] == start:
                to_remove += [i]
        targets = []
        for i in sorted(to_remove, reverse=True):
            edge = edges.pop(i)
            targets += [edge[1]]

        # ... and add all nodes without incoming edges to start_nodes
        for target in targets:
            for edge in edges:
                if edge[1] == target:
                    break
            else:
                start_nodes.add(target)

    if edges:
        raise ValueError("Cyclic references")

    # add isolated tables at the end
    sorted_tables += list(isolated)

    # and finally, reverse the list, so that referenced tables are inserted
    # before the references are needed
    return sorted_tables[::-1]


class DBMapper():
    """
    Reads a JSON mapping file, and can then be used to convert data in
    pandas.DataFrame format to database insert queries.
    """

    def __init__(self, filename):
        """
        Reads a JSON mapping file.
        """
        logging.info("Reading data mapping file")
        with open(filename) as mapping_file:
            self.mapping = json.load(mapping_file)

    @staticmethod
    def _format_value(value):
        """
        Formats `value` in a manner suitable for postgres insert queries.
        """
        if isinstance(value, (str, Timestamp)):
            return f"'{value}'"
        if value is None:
            return 'NULL'
        if numpy.isnan(value):
            return "'NaN'"
        return value

    def _function_value(self, data: pandas.DataFrame, ref: dict):
        """
        Returns a value accoring to the function defined in ref['function'],
        using the values in `data`.
        """
        function = ref.get('function', None)
        if not function:
            logging.warning("No function available for function value")
            return None

        if function['operation'] == 'concat':
            sep = function['separator']
            values = []
            for field in function['targets']:
                value = data[field].values[0]
                if not isinstance(value, str):
                    # we specifically want to replace NaN values with empty
                    # strings here.
                    if numpy.isnan(value):
                        value = ""
                    else:
                        value = str(value)
                values += [value]
            return sep.join(values)
        else:
            logging.error('Unknown function: %s', function['operation'])
        return None

    @property
    def sheets(self):
        """
        Returns the sheet names from the currently loaded mapping file.
        """
        return list(self.mapping.keys())

    def as_query(self, table: str, data: pandas.DataFrame,
                 start: int = 0, count: int = 0):
        """
        Formats an SQL insert query using the given table name and data frame,
        as well as data from the loaded data mapping file.
        """
        # sometimes there are columns that need to be ignored in the data,
        # so we get the column names from the mapping.
        fields = self.get_fields(table)
        quoted_fields = ', '.join([f'"{c[0]}"' for c in fields])

        # define what counts as missing values (for using default).
        missing = [None, numpy.nan]

        # format values, so that strings are quoted
        values = []
        stop = start
        stop += count if count > 0 else len(data.values)
        stop = min(len(data.values), stop)
        for i in range(start, stop):
            formatted_row = []
            for field, ref in fields:
                has_default = "default" in self.mapping[table][ref]
                try:
                    if "function" in self.mapping[table][ref]:
                        value = self._function_value(data[i:i+1],
                                                     self.mapping[table][ref])
                    else:
                        value = data[field][i]
                    if has_default and value in missing:
                        raise KeyError
                except KeyError:
                    if has_default:
                        value = self.mapping[table][ref]["default"]
                    else:
                        logging.error("Could not insert %s values", table)
                        logging.error("Missing %s value on line '%s'",
                                      field, i)
                        sys.exit(1)
                formatted_row.append(self._format_value(value))
            values += [f'({", ".join(map(str, formatted_row))})']

        values = ', '.join(values)
        query = f"INSERT INTO {table} ({quoted_fields}) VALUES {values}"
        mapping = [m for t, m in self.mapping.items()
                   if m['targetTable'] == table]
        if mapping and self.is_returning(table):
            query += f" RETURNING {mapping[0]['returning']}"

        return query + ";"

    def is_returning(self, table):
        """
        Returns `True` is the given table has a 'returning' key in the mapping,
        and that key has a value. Return `False` otherwise.
        """
        if table not in self.mapping:
            return False

        returning = self.mapping[table].get('returning', None)
        return bool(returning)

    def get_fields(self, sheet):
        """
        Returns all target fields for `sheet` from the current mapping.
        """
        mapping = self.mapping.get(sheet, None)
        if not mapping:
            return None
        fields = []
        for field in mapping:
            target = self.target_field(sheet, field)
            if not target:
                continue
            fields += [(target, field)]
        return fields

    def target_field(self, sheet, field):
        """
        Returns the target field name for the given `field` in `sheet`.
        """
        mapping = self.mapping.get(sheet, None)
        if not mapping or field in ['targetTable', 'returning']:
            return None
        info = mapping[field]
        target_field = info.get('field', None)
        if not target_field:
            target_field = as_snake_case(field)
        return target_field

    def update_references(self, table, data):
        """
        Updates all the references in `table` with values from `data`.
        """

        if table not in self.mapping:
            return
        mapping = self.mapping[table]
        logging.debug("updating table references for %s", table)
        for field, settings in mapping.items():
            if 'references' in settings:
                ref = settings['references']

                target = data[ref['table']].set_index(ref['join']['to'])
                joined = data[table].join(target, lsuffix="_joined",
                                          on=ref['join']['from'])
                if 'field' in ref:
                    data[table][field] = joined[ref['field']]
                elif 'function' in ref:
                    values = []
                    for i in range(len(data[table].values)):
                        values += [self._function_value(joined[i:i+1], ref)]
                    data[table][field] = values

    def validate(self, table: str, data: pandas.DataFrame) -> bool:
        """
        Runs any validation defined for `table` in `self.mapping` on `data`.

        Returns `True` if all values validated, or no validation was defined,
        `False` otherwise.
        """
        # If input includes sheet/table that does not match mapping
        if table not in self.mapping:
            logging.warning('unknown table %s in validation', table)
            return True

        valid = True
        # Iterate over mapping fields
        for field, settings in self.mapping[table].items():
            previous_mistake = False
            if 'validation' in settings:
                validator = re.compile(settings['validation'])
                data_field = self.target_field(table, field)
                for value in data[data_field]:
                    if not validator.fullmatch(str(value)):
                        valid = False
                        if not previous_mistake:
                            logging.warning(" - malformed value for %s",
                                            data_field)
                            logging.warning(' - validator: "%s"',
                                            settings['validation'])
                            previous_mistake = True
                        logging.warning("offending value: %s", value)
        return valid

    def reorder_data(self, data: PandasDict) -> PandasDict:
        """
        Takes a pandas sheet dictionary and reorders the data according to the
        loaded DB mapping file. This modifies the original data instead of a
        copy in order to save on memory for large files.
        """
        # go through all the tables and rename fields to the target name. Since
        # we want to modify the sheet names, we make a static copy to loop
        # through.
        sheets = list(data.keys())
        references = []
        for sheet in sheets:
            if sheet not in self.mapping:
                logging.warning("Unknown sheet '%s' ignored", sheet)
                continue

            # Rename data sheet to target table name
            table = self.mapping[sheet]['targetTable']
            data[table] = data.pop(sheet)

            # Extract data-db field map and (fkey) reference dicts from mapping
            field_mapping = {}
            for field, info in self.mapping[sheet].items():
                target_field = self.target_field(sheet, field)
                # Ignore 'non-field' keys (i.e. 'targetTable', 'returning')
                if not target_field:
                    continue
                field_mapping[field] = target_field
                # Keep track of references for table ordering
                ref = info.get('references', None)
                if ref:
                    references += [(table, ref['table'])]

            # Rename data fields
            data[table].rename(columns=field_mapping, inplace=True)

            # Drop empty rows and columns, if any
            data[table] = data[table].dropna(how='all')
            data[table] = data[table].drop(data[table].filter(regex="Unnamed"),
                                           axis='columns')

        # Reorder tables so that no table precedes a table it references
        ordered_tables = OrderedDict()
        for table in order_tables(list(data.keys()), references):
            ordered_tables[table] = data[table]

        # Also update mapping itself, now that input uses target table names,
        # as it will be used later
        sheet_mapping = []
        for sheet, mapping in self.mapping.items():
            sheet_mapping += [(sheet, self.mapping[sheet]['targetTable'])]

        for sheet, table in sheet_mapping:
            # Renamed sheets, e.g. asv-table
            if sheet != table:
                mapping = self.mapping[sheet]
                del self.mapping[sheet]
                self.mapping[table] = mapping

        return ordered_tables
