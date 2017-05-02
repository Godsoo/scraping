# -*- coding: utf-8 -*-
import unittest

from scrapy.spider import BaseSpider

from product_spiders.custom_crawl_methods.bigsitemethod import _check_cls_method_error, _bsm_create_cls, \
    check_fits_to_bigsitemethod

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.spiders.bi_worldwide_usa.amazon_direct import BIWAmazonDirectSpider


class TestBigSiteMethodCrawlMethod(unittest.TestCase):
    def test_check_mandatory_fields_allows_replacement(self):
        from scrapy.spider import BaseSpider

        class A(BaseSpider):
            def start_requests(self):
                pass

        methods_config = {'methods': ['parse', 'parse_full'], 'replacements': [('start_requests', True), ], 'requirements': [('start_urls', False)]}

        self.assertIsNone(_check_cls_method_error(A, methods_config))

    def test_create_new_cls(self):
        from scrapy.spider import BaseSpider
        from productspidersweb.models import Spider, CrawlMethod
        from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

        class A(BaseSpider):
            def start_requests(self):
                return 'a'

        spmdl = Spider()
        spmdl.website_id = 100
        spmdl.crawl_method2 = CrawlMethod()
        spmdl.crawl_method2.params = {'full_crawl_day': '1'}

        new_cls = _bsm_create_cls(A, spmdl)

        self.assertFalse(A == new_cls)
        self.assertTrue(hasattr(new_cls, 'start_requests'))
        self.assertIn(A, new_cls.__bases__)
        self.assertIn(BigSiteMethodSpider, new_cls.__bases__)
        self.assertEqual(new_cls.start_requests, BigSiteMethodSpider.start_requests)
        self.assertEqual(new_cls._start_requests_full, A.start_requests)

    def test_spider_init(self):
        from scrapy.spider import BaseSpider
        from productspidersweb.models import Spider, CrawlMethod

        class A(BaseSpider):
            name = 'a'
            allowed_domains = ['asd.com']

            def start_requests(self):
                return 'a'

            def parse_product(self, response):
                return 'qwe'

        spmdl = Spider()
        spmdl.website_id = 100
        spmdl.crawl_method2 = CrawlMethod()
        spmdl.crawl_method2.params = {'full_crawl_day': '1'}

        new_cls = _bsm_create_cls(A, spmdl)

        spider = new_cls("test spider")

        self.assertTrue(hasattr(spider, 'full_run'))

        self.assertFalse(spider.full_run)

    def test_create_new_cls_with_diff_base(self):
        from productspidersweb.models import Spider, CrawlMethod
        from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
        from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

        class A(BaseAmazonSpider):
            pass

        spmdl = Spider()
        spmdl.website_id = 100
        spmdl.crawl_method2 = CrawlMethod()
        spmdl.crawl_method2.params = {'full_crawl_day': '1'}

        new_cls = _bsm_create_cls(A, spmdl)

        self.assertFalse(A == new_cls)
        self.assertTrue(hasattr(new_cls, 'start_requests'))
        self.assertIn(A, new_cls.__bases__)
        self.assertIn(BigSiteMethodSpider, new_cls.__bases__)
        self.assertEqual(new_cls.start_requests, BigSiteMethodSpider.start_requests)
        self.assertEqual(new_cls._start_requests_full, A.start_requests)

    def test_spider_init_diff_base(self):
        from productspidersweb.models import Spider, CrawlMethod
        from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

        class A(BaseAmazonSpider):
            name = 'a'
            allowed_domains = ['asd.com']

        spmdl = Spider()
        spmdl.website_id = 100
        spmdl.crawl_method2 = CrawlMethod()
        spmdl.crawl_method2.params = {'full_crawl_day': '1'}

        new_cls = _bsm_create_cls(A, spmdl)

        spider = new_cls("test spider")

        self.assertTrue(hasattr(spider, 'full_run'))

        self.assertFalse(spider.full_run)

    def test_check_not_fits(self):
        class A(BaseSpider):
            pass

        errors = check_fits_to_bigsitemethod(A)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any(['parse_product' in error for error in errors]))
        self.assertTrue(any(['parse_full' in error for error in errors]))

    def test_check_not_fits_because_of_override(self):
        class A(BaseSpider):
            def full_run_required(self):
                pass

        errors = check_fits_to_bigsitemethod(A)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any(['full_run_required' in error and 'override' in error for error in errors]))

    def test_check_not_fits_because_of_override_in_parent(self):
        class A(BaseSpider):
            def full_run_required(self):
                pass

        class B(A):
            pass

        errors = check_fits_to_bigsitemethod(B)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any(['full_run_required' in error and 'override' in error for error in errors]))

    def test_check_fits_true_simple_spider(self):
        class A(BaseSpider):
            start_urls = ('asd', )

            def parse_product(self, response):
                pass

            def parse(self, response):
                pass

        errors = check_fits_to_bigsitemethod(A)

        self.assertEqual(len(errors), 0)

    def test_check_fits_amazon_spider(self):
        class A(BaseAmazonSpider):
            pass

        errors = check_fits_to_bigsitemethod(A)

        self.assertEqual(len(errors), 0)

    def test_check_fits_biw_amazon_spider(self):
        class A(BIWAmazonDirectSpider):
            pass

        errors = check_fits_to_bigsitemethod(A)

        self.assertEqual(len(errors), 0)
