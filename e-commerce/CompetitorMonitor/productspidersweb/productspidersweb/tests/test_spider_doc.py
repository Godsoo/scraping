# -*- coding: utf-8 -*-
from unittest import TestCase

from productspidersweb.spider_doc import parse_spider_top_comment


class TestParseTopComment(TestCase):
    def test1(self):
        comment = """Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3941-e-bedding---new-site---argos
This spider searches for SKUs in the website. In the search terms the slashes should be encoded as %252F.
When searching by code the website redirects to the product page."""
        ticket_num, ticket_url, rest_lines = parse_spider_top_comment(comment)

        self.assertEqual(ticket_num, 3941)
        self.assertEqual(ticket_url, 'https://www.assembla.com/spaces/competitormonitor/tickets/3941-e-bedding---new-site---argos')
        self.assertEqual(len(rest_lines), len(comment.splitlines()) - 1)

    def test2(self):
        comment = """
Customer: BIW USA
Website: http://www.bestbuy.com
Type: Marketplace, extract all dealers.
Crawling process: search by brand using the client file from the SFTP and extract all results
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4022-biw-usa-|-bestbuy-|-new-sites/details#

IMPORTANT!
"""
        ticket_num, ticket_url, rest_lines = parse_spider_top_comment(comment)

        self.assertEqual(ticket_num, 4022)
        self.assertEqual(ticket_url, 'https://www.assembla.com/spaces/competitormonitor/tickets/4022-biw-usa-|-bestbuy-|-new-sites/details#')
        self.assertEqual(len(rest_lines), len(comment.splitlines()) - 1)

    def test3(self):
        comment = """
Name: navico-amer-googleshopping
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
Ticket reference: https://www.assembla.com/spaces/competitormonitor/tickets/4212

IMPORTANT:

- Local proxies management. It uses Proxy Service.
- Use of PhantomJS to browse the website.
- PLEASE be CAREFUL, Google bans the proxies quickly.
"""
        ticket_num, ticket_url, rest_lines = parse_spider_top_comment(comment)

        self.assertEqual(ticket_num, 4212)
        self.assertEqual(ticket_url, 'https://www.assembla.com/spaces/competitormonitor/tickets/4212')
        self.assertEqual(len(rest_lines), len(comment.splitlines()) - 1)

    def test4(self):
        comment = """
- Original assembla ticket #: 3916
- Run Scrapy >= 0.15 for correct operation (cookiejar feature)
- Prices including Tax
- It uses cache by using previous crawl data and updating only prices and stock status from product lists.
  Enter to product page only for new products, this is only for some fields like SKU which
  are not in products list page
"""
        ticket_num, ticket_url, rest_lines = parse_spider_top_comment(comment)

        self.assertEqual(ticket_num, 3916)
        self.assertEqual(ticket_url, 'https://www.assembla.com/spaces/competitormonitor/tickets/3916')
        self.assertEqual(len(rest_lines), len(comment.splitlines()) - 1)