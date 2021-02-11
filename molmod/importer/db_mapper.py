#!/usr/bin/env python3
"""
The DBMapper class takes a dictionary of pandas data frames and a json mapping
file, and uses these to generate sql insert queries.
"""

import sys
import json
import math
import logging

from collections import OrderedDict
from typing import List, Mapping, Tuple

import pandas
from pandas import Timestamp

# Define pandas dict of sheets type. This is what's returned from read_excel()
PandasDict = Mapping[str, pandas.DataFrame]


def as_snake_case(text: str) -> str:
    """
    Converts CamelCase to snake_case.
    """
    output = ""
    for i, char in enumerate(text):
        if char.isupper() and i != 0:
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
    origin_nodes = {o for o,t in edges}
    target_nodes = {t for o,t in edges}

    # figure out isolated nodes
    isolated = set(tables).difference(origin_nodes, target_nodes)

    # figure out all start-only nodes
    start_nodes = {o for o,t in edges}.difference({t for o,t in edges})
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
        Formats `value` in a manner that's suitable for postgres insert queries.
        """
        if isinstance(value, (str, Timestamp)):
            return f"'{value}'"
        if value is None:
            return 'NULL'
        if math.isnan(value):
            return "'NaN'"
        return value

    @property
    def sheets(self):
        """
        Returns the sheet names from the currently loaded mapping file.
        """
        return list(self.mapping.keys())

    def as_query(self, table: str, data: pandas.DataFrame):
        """
        Formats an SQL insert query using the given table name and data frame,
        as well as data from the loaded data mapping file.
        """
        # sometimes there are columns that need to be ignored in the data, so we
        # get the column names from the mapping.
        fields = self.get_fields(table)
        quoted_fields = ', '.join([f'"{c}"' for c in fields])

        # format values, so that strings are quoted
        values = []
        for i in range(len(data.values)):
            formatted_row = []
            for field in fields:
                try:
                    value = data[field][i]
                except KeyError:
                    if "default" in self.mapping[table][field]:
                        value = self.mapping[table][field]["default"]
                    else:
                        logging.error("Could not insert %s values", table)
                        logging.error("Missing %s value on line '%s'", field, i)
                        sys.exit(1)
                formatted_row.append(self._format_value(value))
            values += [f'({", ".join(map(str, formatted_row))})']

        values = ', '.join(values)
        query = f"INSERT INTO {table} ({quoted_fields}) VALUES {values}"
        mapping = [m for t,m in self.mapping.items() \
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
            fields += [target]
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
                data[table][field] = joined[ref['field']]

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

            # rename the sheet to the target table names
            table = self.mapping[sheet]['targetTable']
            data[table] = data.pop(sheet)


            # figure out a mapping from the current fields to the new fields
            field_mapping = {}
            # parse field data into field names and validators
            for field, info in self.mapping[sheet].items():
                target_field = self.target_field(sheet, field)
                if not target_field:
                    continue
                field_mapping[field] = target_field
                # keep track of references for table ordering
                ref = info.get('references', None)
                if ref:
                    references += [(table, ref['table'])]

            # then rename all the fields
            data[table].rename(columns=field_mapping, inplace=True)

            # sometimes pandas reads a lot of empty lines, so we filter all rows
            # that are NaN only
            data[table] = data[table].dropna(how='all')
            # ... and some empty columns too ...
            data[table] = data[table].drop(data[table].filter(regex="Unnamed"),
                                           axis='columns')

        # parse all references to figure out insertion order, and make sure that
        # there are no reference loops
        ordered_tables = OrderedDict()
        for table in order_tables(list(data.keys()), references):
            ordered_tables[table] = data[table]

        # also update the mapping, now that we use target tables instead of
        # source sheets
        sheet_mapping = []
        for sheet, mapping in self.mapping.items():
            sheet_mapping += [(sheet, self.mapping[sheet]['targetTable'])]

        for sheet, table in sheet_mapping:
            if sheet != table:
                mapping = self.mapping[sheet]
                del self.mapping[sheet]
                self.mapping[table] = mapping

        return ordered_tables
