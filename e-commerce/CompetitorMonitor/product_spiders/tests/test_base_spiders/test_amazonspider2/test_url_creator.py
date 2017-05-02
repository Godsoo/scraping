# -*- coding: utf-8 -*-
import unittest
from urlparse import urlparse, parse_qs

from product_spiders.base_spiders.amazonspider2 import AmazonUrlCreator


class TestAmazonUrlCreator(unittest.TestCase):
    """
    Tests url creator class
    """
    def test_domain_name_from_url(self):
        url = "http://www.amazon.com/gp/product/B001OW7JT8/ref=s9_psimh_gw_p201_d1_i2?pf_rd_m=ATVPDKIKX0DER&pf_rd_s=center-2&pf_rd_r=0QB7BBXPS3J4660YQN0X&pf_rd_t=101&pf_rd_p=1688200382&pf_rd_i=507846"
        self.assertEqual(AmazonUrlCreator.get_domain_from_url(url), 'www.amazon.com')

        url = "http://www.amazon.co.uk/gp/product/B001UHOQ98/ref=s9_simh_gw_p200_d17_i3?pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=center-2&pf_rd_r=0XD4CJ7P35531QB9PRQM&pf_rd_t=101&pf_rd_p=455345507&pf_rd_i=468294"
        self.assertEqual(AmazonUrlCreator.get_domain_from_url(url), 'www.amazon.co.uk')

    def test_get_review_identifier_from_url(self):
        url = "http://www.amazon.com/review/RRSU6FI3Y6D5I/ref=cm_cr_pr_viewpnt#RRSU6FI3Y6D5I"
        self.assertEqual(AmazonUrlCreator.get_review_identifier_from_url(url), 'RRSU6FI3Y6D5I')

        url = "http://www.amazon.co.uk/review/R3E56QODZNNIW4/ref=cm_cr_pr_perm?ie=UTF8&ASIN=0735619670"
        self.assertEqual(AmazonUrlCreator.get_review_identifier_from_url(url), 'R3E56QODZNNIW4')

    def test_build_url_from_asin(self):
        domain = 'amazon.com'
        asin = '123456'
        expected_url = 'http://www.amazon.com/gp/product/123456/?ref=twister_dp_update&ie=UTF8&psc=1'
        self.assertEqual(AmazonUrlCreator.build_url_from_asin(domain, asin), expected_url)

    def test_build_url_from_asin_and_dealer_id(self):
        domain = 'amazon.co.uk'
        asin = '123456'
        dealder_id = '654321'
        expected_url = 'http://www.amazon.co.uk/gp/product/123456/?m=654321&ref=twister_dp_update&ie=UTF8&psc=1'
        self.assertEqual(AmazonUrlCreator.build_url_from_asin_and_dealer_id(domain, asin, dealder_id), expected_url)

    def test_build_search_url(self):
        domain = 'amazon.it'
        search_string = 'something'

        result = AmazonUrlCreator.build_search_url(domain, search_string)
        parsed_result = urlparse(result)
        parsed_query = parse_qs(parsed_result.query)

        self.assertEqual(parsed_result.hostname, 'www.' + domain)
        self.assertEqual(parsed_result.path, '/s/ref=nb_sb_noss')
        self.assertEqual(parsed_query['field-keywords'][0], search_string)
        self.assertNotIn('emi', parsed_query)

    def test_build_search_query_amazon_direct(self):
        domain = 'amazon.it'
        search_string = 'something'

        result = AmazonUrlCreator.build_search_url(domain, search_string, amazon_direct=True)
        parsed_result = urlparse(result)
        parsed_query = parse_qs(parsed_result.query)

        self.assertEqual(parsed_query['emi'][0], 'A11IL2PNWYJU7H')

        result = AmazonUrlCreator.build_search_url("amazon.com", search_string, amazon_direct=True)
        parsed_result = urlparse(result)
        parsed_query = parse_qs(parsed_result.query)

        self.assertEqual(parsed_query['emi'][0], 'ATVPDKIKX0DER')