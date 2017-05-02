"""
Spider copy from the one in SpecSavers NO
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5012
"""
import re

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader


class Synsam(CrawlSpider):
    name = 'specsavers_sw-synsam.se'
    allowed_domains = ['synsam.se']
    start_urls = ['https://www.synsam.se/kontaktlinser']

    products = LinkExtractor(restrict_css='.product-list-products')
    pagination = LinkExtractor(restrict_css='.paging-navigation',
                               process_value=lambda x: 'https://www.synsam.se/ArticleFilter/CL/?'
                                                       'sort=price&sortOrder=asc&from=' + re.search('fr=(.*)&?', x).group(1))
    rules = (
        Rule(products, callback='parse_product'),
        Rule(pagination)
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@id="articleId"]/@value').extract_first() or response.xpath('//input[@id="skuId"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        breadcrumbs = response.css('.breadcrumbs a::text').extract()[1:]
        loader.add_value('name', breadcrumbs.pop())
        loader.add_value('category', breadcrumbs[-3:])
        loader.add_xpath('price', '//h3[@itemprop="price"]/@content')
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_css('brand', '.product-hero-brand img::attr(alt)')
        if loader.get_output_value('price') < 1000:
            loader.add_value('shipping_cost', 49)
        yield loader.load_item()
