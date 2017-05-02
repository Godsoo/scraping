# -*- coding: utf-8 -*-
"""
This spider is set as a secondary spider to the Alliance Online's Nisbets.
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4843-brakes-ce-|-lockhart--amp--nisbets-|-secondary-spiders/details#
"""

from product_spiders.base_spiders import SecondaryBaseSpider


class NisbetsSpider(SecondaryBaseSpider):
    name = 'brakes_ce-nisbets.co.uk'
    allowed_domains = ['nisbets.co.uk']
    start_urls = ('http://www.nisbets.co.uk/Homepage.action',)
    csv_file = 'alliance_online/nisbets_crawl.csv'
