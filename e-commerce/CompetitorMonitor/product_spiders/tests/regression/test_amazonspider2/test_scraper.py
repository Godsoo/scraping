# -*- coding: utf-8 -*-

from unittest import TestCase

from product_spiders.base_spiders.amazonspider2 import AmazonScraper
from product_spiders.response_utils import download_response


def response_is_ok(response):
    msg = "We're very sorry, but we're having trouble doing what you just asked us"
    if msg.lower() in response.body.lower():
        return False
    return True


def load_page(url, tries=3):
    try_number = 0
    while try_number < tries:
        response = download_response(url)
        if response_is_ok(response):
            return response
    return None


class TestScraperRegression(TestCase):
    def test_detects_kindle(self):
        url = 'http://www.amazon.com/ML-Working-Programmer-Larry-Paulson-ebook/dp/B00D2WQ4EE'
        scraper = AmazonScraper()
        response = download_response(url)

        self.assertTrue(scraper.is_kindle_book(response))

    def test_detects_non_kindle(self):
        url = 'http://www.amazon.com/gp/product/052156543X/'
        scraper = AmazonScraper()
        response = download_response(url)
        self.assertFalse(scraper.is_kindle_book(response))