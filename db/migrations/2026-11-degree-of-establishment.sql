--
-- Adds sampling_event.degree_of_establishment (dwc:degreeOfEstablishment),
-- used to flag non-natural settings such as aquarium/mesocosm experiments
-- ('captive'). The column is appended last in the views, so that CREATE OR
-- REPLACE works, grants are kept, and existing IPT mappings (which refer to
-- columns by position) are unaffected.
--
-- Run once on an existing database (after `make backup`), from mol-mod/:
--   docker exec -i asv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
--     < db/migrations/2026-11-degree-of-establishment.sql
--

\set ON_ERROR_STOP on
\set data_schema `echo ${DATA_SCHEMA:-public}`

BEGIN;

ALTER TABLE :data_schema.sampling_event
    ADD COLUMN IF NOT EXISTS degree_of_establishment character varying;

-- View definitions copied from db/db-api-schema.sql
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
    ta.class,
    ta.oorder AS "order",
    ta.family,
    ta.genus,
    ta.specific_epithet AS specificepithet,
    ta.infraspecific_epithet AS infraspecificepithet,
    ta.otu,
    ta.taxon_remarks AS "taxonRemarks",
    ta.date_identified AS "dateIdentified",
    ta.identification_references AS "identificationReferences",
    concat_ws(' '::text, ta.annotation_algorithm, 'annotation against', ta.reference_db::text || ';'::text, 'confidence at lowest specified (ASV portal) taxon:', ta.annotation_confidence) AS "identificationRemarks",
    (('By data provider: '::text || oc.previous_identifications::text) || '; By ASV portal: '::text) || concat_ws('|'::text, ta.kingdom, ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS "previousIdentifications",
    '' AS "dynamicProperties",
    se.degree_of_establishment AS "degreeOfEstablishment"
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
        AND ta.status::text = 'valid'::text
        GROUP BY se.pid) calc ON se.pid = calc.pid
WHERE ta.status::text = 'valid'
    AND ta.target_prediction = TRUE
    AND ta.annotation_target::text = mixs.target_gene::text;

SET search_path TO :data_schema;

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
    mixs.env_medium,
    se.degree_of_establishment AS "degreeOfEstablishment"
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
            AND ta_1.status::text = 'valid'::text
            GROUP BY se_1.pid) calc ON se.pid = calc.pid;

COMMIT;
