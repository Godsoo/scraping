# Scrapy settings for product_spiders project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'product_spiders'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['product_spiders.spiders']
NEWSPIDER_MODULE = 'product_spiders.spiders'
USER_AGENT = 'Mozilla/5.0 (Windows NT 5.0; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'

RETRY_TIMES = 9
RETRY_HTTP_CODES = [500, 501, 502, 503, 504, 400, 401, 408, 403, 456, 429]

LOG_STDOUT = True

import os

if os.environ.get('PRODUCT_SPIDERS_PLAIN'):
    EXTENSIONS = {
        'product_spiders.extensions.DeleteCheckerExtension': 1001
    }
else:
    EXTENSIONS = {
        'product_spiders.extensions.UpdateManagerExtension': 1000,
        'product_spiders.extensions.MAPDeviationScreenshotExtension': 1002,
        'product_spiders.extensions.MethodDetectExtension': 1003,
        'product_spiders.extensions.LogStatsExtension': 1005
    }

    ITEM_PIPELINES = [
        'product_spiders.pipelines.RequiredFieldsPipeline',
        'product_spiders.pipelines.ReplaceIdentifierPipeline',
        'product_spiders.pipelines.ProductSpidersPipeline',
        'product_spiders.pipelines.PriceConversionRatePipeline',
        'product_spiders.pipelines.DuplicateProductsPipeline',
        'product_spiders.pipelines.CsvExportPipeline',
        'product_spiders.pipelines.MetadataExportPipeline'
    ]

    DOWNLOADER_MIDDLEWARES = {
        'product_spiders.middlewares.UserAgentMiddleWare': 400,
        'product_spiders.middlewares.ProxyMiddleWare': 451,
        'product_spiders.middlewares.TorMiddleWare': 452,
        'product_spiders.middlewares.ProxyServiceMiddleware': 550,
        'product_spiders.downloadermiddleware.stats.DownloaderStatsPerDomain': 850,
        'product_spiders.downloadermiddleware.stats.DownloaderProxyStats': 851,
        'product_spiders.downloadermiddleware.stats.DownloaderProxyStatsPerDomain': 852,
        'product_spiders.downloadermiddleware.http_cache_per_spider.HttpCacheMiddlewareEnablePerSpider': 900,
        'product_spiders.middlewares.AmazonMiddleWare': 399
    }

HTTPCACHE_PER_SPIDER_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 60 * 60 * 6
HTTPCACHE_IGNORE_HTTP_CODES = [400, 403, 404, 408, 500, 501, 502, 503, 504]
HTTPCACHE_STORAGE = 'product_spiders.downloadermiddleware.http_cache_storage_ssdb.SSDBHttpCacheStorage'

HTTPCACHE_POSTGRES_DB_URI = 'postgresql://productspiders:productspiders@148.251.79.44:5432/spiders_http_cache'
HTTPCACHE_REDIS_HOST = '148.251.79.44'
HTTPCACHE_REDIS_PORT = 6379

HTTPCACHE_SSDB_HOST = '148.251.79.44'
HTTPCACHE_SSDB_PORT = 8888

DOWNLOADER_STATS_PER_DOMAIN = True

if not os.environ.get('PRODUCT_SPIDERS_PLAIN'):
    SPIDER_LOADER_CLASS = 'product_spiders.spidermanager.custom_crawl_method_spidermanager.CustomCrawlMethodSpiderManager'
    # fallback for Scrapy 0.16
    SPIDER_MANAGER_CLASS = 'product_spiders.spidermanager.custom_crawl_method_spidermanager.CustomCrawlMethodSpiderManager'

DOWNLOADER_CLIENTCONTEXTFACTORY = 'product_spiders.contextfactory.TLSFlexibleContextFactory'