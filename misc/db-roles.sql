--
-- Environment variables
--

\set passwd `echo "${POSTGRES_PASSWORD}"`
\set anon `echo "${PGRST_DB_ANON_ROLE}"`
\set anonpass `echo "${PGRST_DB_ANON_PASS}"`
\set db_schema `echo "${PGRST_DB_SCHEMA}"`

--
-- Roles
--

-- DB-import etc. via python
CREATE ROLE admin;
ALTER ROLE admin WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'passwd';
-- PostgREST
CREATE ROLE authenticator;
ALTER ROLE authenticator WITH NOSUPERUSER NOINHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'passwd';
CREATE ROLE :anon;
ALTER ROLE :anon WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOLOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'anonpass';
-- IPT
CREATE ROLE sbdi;
ALTER ROLE sbdi WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'passwd';

--
-- Schema
--

CREATE SCHEMA :db_schema;

--
-- Role memberships
--

GRANT admin TO authenticator;
GRANT :anon TO authenticator;

GRANT ALL ON SCHEMA :db_schema TO :anon;
GRANT ALL ON SCHEMA :db_schema TO authenticator;
GRANT ALL ON SCHEMA :db_schema TO sbdi;

GRANT ALL ON SCHEMA public TO :anon;
GRANT ALL ON SCHEMA public TO authenticator;
GRANT ALL ON SCHEMA public TO sbdi;

-- GRANT SELECT ON ALL TABLES IN SCHEMA :db_schema TO authenticator;
-- GRANT SELECT ON ALL TABLES IN SCHEMA :db_schema TO web_anon;
