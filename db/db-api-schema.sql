
\set data_schema `echo ${DATA_SCHEMA:-public}`

--
-- api schema tables
--

CREATE SCHEMA api;

CREATE OR REPLACE VIEW api.dwc_oc_emof AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    ds.dataset_id || ':' || se.event_id_alias AS "eventID",
    ds.dataset_id || ':' || se.event_id_alias || ':' || oc.asv_id_alias AS "occurrenceID",
    ds.dataset_id || ':' || se.event_id_alias || ':' || emof.measurement_type AS "measurementID",
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
   AND ta.status::text = 'valid'
   AND ta.target_prediction = true AND ta.annotation_target::text = mixs.target_gene::text;

CREATE OR REPLACE VIEW api.dwc_oc_mixs AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    ds.dataset_id || ':' || se.event_id_alias AS "eventID",
    ds.dataset_id || ':' || se.event_id_alias || ':' || oc.asv_id_alias AS "occurrenceID",
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
   AND ta.status::text = 'valid'
   AND ta.target_prediction = true AND ta.annotation_target::text = mixs.target_gene::text;

CREATE OR REPLACE VIEW api.dwc_oc_occurrence AS
SELECT ds.pid AS dataset_pid,
    ds.dataset_id AS "datasetID",
    ds.dataset_id || ':' || se.event_id_alias AS "eventID",
    ds.dataset_id || ':' || se.event_id_alias || ':' || oc.asv_id_alias AS "occurrenceID",
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
    oc.associated_sequences AS "associatedSequences",
    se.recorded_by AS "recordedBy",
    se.material_sample_id AS "materialSampleID",
    se.sample_size_value AS "sampleSizeValue",
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
    (((ta.annotation_algorithm::text || ' annotation confidence (at lowest specified taxon): '::text) || ta.annotation_confidence) || ', against reference database: '::text) || ta.reference_db::text AS "identificationRemarks",
    'Identified by data provider as: '::text || oc.previous_identifications::text AS "previousIdentifications",
    row_to_json(( SELECT ds.*::record AS d
        FROM ( SELECT se.sample_size_value AS "sampleSizeValue",
                      oc.organism_quantity AS "organismQuantity",
                      m.sop,
                      m.seq_meth,
                      m.pcr_primer_name_forward,
                      m.pcr_primer_forward,
                      m.pcr_primer_name_reverse,
                      m.pcr_primer_reverse,
                      m.target_gene,
                      m.target_subfragment,
                      m.denoising_appr,
                      m.lib_layout,
                      a.asv_sequence AS "DNA_sequence",
                      m.env_broad_scale,
                      m.env_local_scale,
                      m.env_medium) d)) AS "dynamicProperties"
   FROM :data_schema.sampling_event se
   JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
   JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
   JOIN :data_schema.asv ON asv.pid = oc.asv_pid
   JOIN :data_schema.mixs ON mixs.pid = se.pid
   JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
   AND ta.status::text = 'valid'
   AND ta.target_prediction = true AND ta.annotation_target::text = mixs.target_gene::text;

CREATE VIEW api.app_filter_mixs_tax AS
 SELECT mixs.target_gene AS gene,
    mixs.target_subfragment AS sub,
    ((((mixs.pcr_primer_name_forward)::text || ': '::text) || (mixs.pcr_primer_forward)::text))::character varying AS fw_prim,
    ((((mixs.pcr_primer_name_reverse)::text || ': '::text) || (mixs.pcr_primer_reverse)::text))::character varying AS rv_prim,
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
   WHERE ds.in_bioatlas AND ta.status::text = 'valid'::text
      AND ta.target_prediction = true AND ta.annotation_target::text = mixs.target_gene::text;

CREATE VIEW api.app_search_mixs_tax AS
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
   WHERE ds.in_bioatlas AND ta.status::text = 'valid'::text
   AND ta.target_prediction = True
   AND ta.annotation_target = mixs.target_gene
  ORDER BY asv.asv_id, asv.asv_sequence, mixs.target_gene, mixs.target_subfragment, (((mixs.pcr_primer_name_forward)::text || ': '::text) || (mixs.pcr_primer_forward)::text), (((mixs.pcr_primer_name_reverse)::text || ': '::text) || (mixs.pcr_primer_reverse)::text);

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
                 AND ta.target_prediction = True
                 AND ta.annotation_target = mixs.target_gene) sub
   GROUP BY sub.gene
   ORDER BY sub.gene
  WITH DATA;

