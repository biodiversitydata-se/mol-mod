MolMod Data Importer
====================

The mol-mod data importer takes a stream of excel-data and loads it into the
database according to the mapping given in 'data-mapping.json'. The mapping file
has the following syntax:
'''
  {
    <excel-sheet>: {
      <column>: {
        [field: <database-field>],
        [default: <any value>]
      },
      targetTable: <string>
    }
  }
'''

For brevity, 'field' can be removed from the column description, and then the
snake case representation of the column will be used. Where a column might be
missing from the input data, or a column may have empty fields, a 'default'
value can be set.
