# -*- coding: utf-8 -*-
from product_spiders.base_spiders.amazonspider2.scraper import AmazonUrlCreator, AmazonScraper
from product_spiders.base_spiders.amazonspider2.items import AmazonProductLoader, AmazonProduct
from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpider, BaseAmazonConcurrentSpiderWithCaptcha
from product_spiders.base_spiders.amazonspider2.legoamazonspider import BaseLegoAmazonSpider
from product_spiders.base_spiders.amazonspider2.utils import safe_copy_meta
