MolMod Data Importer
====================

The mol-mod data importer takes a stream of excel-data and loads it into the
database according to the mapping given in `data-mapping.json`. The mapping file
has the following syntax:
```
  {
    <excel-sheet>: {
      <column>: {
        [field: <database-field>]
      },
      targetTable: <string>,
      [returning: <string>]
    }
  }
```

If the returning field is present, the insert queries will be instructed to
fetch the given field(s). These will then be added to the loaded data and be
available for joins.

For brevity, `field` can be removed from the column description, and then the
snake case representation of the column will be used.

ex.
```
  {
    "event": {
      "eventDate": {
        "field": "event_date"
      },
      "samplingProcotol": {
        "field": "sampling_protocol"
      },
      "targetTable": "sampling_event"
    }
  }
```
can be written as:
```
  {
    "event": {
      "eventDate": {},
      "samplingProcotol": {},
      "targetTable": "sampling_event"
  }
```
