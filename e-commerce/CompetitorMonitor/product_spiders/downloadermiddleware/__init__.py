# -*- coding: utf-8 -*-
cache_storages = {
    'REDIS_POSTGRES': {
        'title': 'Redis + PostgreSQL',
        'class': 'product_spiders.downloadermiddleware.http_cache_storage_redis_postgres.RedisPostgresHttpCacheStorage'
    },
    'SSDB': {
        'title': 'SSDB',
        'class': 'product_spiders.downloadermiddleware.http_cache_storage_ssdb.SSDBHttpCacheStorage'
    }
}