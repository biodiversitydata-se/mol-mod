--
-- Environment variables
--

\set anon `echo ${PGRST_DB_ANON_ROLE:-web_anon}`
-- This is loaded directly from docker secret
-- See compose file & https://hub.docker.com/_/postgres under Docker secrets
\set passwd `echo ${POSTGRES_PASSWORD}`
-- These need to be read from container files
\set iptpass `cat ${POSTGRES_IPT_PASS_FILE}`
\set anonpass `cat ${PGRST_DB_ANON_PASS_FILE}`

--
-- Roles
--

-- Role that PostgREST uses for connecting to the database
CREATE ROLE authenticator;
ALTER ROLE authenticator WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'passwd';
-- Role that PostgREST switches into when running queries
CREATE ROLE :anon;
ALTER ROLE :anon WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOLOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'anonpass';
-- Role for connecting to database from IPT
CREATE ROLE ipt;
ALTER ROLE ipt WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'iptpass';

--
-- Role memberships
--

-- Make it possible for authenticator to switch into anon role, by making auth. member of anon
GRANT :anon TO authenticator;

--
-- Privileges on database objects
--

-- Let web users read all views in dedicated API schema
GRANT USAGE ON SCHEMA api TO :anon;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO :anon;
-- Also allow access to functions needed for paginated select2 dropdowns
-- & for getting sequences for BLAST hits
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO :anon;
GRANT ALL ON ALL TABLES IN SCHEMA api TO authenticator;
-- Only allow IPT user to access Darwin Core views
GRANT USAGE ON SCHEMA api TO ipt;
GRANT SELECT ON TABLE api.dwc_oc_occurrence TO ipt;
GRANT SELECT ON TABLE api.dwc_oc_mixs TO ipt;
GRANT SELECT ON TABLE api.dwc_oc_emof TO ipt;
