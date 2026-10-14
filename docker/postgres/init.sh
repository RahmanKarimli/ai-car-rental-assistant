# Sourced by the PostgreSQL entrypoint; deliberately non-executable for noexec mounts.
set -eu
APP_PASSWORD=$(cat /run/secrets/app_database_password)
GRAPH_PASSWORD=$(cat /run/secrets/graph_database_password)
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_password="$APP_PASSWORD" --set=graph_password="$GRAPH_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS btree_gist;
SELECT 'CREATE ROLE rental_app LOGIN PASSWORD ' || quote_literal(:'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rental_app') \gexec
SELECT 'CREATE ROLE rental_graph LOGIN PASSWORD ' || quote_literal(:'graph_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rental_graph') \gexec
CREATE SCHEMA IF NOT EXISTS agent_state AUTHORIZATION rental_graph;
GRANT USAGE ON SCHEMA public TO rental_app;
SQL
