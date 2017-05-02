CREATE TYPE http_cache_storage AS ENUM ('REDIS_POSTGRES', 'SSDB');

ALTER TABLE spider add column cache_storage http_cache_storage default null;
