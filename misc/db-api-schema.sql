
\set data_schema `echo ${DATA_SCHEMA:-public}`

--
-- api schema tables
--

CREATE SCHEMA api;


CREATE VIEW api.app_filter_mixs_tax AS
 SELECT DISTINCT m.target_gene AS gene,
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
   FROM :data_schema.asv a,
    :data_schema.mixs m,
    :data_schema.occurrence o,
    :data_schema.taxon_annotation ta
  WHERE ((a.asv_id = o.asv_id) AND ((o.event_id)::text = (m.event_id)::text) AND (a.asv_id = ta.asv_id));


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
 SELECT ta.asv_id,
    concat_ws(';'::text, ta.kingdom, ta.phylum, ta.class, ta.oorder, ta.family, ta.genus, ta.specific_epithet, ta.infraspecific_epithet, ta.otu) AS higher_taxonomy,
    asv.asv_sequence
   FROM (:data_schema.asv
     JOIN :data_schema.taxon_annotation ta ON ((asv.asv_id = ta.asv_id)))
  WHERE ((ta.status)::text = 'valid'::text);

CREATE FUNCTION api.app_seq_from_id(ids character varying[]) RETURNS SETOF :data_schema.asv
    LANGUAGE sql IMMUTABLE
    AS $$
   SELECT asv_id, asv_sequence FROM api.app_asvs_for_blastdb a WHERE asv_id IN (
	   SELECT unnest(ids)
	)
$$;
