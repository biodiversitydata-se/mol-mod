
\set data_schema `echo ${DATA_SCHEMA:-public}`

--
-- api schema tables
--

CREATE SCHEMA api;

--
-- Darwin Core (dwc) output views which are only accessed by the 'IPT' user when
-- datasets are published to Bioatlas/GBIF via https://www.gbif.se/ipt/
--

CREATE OR REPLACE VIEW api.dwc_oc_emof AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    (ds.dataset_id || ':' || se.event_id)  AS "eventID",
    (ds.dataset_id || ':' || se.event_id || ':' || oc.asv_id_alias) AS "occurrenceID",
    (ds.dataset_id || ':' || se.event_id || ':' || emof.measurement_type) AS "measurementID",
    emof.measurement_type AS "measurementType",
    emof.measurement_type_id AS "measurementTypeID",
    emof.measurement_unit AS "measurementUnit",
    emof.measurement_unit_id AS "measurementUnitID",
    emof.measurement_value AS "measurementValue",
    emof.measurement_value_id AS "measurementValueID",
    emof.measurement_accuracy AS "measurementAccuracy",
    emof.measurement_determined_date AS "measurementDeterminedDate",
    emof.measurement_determined_by AS "measurementDeterminedBy",
    emof.measurement_method AS "measurementMethod",
    emof.measurement_remarks AS "measurementRemarks"
FROM :data_schema.emof
    JOIN :data_schema.sampling_event se ON emof.event_pid = se.pid
    JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
    JOIN :data_schema.taxon_annotation ta ON ta.asv_pid = oc.asv_pid
    JOIN :data_schema.mixs ON mixs.pid = oc.event_pid
    JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = TRUE
    AND ta.annotation_target::text = mixs.target_gene::text;

CREATE OR REPLACE VIEW api.dwc_oc_mixs AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    (ds.dataset_id || ':' || se.event_id)  AS "eventID",
    (ds.dataset_id || ':' || se.event_id || ':' || oc.asv_id_alias) AS "occurrenceID",
    asv.asv_id AS "taxonID",
    mixs.sop,
    mixs.pcr_primer_name_forward,
    mixs.pcr_primer_name_reverse,
    mixs.pcr_primer_forward,
    mixs.pcr_primer_reverse,
    mixs.target_gene,
    mixs.target_subfragment,
    mixs.lib_layout,
    mixs.seq_meth,
    mixs.denoising_appr,
    asv.asv_sequence AS "DNA_sequence",
    mixs.env_broad_scale,
    mixs.env_local_scale,
    mixs.env_medium
FROM :data_schema.mixs
    JOIN :data_schema.sampling_event se ON mixs.pid = se.pid
    JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
    JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
    JOIN :data_schema.asv ON asv.pid = oc.asv_pid
    JOIN :data_schema.taxon_annotation ta ON ta.asv_pid = oc.asv_pid
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = TRUE
    AND ta.annotation_target::text = mixs.target_gene::text;

