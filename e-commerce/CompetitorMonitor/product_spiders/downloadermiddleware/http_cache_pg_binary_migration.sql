CREATE TABLE http_cache_binary (
  id            SERIAL PRIMARY KEY,
  hashkey       VARCHAR UNIQUE              NOT NULL,

  ts            TIMESTAMP WITHOUT TIME ZONE NOT NULL,

  request_url   VARCHAR(1024)               NOT NULL,
  request_meta  hstore                      NOT NULL,
  request_body  BYTEA,

  response_url  VARCHAR(1024)               NOT NULL,
  response_meta hstore                      NOT NULL,
  response_body BYTEA
);
