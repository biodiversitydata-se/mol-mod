SET client_encoding = 'UTF8';

--
-- data schema tables
--
CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.dataset (
    id SERIAL PRIMARY KEY,
    dataset_id character varying UNIQUE,
    insertion_time timestamp without time zone,
    provider_email character varying
);

CREATE TABLE IF NOT EXISTS public.sampling_event (
    id SERIAL PRIMARY KEY,
    event_id character varying UNIQUE,
    material_sample_id character varying,
    dataset_id integer REFERENCES public.dataset(id) NOT NULL,
    event_date character varying NOT NULL,
    sampling_protocol character varying NOT NULL,
    sample_size_value integer NOT NULL,
    location_id character varying,
    decimal_latitude numeric NOT NULL,
    decimal_longitude numeric NOT NULL,
    geodetic_datum character varying,
    coordinate_uncertainty_in_meters numeric,
    event_id_alias character varying,
    recorded_by character varying,
    verbatim_locality character varying,
    municipality character varying,
    country character varying,
    minimum_elevation_in_meters numeric,
    maximum_elevation_in_meters numeric,
    minimum_depth_in_meters numeric,
    maximum_depth_in_meters numeric
);

CREATE TABLE IF NOT EXISTS public.mixs (
    id integer PRIMARY KEY REFERENCES public.sampling_event(id),
    sop character varying,
    target_gene character varying NOT NULL,
    target_subfragment character varying NOT NULL,
    pcr_primer_name_forward character varying NOT NULL,
    pcr_primer_name_reverse character varying NOT NULL,
    pcr_primer_forward character varying NOT NULL,
    pcr_primer_reverse character varying NOT NULL,
    env_broad_scale character varying NOT NULL,
    env_local_scale character varying NOT NULL,
    env_medium character varying NOT NULL
);

CREATE TABLE IF NOT EXISTS public.emof (
    id SERIAL PRIMARY KEY,
    measurement_id character varying UNIQUE,
    measurement_type character varying,
    measurement_type_id character varying,
    measurement_value character varying,
    measurement_value_id character varying,
    measurement_unit character varying,
    measurement_unit_id character varying,
    measurement_accuracy character varying,
    measurement_remarks character varying,
    event_id integer NOT NULL REFERENCES public.sampling_event(id),
    measurement_determined_date character varying,
    measurement_determined_by character varying,
    measurement_method character varying
);


CREATE TABLE IF NOT EXISTS public.asv (
    id SERIAL PRIMARY KEY,
    asv_id character(36) UNIQUE,
    asv_sequence character varying NOT NULL
);

CREATE TABLE IF NOT EXISTS public.occurrence (
    id SERIAL PRIMARY KEY,
    occurrence_id character varying UNIQUE,
    event_id integer REFERENCES public.sampling_event(id) NOT NULL,
    asv_id integer REFERENCES public.asv(id) NOT NULL,
    organism_quantity integer NOT NULL,
    previous_identifications character varying NOT NULL,
    asv_id_alias character varying NOT NULL,
    associated_sequences character varying
);

CREATE TABLE IF NOT EXISTS public.taxon_annotation (
    annotation_id SERIAL PRIMARY KEY,
    asv_id  integer REFERENCES public.asv(id) NOT NULL,
    status character varying NOT NULL,
    kingdom character varying,
    phylum character varying,
    class character varying,
    oorder character varying,
    family character varying,
    genus character varying,
    specific_epithet character varying,
    infraspecific_epithet character varying,
    otu character varying,
    date_identified date NOT NULL,
    identification_references character varying,
    reference_db character varying NOT NULL,
    annotation_algorithm character varying NOT NULL,
    annotation_confidence numeric,
    taxon_remarks character varying,
    scientific_name character varying,
    taxon_rank character varying
);

CREATE INDEX IF NOT EXISTS taxon_asv ON public.taxon_annotation(asv_id);
CREATE INDEX IF NOT EXISTS occurrence_event ON public.occurrence(event_id);
CREATE INDEX IF NOT EXISTS occurrence_asv ON public.occurrence(asv_id);