CREATE OR REPLACE VIEW api.dwc_oc_occurrence AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    ds.dataset_name AS "datasetName",
    (ds.dataset_id || ':' || se.event_id)  AS "eventID",
    (ds.dataset_id || ':' || se.event_id || ':' || oc.asv_id_alias) AS "occurrenceID",
    'MaterialSample'::text AS "basisOfRecord",
    se.event_date AS "eventDate",
    se.location_id AS "locationID",
    se.verbatim_locality AS "verbatimLocality",
    se.municipality,
    se.country,
    se.minimum_elevation_in_meters AS "minimumElevationInMeters",
    se.maximum_elevation_in_meters AS "maximumElevationInMeters",
    se.minimum_depth_in_meters AS "minimumDepthInMeters",
    se.maximum_depth_in_meters AS "maximumDepthInMeters",
    se.decimal_latitude AS "decimalLatitude",
    se.decimal_longitude AS "decimalLongitude",
    se.geodetic_datum AS "geodeticDatum",
    se.coordinate_uncertainty_in_meters AS "coordinateUncertaintyInMeters",
    se.data_generalizations AS "dataGeneralizations",
    concat_ws(' | ', se.associated_sequences, oc.associated_sequences) AS "associatedSequences",
    se.recorded_by AS "recordedBy",
    se.material_sample_id AS "materialSampleID",
    se.institution_code AS "institutionCode",
    se.institution_id AS "institutionID",
    se.collection_code AS "collectionCode",
    se.field_number AS "fieldNumber",
    se.catalog_number AS "catalogNumber",
    se.references_ AS "references",
    calc.size AS "sampleSizeValue",
    'DNA sequence reads'::text AS "sampleSizeUnit",
    se.sampling_protocol AS "samplingProtocol",
    'DNA sequence reads'::text AS "organismQuantityType",
    oc.organism_quantity AS "organismQuantity",
    asv.asv_id AS "taxonID",
    ta.scientific_name AS "scientificName",
    ta.taxon_rank AS "taxonRank",
    ta.kingdom,
    ta.phylum,
    ta.oorder AS "order",
    ta.class,
    ta.family,
    ta.genus,
    ta.specific_epithet AS specificepithet,
    ta.infraspecific_epithet AS infraspecificepithet,
    ta.otu,
    ta.taxon_remarks AS "taxonRemarks",
    ta.date_identified AS "dateIdentified",
    ta.identification_references AS "identificationReferences",
    concat_ws(' '::text, ta.annotation_algorithm, 'annotation against', ta.reference_db::text || ';'::text, 'confidence at lowest specified (ASV portal) taxon:', ta.annotation_confidence) AS "identificationRemarks",
    (('By data provider: '::text || oc.previous_identifications::text) || '; By ASV portal: '::text) || concat_ws('|'::text, ta.kingdom, ta.phylum, ta.oorder, ta.class, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS "previousIdentifications",
    '' AS "dynamicProperties"
FROM :data_schema.sampling_event se
    JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
    JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
    JOIN :data_schema.asv ON asv.pid = oc.asv_pid
    JOIN :data_schema.mixs ON mixs.pid = se.pid
    JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
    JOIN (SELECT sum(oc.organism_quantity) as size, se.pid
        FROM sampling_event se
            JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
            JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
            JOIN :data_schema.asv ON asv.pid = oc.asv_pid
            JOIN :data_schema.mixs ON mixs.pid = se.pid
            JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
        WHERE ta.target_prediction = TRUE AND ta.annotation_target::text = mixs.target_gene::text
        GROUP BY se.pid) calc ON se.pid = calc.pid
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = TRUE
    AND ta.annotation_target::text = mixs.target_gene::text;

--
-- Objects used in FILTER page
-- Views are materialized to increase search performance, and need to updated after
-- data import / db restore (see 'make status' / 'make stats' in Makefile)
--

-- View for data displayed in the FILTER search result table,
-- also used by view for FILTER dropdown options (below)
CREATE MATERIALIZED VIEW api.app_search_mixs_tax AS
SELECT DISTINCT asv.asv_id,
    concat_ws('|'::text, concat_ws(''::text, asv.asv_id, '-', ta.kingdom), ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS asv_tax,
    asv.asv_sequence,
    mixs.target_gene AS gene,
    mixs.target_subfragment AS sub,
    (mixs.pcr_primer_name_forward)::text AS fw_name,
    (mixs.pcr_primer_forward)::text AS fw_sequence,
    (mixs.pcr_primer_name_reverse)::text AS rv_name,
    (mixs.pcr_primer_reverse)::text AS rv_sequence,
    (((mixs.pcr_primer_name_forward)::text || ': '::text) || (mixs.pcr_primer_forward)::text) AS fw_prim,
    (((mixs.pcr_primer_name_reverse)::text || ': '::text) || (mixs.pcr_primer_reverse)::text) AS rv_prim,
    ta.kingdom,
    ta.phylum,
    ta.class AS classs,
    ta.oorder,
    ta.family,
    ta.genus,
    ta.specific_epithet AS species
FROM :data_schema.mixs
    JOIN :data_schema.occurrence oc ON oc.event_pid = mixs.pid
    JOIN :data_schema.asv ON asv.pid = oc.asv_pid
    JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
    JOIN :data_schema.sampling_event se ON oc.event_pid = se.pid
    JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
WHERE ds.in_bioatlas
    AND ta.status::text = 'valid'::text
    AND ta.target_prediction = TRUE
    AND ta.annotation_target = mixs.target_gene
ORDER BY asv.asv_id, asv.asv_sequence, mixs.target_gene, mixs.target_subfragment, (((mixs.pcr_primer_name_forward)::text || ': '::text) || (mixs.pcr_primer_forward)::text), (((mixs.pcr_primer_name_reverse)::text || ': '::text) || (mixs.pcr_primer_reverse)::text);

-- View for FILTER dropdown options (dynamically filtered in function, below)
CREATE MATERIALIZED VIEW api.app_filter_mixs_tax AS
SELECT DISTINCT gene, sub,
    fw_name || ': ' || fw_sequence AS fw_prim,
	rv_name || ': ' || rv_sequence AS rv_prim,
    kingdom,
    phylum,
    classs,
    oorder,
    family,
    genus,
    species
FROM api.app_search_mixs_tax;

-- Function executed as the user clicks a FILTER dropdown, getting data from
-- a materialized view (above), and dynamically modifying the query based on
-- 1) which dropdown sent the request,
-- 2) what the user typed in the dropdown, if anything, and
-- 3) which selections have previously been made in other dropdowns, if any
CREATE OR REPLACE FUNCTION api.app_drop_options(
    field text,
    noffset bigint,
    nlimit integer,
    term text DEFAULT '',
    kingdom text[] DEFAULT '{}',
    phylum text[] DEFAULT '{}',
    classs text[] DEFAULT '{}',
    oorder text[] DEFAULT '{}',
    family text[] DEFAULT '{}',
    genus text[] DEFAULT '{}',
    species text[] DEFAULT '{}',
    gene text[] DEFAULT '{}',
    sub text[] DEFAULT '{}',
    fw_prim text[] DEFAULT '{}',
    rv_prim text[] DEFAULT '{}')
