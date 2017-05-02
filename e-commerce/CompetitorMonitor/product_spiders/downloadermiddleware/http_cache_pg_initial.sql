CREATE DATABASE spiders_http_cache;
GRANT ALL PRIVILEGES ON DATABASE spiders_http_cache TO productspiders;

\c spiders_http_cache

CREATE EXTENSION hstore;

CREATE TABLE http_cache (
  id      SERIAL PRIMARY KEY,
  hashkey VARCHAR UNIQUE NOT NULL,
  value   hstore
);
ALTER TABLE http_cache OWNER TO productspiders;