--
-- Psql variables
--

-- Get role names from .env
\set auth `echo ${PGRST_DB_AUTH_ROLE:-auth}`
\set anon `echo ${PGRST_DB_ANON_ROLE:-anon}`
\set ipt `echo ${POSTGRES_IPT_ROLE:-ipt}`
-- Read pwds from secrets passed to containers via compose file
\set authpass `cat ${POSTGRES_AUTH_PASS_FILE}`
\set iptpass `cat ${POSTGRES_IPT_PASS_FILE}`


--
-- Roles
--

-- Role that PostgREST uses for connecting to the database
CREATE ROLE :auth;
ALTER ROLE :auth WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'authpass';
-- Role that PostgREST switches into when running queries
CREATE ROLE :anon;
ALTER ROLE :anon WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB NOLOGIN NOREPLICATION NOBYPASSRLS;

-- Role for connecting to database from IPT
CREATE ROLE :ipt;
ALTER ROLE :ipt WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'iptpass';

--
-- Role memberships
--

-- Make it possible for :auth to switch into anon role, by making auth. member of anon
GRANT :anon TO :auth;

--
-- Privileges on database objects
--

-- Let web users read all views in dedicated API schema
GRANT USAGE ON SCHEMA api TO :anon;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO :anon;
-- Also allow access to functions needed for paginated select2 dropdowns
-- & for getting sequences for BLAST hits
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO :anon;

-- Only allow IPT user to access Darwin Core views
GRANT USAGE ON SCHEMA api TO :ipt;
GRANT SELECT ON TABLE api.dwc_oc_occurrence TO :ipt;
GRANT SELECT ON TABLE api.dwc_oc_mixs TO :ipt;
GRANT SELECT ON TABLE api.dwc_oc_emof TO :ipt;
