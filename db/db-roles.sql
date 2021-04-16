--
-- Environment variables
--
-- This is loaded directly from docker secrets (see compose file)
-- See https://hub.docker.com/_/postgres under Docker secrets
\set passwd `echo ${POSTGRES_PASSWORD}`
-- These need to be read from container files
\set iptpass `cat ${POSTGRES_IPT_PASS_FILE}`
\set anon `echo ${PGRST_DB_ANON_ROLE:-web_anon}`
\set anonpass `cat ${PGRST_DB_ANON_PASS_FILE}`

--
-- Roles
--

-- PostgREST
CREATE ROLE authenticator;
ALTER ROLE authenticator WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'passwd';
CREATE ROLE :anon;
ALTER ROLE :anon WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOLOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'anonpass';
CREATE ROLE ipt;
ALTER ROLE ipt WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'iptpass';
--
-- Role memberships
--

GRANT :anon TO authenticator;

GRANT USAGE ON SCHEMA api TO :anon;
GRANT USAGE ON SCHEMA api TO ipt;

GRANT SELECT ON ALL TABLES IN SCHEMA api TO :anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO :anon;
GRANT ALL ON ALL TABLES IN SCHEMA api TO authenticator;

GRANT SELECT ON TABLE api.dwc_oc_occurrence TO ipt;
GRANT SELECT ON TABLE api.dwc_oc_mixs TO ipt;
GRANT SELECT ON TABLE api.dwc_oc_emof TO ipt;