CREATE FUNCTION api.app_drop_options(field text, noffset bigint, nlimit integer, term text DEFAULT ''::text, kingdom text[] DEFAULT '{}'::text[], phylum text[] DEFAULT '{}'::text[], classs text[] DEFAULT '{}'::text[], oorder text[] DEFAULT '{}'::text[], family text[] DEFAULT '{}'::text[], genus text[] DEFAULT '{}'::text[], species text[] DEFAULT '{}'::text[], gene text[] DEFAULT '{}'::text[], sub text[] DEFAULT '{}'::text[], fw_prim text[] DEFAULT '{}'::text[], rv_prim text[] DEFAULT '{}'::text[]) RETURNS TABLE(data json)
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
BEGIN
	RETURN QUERY EXECUTE
		format('with filtered as (
			   SELECT DISTINCT %I
			   FROM api.app_filter_mixs_tax
			   WHERE %I <> '''' AND %I IS NOT NULL
			   AND ($1 = ''{}'' OR kingdom IN (SELECT unnest($1)))
			   AND ($2 = ''{}'' OR phylum IN (SELECT unnest($2)))
			   AND ($3 = ''{}'' OR classs IN (SELECT unnest($3)))
			   AND ($4 = ''{}'' OR oorder IN (SELECT unnest($4)))
			   AND ($5 = ''{}'' OR family IN (SELECT unnest($5)))
			   AND ($6 = ''{}'' OR genus IN (SELECT unnest($6)))
			   AND ($7 = ''{}'' OR species IN (SELECT unnest($7)))
			   AND %I ~* $8
			   AND ($9 = ''{}'' OR gene IN (SELECT unnest($9)))
			   AND ($14 = ''{}'' OR sub IN (SELECT unnest($14)))
			   AND ($10 = ''{}'' OR fw_prim IN (SELECT unnest($10)))
			   AND ($11 = ''{}'' OR rv_prim IN (SELECT unnest($11)))
			   )
			   SELECT json_build_object(
    			''count'', (SELECT COUNT(*) FROM filtered),
    			''results'', COALESCE(json_agg(to_json(t)),''[]''))
			   from (
    			SELECT %I AS "id", %I AS "text"
			   	FROM filtered
			   	ORDER BY %I
			   	OFFSET $12
			   	LIMIT $13
			  ) t', field, field, field, field, field, field, field)
   USING kingdom, phylum, classs, oorder, family, genus, species, '^'||term||'.*$', gene, fw_prim, rv_prim, noffset, nlimit, sub;
END
$_$;

CREATE VIEW api.app_asvs_for_blastdb AS
 SELECT asv.asv_id,
        concat_ws(';'::text, ta.kingdom, ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS higher_taxonomy,
        asv.asv_sequence
   FROM :data_schema.asv
   JOIN :data_schema.taxon_annotation ta ON asv.pid = ta.asv_pid
  WHERE ta.status::text = 'valid'::text
    AND ta.target_prediction = True
    AND asv.pid IN (
        SELECT DISTINCT ib.pid
        FROM asv ib
           JOIN :data_schema.occurrence oc ON oc.asv_pid = ib.pid
           JOIN :data_schema.sampling_event se ON oc.event_pid = se.pid
           JOIN :data_schema.mixs ON se.pid = mixs.pid
           JOIN :data_schema.taxon_annotation tg ON tg.asv_pid = ib.pid
           JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
        WHERE ds.in_bioatlas AND tg.annotation_target = mixs.target_gene
        );

CREATE FUNCTION api.app_seq_from_id(ids character varying[]) RETURNS TABLE(asv_id CHARACTER(36), ASV_SEQUENCE CHARACTER VARYING)
    LANGUAGE sql IMMUTABLE
    AS $$
   SELECT asv_id, asv_sequence FROM api.app_asvs_for_blastdb WHERE asv_id IN (
	   SELECT unnest(ids)
	)
$$;
