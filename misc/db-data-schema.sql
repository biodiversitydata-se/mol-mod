SET client_encoding = 'UTF8';

--
-- data schema tables
--
CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.dataset (
    pid BIGSERIAL PRIMARY KEY,
    dataset_id character varying UNIQUE,
    insertion_time timestamp without time zone NOT NULL DEFAULT now(),
    published boolean default false,
    in_bioatlas boolean default false,
    provider_email character varying
);

CREATE TABLE IF NOT EXISTS public.sampling_event (
    pid BIGSERIAL PRIMARY KEY,
    material_sample_id character varying,
    dataset_pid integer REFERENCES public.dataset(pid) NOT NULL,
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
    pid integer PRIMARY KEY REFERENCES public.sampling_event(pid),
    sop character varying,
    target_gene character varying NOT NULL,
    target_subfragment character varying NOT NULL,
    lib_layout character varying NOT NULL,
    pcr_primer_name_forward character varying NOT NULL,
    pcr_primer_name_reverse character varying NOT NULL,
    pcr_primer_forward character varying NOT NULL,
    pcr_primer_reverse character varying NOT NULL,
    env_broad_scale character varying NOT NULL,
    env_local_scale character varying NOT NULL,
    env_medium character varying NOT NULL
);

CREATE TABLE IF NOT EXISTS public.emof (
    pid BIGSERIAL PRIMARY KEY,
    measurement_type character varying,
    measurement_type_id character varying,
    measurement_value character varying,
    measurement_value_id character varying,
    measurement_unit character varying,
    measurement_unit_id character varying,
    measurement_accuracy character varying,
    measurement_remarks character varying,
    event_pid integer NOT NULL REFERENCES public.sampling_event(pid),
    measurement_determined_date character varying,
    measurement_determined_by character varying,
    measurement_method character varying
);

CREATE TABLE IF NOT EXISTS public.asv (
    pid BIGSERIAL PRIMARY KEY,
    asv_id character(36) UNIQUE,
    asv_sequence character varying UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS public.occurrence (
    pid BIGSERIAL PRIMARY KEY,
    event_pid integer REFERENCES public.sampling_event(pid) NOT NULL,
    asv_pid integer REFERENCES public.asv(pid) NOT NULL,
    organism_quantity integer NOT NULL,
    previous_identifications character varying NOT NULL,
    asv_id_alias character varying NOT NULL,
    associated_sequences character varying
);

CREATE TABLE IF NOT EXISTS public.taxon_annotation (
    pid BIGSERIAL PRIMARY KEY,
    asv_pid  integer REFERENCES public.asv(pid) NOT NULL,
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

CREATE INDEX IF NOT EXISTS taxon_asv ON public.taxon_annotation(asv_pid);
CREATE INDEX IF NOT EXISTS mixs_id ON public.mixs(pid);
CREATE INDEX IF NOT EXISTS occurrence_event ON public.occurrence(event_pid);
CREATE INDEX IF NOT EXISTS occurrence_asv ON public.occurrence(asv_pid);
