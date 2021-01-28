
\set data_schema `echo ${DATA_SCHEMA:-public}`

--
-- api schema tables
--

CREATE SCHEMA api;

CREATE OR REPLACE VIEW api.dwc_oc_emof AS
 SELECT ds.dataset_id AS "datasetID",
    se.event_id AS "eventID",
    oc.occurrence_id AS "occurrenceID",
    emof.measurement_id AS "measurementID",
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
   JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid;

CREATE OR REPLACE VIEW api.dwc_oc_mixs AS
 SELECT ds.dataset_id AS "datasetID",
    se.event_id AS "eventID",
    oc.occurrence_id AS "occurrenceID",
    asv.asv_id AS "taxonID",
    mixs.sop,
    mixs.pcr_primer_name_forward,
    mixs.pcr_primer_name_reverse,
    mixs.pcr_primer_forward,
    mixs.pcr_primer_reverse,
    mixs.target_gene,
    mixs.target_subfragment,
    asv.asv_sequence AS "DNA_sequence",
    mixs.env_broad_scale,
    mixs.env_local_scale,
    mixs.env_medium
   FROM :data_schema.mixs
   JOIN :data_schema.sampling_event se ON mixs.pid = se.pid
   JOIN :data_schema.occurrence oc ON oc.event_pid = se.pid
   JOIN :data_schema.dataset ds ON se.dataset_pid = ds.pid
   JOIN :data_schema.asv asv ON asv.pid = oc.asv_pid;


CREATE VIEW api.app_filter_mixs_tax AS
 SELECT m.target_gene AS gene,
    m.target_subfragment AS sub,
    ((((m.pcr_primer_name_forward)::text || ': '::text) || (m.pcr_primer_forward)::text))::character varying AS fw_prim,
    ((((m.pcr_primer_name_reverse)::text || ': '::text) || (m.pcr_primer_reverse)::text))::character varying AS rv_prim,
    ta.kingdom,
    ta.phylum,
    ta.class AS classs,
    ta.oorder,
    ta.family,
    ta.genus,
    ta.specific_epithet AS species
   FROM :data_schema.mixs m
   JOIN :data_schema.occurrence o ON o.event_pid = m.pid
   JOIN :data_schema.asv a ON a.pid = o.asv_pid
   JOIN :data_schema.taxon_annotation ta ON a.pid = ta.asv_pid;

CREATE VIEW api.app_search_mixs_tax AS
 SELECT a.asv_id,
    concat_ws('|'::text, concat_ws(''::text, a.asv_id, '-', ta.kingdom), ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS asv_tax,
    a.asv_sequence,
    m.target_gene AS gene,
    m.target_subfragment AS sub,
    (m.pcr_primer_name_forward)::text AS fw_name,
    (m.pcr_primer_forward)::text AS fw_sequence,
    (m.pcr_primer_name_reverse)::text AS rv_name,
    (m.pcr_primer_reverse)::text AS rv_sequence,
    (((m.pcr_primer_name_forward)::text || ': '::text) || (m.pcr_primer_forward)::text) AS fw_prim,
    (((m.pcr_primer_name_reverse)::text || ': '::text) || (m.pcr_primer_reverse)::text) AS rv_prim,
    ta.kingdom,
    ta.phylum,
    ta.class AS classs,
    ta.oorder,
    ta.family,
    ta.genus,
    ta.specific_epithet AS species
   FROM :data_schema.mixs m
   JOIN :data_schema.occurrence o ON o.event_pid = m.pid
   JOIN :data_schema.asv a ON a.pid = o.asv_pid
   JOIN :data_schema.taxon_annotation ta ON a.pid = ta.asv_pid
  ORDER BY a.asv_id, a.asv_sequence, m.target_gene, m.target_subfragment, (((m.pcr_primer_name_forward)::text || ': '::text) || (m.pcr_primer_forward)::text), (((m.pcr_primer_name_reverse)::text || ': '::text) || (m.pcr_primer_reverse)::text);

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
			   AND %I ~ $8
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
   USING kingdom, phylum, classs, oorder, family, genus, species, term, gene, fw_prim, rv_prim, noffset, nlimit, sub;
END
$_$;

CREATE VIEW api.app_asvs_for_blastdb AS
 SELECT a.asv_id,
    concat_ws(';'::text, ta.kingdom, ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS higher_taxonomy,
    a.asv_sequence
   FROM (:data_schema.asv a
     JOIN :data_schema.taxon_annotation ta ON ((a.pid = ta.asv_pid)))
  WHERE ((ta.status)::text = 'valid'::text);

CREATE FUNCTION api.app_seq_from_id(ids character varying[]) RETURNS TABLE(asv_id CHARACTER(36), ASV_SEQUENCE CHARACTER VARYING)
    LANGUAGE sql IMMUTABLE
    AS $$
   SELECT asv_id, asv_sequence FROM api.app_asvs_for_blastdb WHERE asv_id IN (
	   SELECT unnest(ids)
	)
$$;
