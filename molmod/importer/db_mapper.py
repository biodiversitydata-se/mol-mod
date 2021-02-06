#!/usr/bin/env python3
"""
The DBMapper class takes a dictionary of pandas data frames and a json mapping
file, and uses these to generate sql insert queries.
"""

import json
import logging

from typing import Mapping

import pandas

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
        self.mapping = json.load(open(filename))

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
        quoted_fields = ', '.join([f'"{c}"' for c in data.columns])

        # format values, so that strings are quoted
        values = []
        for row in data.values:
            formatted_row = []
            for value in row:
                if isinstance(value, str):
                    formatted_row += [f"'{value}'"]
                else:
                    formatted_row += [value]
            values += [f'({", ".join(map(str, formatted_row))})']

        values = ', '.join(values)
        query = f"INSERT INTO {table} ({quoted_fields}) VALUES {values}"
        mapping = [m for t,m in self.mapping.items() \
                             if m['targetTable'] == table]
        if mapping and mapping[0]['returning']:
            query += f" RETURNING {mapping[0]['returning']}"

        return query + ";"

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
                # ignore the "targetTable" and "returning" fields
                if field in ['targetTable', 'returning']:
                    continue
                target_field = info.get('field', None)
                if not target_field:
                    target_field = as_snake_case(field)
                field_mapping[field] = target_field
                # keep track of references for table ordering
                if info.get('references', None):
                    references += [(table, info.get('references'))]

            # then rename all the fields
            data[table].rename(columns=field_mapping, inplace=True)

            # sometimes pandas reads a lot of empty lines, so we filter all rows
            # that are NaN only
            data[table] = data[table].dropna(how='all')
            # ... and some empty columns too ...
            data[table] = data[table].dropna(axis='columns', how='all')

        return data
