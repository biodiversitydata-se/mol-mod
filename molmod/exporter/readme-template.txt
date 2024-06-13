
SUMMARY

This folder contains restructured and condensed data from Darwin Core (DwC) datasets already published in the Swedish Biodiversity Data Infrastructure (SBDI; https://biodiversitydata.se) and the Global Biodiversity Information Facility (GBIF; https://www.gbif.org/), through the Swedish ASV portal (https://asv-portal.biodiversitydata.se) and the GBIF-Sweden Integrated Publishing Toolkit (IPT; https://www.gbif.se/ipt/).


DATASET METADATA

[API data]

Please see the included eml.xml file for full metadata, and attribute the original authors when using this dataset.


BACKGROUND

Current recommendations for publishing DNA-derived data in biodiversity data platforms (https://docs.gbif-uat.org/publishing-dna-derived-data/en/#data-packaging-and-mapping) suggest using a (DwC) occurrence core structure. However, for datasets with many occurrences and/or contextual metadata parameters, this approach leads to prohibitively large DwC archives. To address this, we restructure and provide more compact versions of these DwC archives to facilitate download and subsequent analysis of ASV datasets.


RESTRUCTURING OF DATASETS

The restructured datasets in this publication retain the same data fields as the original DwC archives (with a few exceptions mentioned below). However, they are organized around sampling events instead of occurrences. Individual archives consist of the following files:

event.tsv: Basic event information (who, when, where), plus event-level fields from the DNA-derived data extension.
emof.tsv: Event-level contextual metadata parameters, if supplied.
occurrence.tsv: IDs and counts of observed ASVs for each event (sample).
asv.tsv: Taxonomy and sequences of observed ASVs.
eml.xml: Dataset-level metadata, copied unchanged from the original IPT resource.

Rows in event.tsv, emof.tsv, and occurrence.tsv are linked via shared 'eventID' fields, while occurrence.tsv and asv.tsv are linked via 'taxonID'.

Some fields have been excluded or split up to reduce file size: All ASV datasets share 'basisOfRecord' = 'materialSample', and 'organismQuantityType' = 'DNA sequence reads', so these fields have been omitted. We also exclude 'datasetID' as this is also part of the composite 'eventID', which is included as the central key in these restructured datasets. Instead of including the full, composite 'occurrenceID' in occurrence.tsv, we report 'eventID' plus 'taxonID' there. Note that 'occurrenceID' can easily be recreated by combining 'eventID' with 'asv_id_alias' from asv.tsv, via shared field 'taxonID', if needed.

Finally, restructured datasets will always include data on 'kingdom' and 'phylum' when assigned. Currently, these fields are not mapped in the IPT for 18S rRNA data because the higher taxonomy in PR2 differs significantly from the GBIF taxonomy backbone, disrupting name-matching during import to GBIF/Bioatlas platforms.

The SBDI Molecular Data Team
Contact form: https://docs.biodiversitydata.se/support/
