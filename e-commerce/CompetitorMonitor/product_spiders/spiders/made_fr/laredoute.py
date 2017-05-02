# -*- coding: utf-8 -*-


"""
Name: made_fr-laredoute.fr
Account: Made FR
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4750
"""


import re
import json
import HTMLParser
from extruct.w3cmicrodata import MicrodataExtractor
from scrapy import Spider, Request
from product_spiders.utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class MadeLaredouteSpider(Spider):
    name = 'made_fr-laredoute.fr'
    allowed_domains = ['laredoute.fr']
    start_urls = [
        'http://www.laredoute.fr/pplp/100/cat-84100.aspx',
        'http://www.laredoute.fr/pplp/100/cat-75363.aspx',
    ]

    extra_brand_urls = [
        'http://www.laredoute.fr/brnd/achatdesign.aspx?brndid=achatdesign',
        'http://www.laredoute.fr/brnd/declikdeco.aspx?brndid=declikdeco',
    ]

    def __init__(self, *args, **kwargs):
        super(MadeLaredouteSpider, self).__init__(*args, **kwargs)

        self.html_parser = HTMLParser.HTMLParser()
        self.product_url = 'http://www.laredoute.fr/ppdp/prod-%(ProductId)s.aspx'

    def start_requests(self):
        for url in self.extra_brand_urls:
            yield Request(url, callback=self.parse_brand_page)

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        category_urls = map(response.urljoin,
                            response.xpath(u'//div[@class="divFilterTitle" and contains(text(), '
                                           u'"CATÉGORIES")]/following-sibling::div//a/@href')
                            .extract())
        subcat_urls = map(response.urljoin,
                          response.xpath('//ul[@class="level3"]/li/a/@href').re(r'.*cat-\d+\.aspx'))
        product_urls = map(response.urljoin,
                           response.xpath('//div[@id="plpListdivMain"]//article[@data-productid]//a/@href')
                           .extract())
        next_urls = map(response.urljoin, response.xpath('//li[@class="next"]/a/@href').extract())

        for url in category_urls:
            yield Request(url)

        for url in subcat_urls:
            yield Request(url)

        for url in next_urls:
            yield Request(url)

        for url in product_urls:
            yield Request(url, callback=self.parse_product)

    def parse_brand_sitemap(self, response):
        urls = re.findall(r'<loc>(http://www.laredoute.fr/brnd/.*)</loc>', response.body)
        for url in urls:
            yield Request(url, callback=self.parse_brand_page)

    def parse_brand_page(self, response):
        product_urls = map(response.urljoin, response.xpath('//div[@data-productid]/a/@href').extract())
        for url in product_urls:
            yield Request(url, callback=self.parse_product)

        next_urls = map(response.urljoin, set(response.xpath('//a[@id="aNext"]/@href').extract()))
        for url in next_urls:
            yield Request(url, callback=self.parse_brand_page)

    def parse_product(self, response):
        mde = MicrodataExtractor()
        try:
            micro_data = mde.extract(response.body)['items']
            gen_data = filter(lambda a: a['type'] == 'http://schema.org/Product',
                              micro_data)[0]['properties']
            categories = [c['properties']['title']
                          for c in filter(lambda d: d['type'] == 'http://data-vocabulary.org/Breadcrumb',
                                          micro_data)][1:]
        except:
            self.log('WARNING => Wrong product page in %s' % response.url)
            return

        main_name = gen_data['name']
        if isinstance(main_name, list):
            main_name = main_name[0]
        main_brand = gen_data.get('brand', '')
        if isinstance(main_brand, list):
            main_brand = main_brand[0]

        variants = response.xpath('//input[@name="ctl00$cphMain$ctl00$hidProductVariants"]/@value').extract()
        if variants:
            data = json.loads(self.html_parser.unescape(variants[0]))
            for d in data:
                for var in d['Variants']:
                    for size_data in var['Variants']:
                        color_name = size_data.get('Article', dict()).get('ColorName', '')
                        size_data = size_data['Article']
                        url = self.product_url % size_data
                        identifier = size_data['ItemOfferId']
                        name = main_name + ', ' + color_name + ', ' + size_data['FriendlySize']
                        price = size_data['WebInfo']['ArticlePriceDisplay']['FormattedSalePriceAfterWithCharges']
                        shipping_cost = size_data['FormattedDeliveryFee']
                        loader = ProductLoader(item=Product(), response=response)
                        loader.add_value('name', name)
                        loader.add_value('url', url)
                        loader.add_value('identifier', identifier)
                        loader.add_value('sku', size_data['ProductId'])
                        loader.add_value('price', extract_price_eu(price))
                        if shipping_cost:
                            loader.add_value('shipping_cost', extract_price_eu(shipping_cost))
                        loader.add_value('image_url', gen_data['image'][-1])
                        if size_data['AvailabilityCode'] != 'L':
                            loader.add_value('stock', 0)
                        loader.add_value('category', categories)
                        if main_brand:
                            loader.add_value('brand', main_brand)
                        yield loader.load_item()
        else:
            self.log('WARNING: Variants not found in => %s' % response.url)
