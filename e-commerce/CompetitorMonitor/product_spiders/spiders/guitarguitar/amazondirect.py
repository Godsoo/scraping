# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4748

The spider uses amazon base spider, however it overwrites `parse_product_list` method
to satisfy requirement - filter by brand

"""
import os
import csv
import urlparse as up
from urllib import urlencode
from collections import OrderedDict

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator, safe_copy_meta

HERE = os.path.abspath(os.path.dirname(__file__))


def filter_by_brand(url, brand):
    parsed = up.urlparse(url)
    parsed_query = up.parse_qs(parsed.query)
    if parsed_query.get('rh'):
        filter_options = OrderedDict([x.split(':') for x in parsed_query['rh'][0].split(',')])
    else:
        filter_options = OrderedDict()
    if 'p_89' in filter_options:
        filter_options['p_89'] = filter_options['p_89'] + '|' + brand
    else:
        filter_options['p_89'] = brand
    parsed_query['rh'] = ','.join('{}:{}'.format(k, v) for k, v in filter_options.items())
    new_parsed_url = up.ParseResult(parsed.scheme, parsed.netloc, parsed.path, parsed.params,
                                    urlencode(parsed_query, doseq=True), parsed.fragment)
    new_url = up.urlunparse(new_parsed_url)
    return new_url


class GuitarGuitarAmazonCoUkBaseSpider(BaseAmazonSpider):
    name = 'guitarguitar_amazon.co.uk_direct'
    domain = 'amazon.co.uk'

    type = 'category'

    _use_amazon_identifier = True

    parse_options = True

    do_retry = True
    model_as_sku = True

    max_pages = None

    def __init__(self, *args, **kwargs):
        super(GuitarGuitarAmazonCoUkBaseSpider, self).__init__(*args, **kwargs)

        filename = os.path.join(HERE, 'guitarguitar_products.csv')

        with open(filename) as f:
            self.brands = list({x['BRAND'] for x in csv.DictReader(f)})

        # Hard-code these two, as they are the same as Beyer
        self.brands.append('Beyer Dynamic')
        self.brands.append('Beyerdynamic')
        # This is Electro Harmonix
        self.brands.append("electro-harmonix")
        # Akai
        self.brands.append("AKAI Pro")
        # Gibson
        self.brands.append("Gibson")
        self.brands.append("Gibson Gear")
        # Yamaha
        self.brands.append('Yamaha Commercial')
        self.brands.append('Yamaha Electronics')
        self.brands.append('Yamaha Music Europe')

        self.brands = sorted(self.brands)

        self.log("Collected brands: {}".format(", ".join(self.brands)))

    def get_category_url_generator(self):
        """
        Yields category urls one by one
        """
        yield "https://www.amazon.co.uk/s/ref=sr_nr_p_89_0?rh=n%3A340837031", \
              "Musical Instruments & DJ Equipment"

    def parse_product_list(self, response):
        if 'dont-brand-filter' in response.meta:
            data = self.scraper.scrape_search_results_page(response, amazon_direct=self.amazon_direct)
            self.log("[[TESTING]] Found {} products for brand {}".format(data['results_count'], response.meta['brand']))
            for r in super(GuitarGuitarAmazonCoUkBaseSpider, self).parse_product_list(response):
                yield r
        else:
            for brand in self.brands:
                new_url = filter_by_brand(response.url, brand)
                if self.amazon_direct:
                    new_url = AmazonUrlCreator.filter_by_amazon_direct(self.domain, new_url)
                new_meta = safe_copy_meta(response.meta)
                new_meta['dont-brand-filter'] = True
                new_meta['brand'] = brand
                request = response.request.replace(url=new_url, meta=new_meta)

                yield request


class GuitarGuitarAmazonCoUkDirect(GuitarGuitarAmazonCoUkBaseSpider):
    name = 'guitarguitar_amazon.co.uk_direct'
    amazon_direct = True