RETURNS TABLE(data json)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Execute dynamically, i.e. modify the query based on 1) which dropdown sent
    -- the request, 2) what the user typed, if anything, and 3) which
    -- selections have previously been made in other dropdowns, if any
    RETURN QUERY EXECUTE format(
        '-- Put filtered options in temp table
		WITH filtered AS (
		 	SELECT DISTINCT %I AS id
         	FROM api.app_filter_mixs_tax
         	WHERE %I <> '''' AND %I IS NOT NULL
         	AND ($1 = ''{}'' OR kingdom = ANY($1))
         	AND ($2 = ''{}'' OR phylum = ANY($2))
         	AND ($3 = ''{}'' OR classs = ANY($3))
         	AND ($4 = ''{}'' OR oorder = ANY($4))
         	AND ($5 = ''{}'' OR family = ANY($5))
         	AND ($6 = ''{}'' OR genus = ANY($6))
         	AND ($7 = ''{}'' OR species = ANY($7))
            -- Make case-insensitive comparison with user-provided term
         	AND %I ~* $8
         	AND ($9 = ''{}'' OR gene = ANY($9))
         	AND ($10 = ''{}'' OR sub = ANY($10))
         	AND ($11 = ''{}'' OR fw_prim = ANY($11))
         	AND ($12 = ''{}'' OR rv_prim = ANY($12))
         	ORDER BY %I
         	OFFSET $13
         	LIMIT $14)
		-- Format & paginate according to select2 requirements
		SELECT json_build_object(
            ''count'', (SELECT COUNT(*) FROM filtered),
            ''results'', COALESCE(json_agg(json_build_object(''id'', f.id, ''text'', f.id)),''[]'')
		-- Format dynamic field NAME
		) FROM filtered f', field, field, field, field, field, field)
	-- Set dynamic field VALUES
    USING kingdom, phylum, classs, oorder, family, genus, species, '^'||term||'.*$',
	gene, sub, fw_prim, rv_prim, noffset, nlimit;
END;
$$;
COMMENT ON FUNCTION api.app_drop_options(text, bigint, integer, text, text[], text[], text[], text[], text[], text[], text[], text[], text[], text[], text[])
    IS 'Example call 1 (view in Properties | General to get quotes right):
SELECT api.app_drop_options(''classs'', 0, 25, ''T'', ''{}'', ''{Actinobacteriota, Bacteroidota}'');

Example call 2 (view in Properties | General to get quotes right):
-- Payload sent to /rpc/app_drop_options: {"kingdom": ["Bacteria"], "phylum": ["Planctomycetes"], "field": "classs", "term": "", "nlimit": 25, "noffset": 0}
SELECT api.app_drop_options(''classs'', 0, 25, '''', ''{Bacteria}'',''{Planctomycetes}'');
';


--
-- Objects used in BLAST page
--

-- View used by A) portal admin to produce a fasta file for building a BLAST db,
-- and also B) by webb app to retrieve subject sequences to add to BLAST result
-- tables, as these are not included in normal BLAST output. View output is then
-- filtered via a POST request to the below function, because:
-- 1) we may need to send more ASV IDs than we can fit into an URL to filter a GET request, and
-- 2) PostgREST does not allow POST requests for SELECT operations on views
-- Materialized (see above), and updated with 'make blastdb'
CREATE MATERIALIZED VIEW IF NOT EXISTS api.app_asvs_for_blastdb AS
SELECT DISTINCT asv_id, higher_taxonomy, asv_sequence
    FROM (SELECT asv.asv_id,
            concat_ws(';'::text, ta.kingdom, ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS higher_taxonomy,
            asv.asv_sequence
        FROM :data_schema.asv
            JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
            JOIN :data_schema.occurrence oc ON oc.asv_pid = asv.pid
            JOIN :data_schema.sampling_event se ON oc.event_pid = se.pid
            JOIN :data_schema.mixs ON se.pid = mixs.pid
            JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
        WHERE ds.in_bioatlas
            AND ta.annotation_target::text = mixs.target_gene::text
            AND ta.status::text = 'valid'::text AND ta.target_prediction = TRUE) rd;
CREATE INDEX IF NOT EXISTS blast_asv ON api.app_asvs_for_blastdb(asv_id);

CREATE FUNCTION api.app_seq_from_id(ids character varying[])
    RETURNS TABLE(asv_id CHARACTER(36), ASV_SEQUENCE CHARACTER VARYING)
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT asv_id, asv_sequence FROM api.app_asvs_for_blastdb
    WHERE asv_id = ANY(ids)
$$;
COMMENT ON FUNCTION api.app_seq_from_id(character varying[])
    IS 'Example call (view in Properties | General to get quotes right):
SELECT api.app_seq_from_id(''{ASV:40b37890b1b1fcdf0ece91f1da34c1ca}'')';

-- View used for populating stats table in About page
-- Materialized (see above), and updated with 'make status' / 'make stats'
CREATE MATERIALIZED VIEW api.app_about_stats AS
SELECT sub.gene,
   string_agg(DISTINCT sub.kingdom::text, ', '::text) AS kingdoms,
   count(DISTINCT sub.dataset) AS datasets,
   count(DISTINCT CASE WHEN sub.phylum <> '' then sub.phylum end) AS phyla,
   count(DISTINCT CASE WHEN sub.classs <> '' then sub.classs end) AS classes,
   count(DISTINCT CASE WHEN sub.oorder <> '' then sub.oorder end)AS orders,
   count(DISTINCT CASE WHEN sub.family <> '' then sub.family end) AS families,
   count(DISTINCT CASE WHEN sub.genus <> '' then sub.genus end) AS genera,
   count(DISTINCT CASE WHEN sub.species <> '' then sub.species end) AS species,
   count(DISTINCT sub.asv_id) AS asvs
  FROM ( SELECT ds.pid as dataset,
           asv.asv_id,
           mixs.target_gene AS gene,
           ta.kingdom,
           ta.phylum,
           ta.class AS classs,
           ta.oorder,
           ta.family,
           ta.genus,
           ta.genus::text || ta.specific_epithet::text AS species
          FROM mixs
            JOIN :data_schema.occurrence oc ON oc.event_pid = mixs.pid
            JOIN :data_schema.asv ON asv.pid = oc.asv_pid
            JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
            JOIN :data_schema.sampling_event se ON oc.event_pid = se.pid
            JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
            WHERE ds.in_bioatlas and ta.status::text = 'valid'::text
               AND ta.target_prediction = TRUE
               AND ta.annotation_target = mixs.target_gene) sub
 GROUP BY sub.gene
 ORDER BY sub.gene
WITH DATA;

-- View used for populating dataset table in Download data page
-- Materialized (see above), and updated with 'make status' / 'make stats'
CREATE MATERIALIZED VIEW IF NOT EXISTS api.app_dataset_list
TABLESPACE pg_default
AS
 SELECT DISTINCT ds.dataset_id,
    ds.dataset_name,
    ds.ipt_resource_id,
    mixs.target_gene,
    mixs.target_subfragment,
    mixs.pcr_primer_name_forward,
    mixs.pcr_primer_name_reverse,
    se.institution_code
   FROM dataset ds,
    sampling_event se,
    mixs
  WHERE ds.in_bioatlas = true AND ds.pid = se.dataset_pid AND se.pid = mixs.pid
  ORDER BY mixs.target_gene, ds.dataset_name
WITH DATA;


--
-- 'Utility' views used by admin
--

-- View listing reference database and algorithm used for annotaton of each dataset
CREATE OR REPLACE VIEW api.annotation_overview
AS
SELECT DISTINCT ds.pid, ds.ipt_resource_id, dataset_id, in_bioatlas,
annotation_target, split_part(reference_db, ' (', 1) AS db,
split_part(annotation_algorithm, ' (', 1) AS algo
FROM dataset ds, sampling_event se, occurrence oc, taxon_annotation ta
WHERE ds.pid = se.dataset_pid
AND se.pid = oc.event_pid
AND oc.asv_pid = ta.asv_pid
AND ta.status = 'valid'
ORDER BY annotation_target, dataset_id;

CREATE OR REPLACE VIEW api.split_annotation_ds
AS
SELECT DISTINCT pid, dataset_id, db, algo
FROM api.annotation_overview
WHERE dataset_id IN (
    SELECT dataset_id
    FROM api.annotation_overview
    GROUP BY dataset_id
    HAVING COUNT(DISTINCT db) > 1 OR COUNT(DISTINCT algo) > 1
);


--
-- Views for generating event-core-like dataset files,
-- intended for download (after some processing)
--

CREATE OR REPLACE VIEW api.dl_event
AS
SELECT se.dataset_pid,
    ds.ipt_resource_id,
    (ds.dataset_id::text || ':'::text) || se.event_id::text AS "eventID",
    ds.dataset_name AS "datasetName",
    se.event_date AS "eventDate",
    se.location_id AS "locationID",
    se.verbatim_locality AS "verbatimLocality",
    se.municipality,
    se.country,
    se.minimum_elevation_in_meters AS "minimumElevationInMeters",
    se.maximum_elevation_in_meters AS "maximumElevationInMeters",
    se.minimum_depth_in_meters AS "minimumDepthInMeters",
    se.maximum_depth_in_meters AS "maximumDepthInMeters",
    se.decimal_latitude AS "decimalLatitude",
    se.decimal_longitude AS "decimalLongitude",
    se.geodetic_datum AS "geodeticDatum",
    se.coordinate_uncertainty_in_meters AS "coordinateUncertaintyInMeters",
    se.data_generalizations AS "dataGeneralizations",
    se.associated_sequences AS "associatedSequences",
    se.recorded_by AS "recordedBy",
    se.material_sample_id AS "materialSampleID",
    se.institution_code AS "institutionCode",
    se.institution_id AS "institutionID",
    se.collection_code AS "collectionCode",
    se.field_number AS "fieldNumber",
    se.catalog_number AS "catalogNumber",
    se.references_ AS "references",
    calc.size AS "sampleSizeValue",
    'DNA sequence reads'::text AS "sampleSizeUnit",
    se.sampling_protocol AS "samplingProtocol",
    mixs.sop,
    mixs.pcr_primer_name_forward,
    mixs.pcr_primer_name_reverse,
    mixs.pcr_primer_forward,
    mixs.pcr_primer_reverse,
    mixs.target_gene,
    mixs.target_subfragment,
    mixs.lib_layout,
    mixs.seq_meth,
    mixs.denoising_appr,
    mixs.env_broad_scale,
    mixs.env_local_scale,
    mixs.env_medium
    FROM sampling_event se
        JOIN dataset ds ON se.dataset_pid = ds.pid
        JOIN mixs ON se.pid = mixs.pid
        JOIN ( SELECT sum(oc_1.organism_quantity) AS size,
            se_1.pid
            FROM sampling_event se_1
                JOIN occurrence oc_1 ON oc_1.event_pid = se_1.pid
                JOIN asv asv_1 ON asv_1.pid = oc_1.asv_pid
                JOIN mixs mixs_1 ON mixs_1.pid = se_1.pid
                JOIN taxon_annotation ta_1 ON asv_1.pid = ta_1.asv_pid
            WHERE ta_1.target_prediction = true AND ta_1.annotation_target::text = mixs_1.target_gene::text
            GROUP BY se_1.pid) calc ON se.pid = calc.pid;


CREATE OR REPLACE VIEW api.dl_emof
AS
SELECT se.dataset_pid,
    (ds.dataset_id::text || ':'::text) || se.event_id::text AS "eventID",
    emof.measurement_type AS "measurementType",
    emof.measurement_type_id AS "measurementTypeID",
    emof.measurement_unit AS "measurementUnit",
    emof.measurement_unit_id AS "measurementUnitID",
    emof.measurement_value AS "measurementValue",
    emof.measurement_value_id AS "measurementValueID",
    emof.measurement_accuracy AS "measurementAccuracy",
    emof.measurement_determined_date AS "measurementDeterminedDate",
    emof.measurement_determined_by AS "measurementDeterminedBy",
    emof.measurement_method AS "measurementMethod",
    emof.measurement_remarks AS "measurementRemarks"
FROM sampling_event se
    JOIN emof ON emof.event_pid = se.pid
    JOIN dataset ds ON ds.pid = se.dataset_pid;


CREATE OR REPLACE VIEW api.dl_asv
AS
WITH ds_asv AS (
    SELECT DISTINCT se.dataset_pid,
        oc.asv_pid, oc.asv_id_alias, oc.associated_sequences, oc.previous_identifications
    FROM occurrence oc
        JOIN sampling_event se ON oc.event_pid = se.pid
        JOIN taxon_annotation ta_1 ON oc.asv_pid = ta_1.asv_pid
        JOIN mixs ON se.pid = mixs.pid
    WHERE ta_1.status::text = 'valid'::text
        AND ta_1.target_prediction = true
        AND ta_1.annotation_target::text = mixs.target_gene::text
)
SELECT ds_asv.dataset_pid,
    asv.asv_id AS "taxonID",
    ds_asv.asv_id_alias AS asv_id_alias,
    asv.asv_sequence AS "DNA_sequence",
    ta.scientific_name AS "scientificName",
    ta.taxon_rank AS "taxonRank",
    ta.kingdom,
    ta.phylum,
    ta.oorder AS "order",
    ta.class,
    ta.family,
    ta.genus,
    ta.specific_epithet AS "specificEpithet",
    ta.infraspecific_epithet AS "infraspecificEpithet",
    ta.otu,
    ta.date_identified AS "dateIdentified",
    ta.identification_references AS "identificationReferences",
    ds_asv.associated_sequences AS "associatedSequences",
    ds_asv.previous_identifications::text AS "previousIdentifications",
    concat_ws(' '::text, ta.annotation_algorithm, 'annotation against', ta.reference_db::text || ';'::text, 'confidence at lowest specified (ASV portal) taxon:', ta.annotation_confidence) AS "identificationRemarks"
FROM asv
    JOIN ds_asv ON asv.pid = ds_asv.asv_pid
    JOIN taxon_annotation ta ON asv.pid = ta.asv_pid
WHERE ta.status::text = 'valid'::text;


CREATE OR REPLACE VIEW api.dl_occurrence
AS
SELECT se.dataset_pid,
    (ds.dataset_id::text || ':'::text) || se.event_id::text AS "eventID",
    asv.asv_id AS "taxonID",
    oc.organism_quantity AS "organismQuantity"
FROM sampling_event se
    JOIN occurrence oc ON oc.event_pid = se.pid
    JOIN dataset ds ON ds.pid = se.dataset_pid
    JOIN asv ON asv.pid = oc.asv_pid
    JOIN mixs ON mixs.pid = se.pid
    JOIN taxon_annotation ta ON asv.pid = ta.asv_pid
WHERE ta.status::text = 'valid'::text
    AND ta.target_prediction = true
    AND ta.annotation_target::text = mixs.target_gene::text;
