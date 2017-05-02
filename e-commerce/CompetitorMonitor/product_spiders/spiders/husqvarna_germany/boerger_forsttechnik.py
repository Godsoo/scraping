from copy import deepcopy

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from scrapy import log

from urlparse import urljoin


class BoergerForsttechnikSpider(CrawlSpider):
    name = 'husqvarna_germany-boerger-forsttechnik.de'
    allowed_domains = ['boerger-forsttechnik.de']
    start_urls = ('http://www.boerger-forsttechnik.de',)
    
    categories = LinkExtractor(restrict_css='nav.navbar-categories-left')
    pages = LinkExtractor(restrict_css='ul.pagination')
    products = LinkExtractor(restrict_css='div.product-container div.title')
    
    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))

    def __parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//div[contains(@class, "cat_link_container")]/a/@href').extract()
        for url in categories:
            url = urljoin(base_url, url) + '?listing_sort=price_asc&listing_count=384'
            yield Request(url)

        subcategories = response.xpath('//ul[@class="sub_categories_listing_body"]//a/@href').extract()
        for url in subcategories:
            url = urljoin(base_url, url) + '?listing_sort=price_asc&listing_count=384'
            yield Request(url)

        next_page = hxs.select('//a[contains(text(),"[>>]")]/@href').extract()
        if next_page:
            yield Request(urljoin(base_url, next_page[0]))

        products = hxs.select('//a[@class="product_link"]/@href').extract()
        for url in products:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = response.xpath('//input[@id="products-id"]/@value').extract_first()
        loader.add_value('identifier', identifier)

        sku = response.xpath('//span[@itemprop="model"]/text()').extract_first()
        loader.add_value('sku', sku)

        name = response.xpath('//h2/span[@itemprop="name"]/text()').extract_first() or response.xpath('//h1/text()').extract_first()
        loader.add_value('name', name)

        loader.add_value('url', response.url)
        
        price = response.xpath('//span[@itemprop="price"]/@content').extract_first()
        if price:
            price = price.replace('.', ',')
        else:
            price = response.xpath('//span[@itemprop="price"]/text()').extract_first() or response.css('div.current-price-container').xpath('br/following::text()').extract_first() or response.css('div.current-price-container ::text').extract_first() or 0
        loader.add_value('price', price)

        category = hxs.select('//div[@id="breadcrumb_navi"]/span/a/span/text()').extract()
        category = category[1:-1] if len(category) > 2 else ''
        loader.add_value('category', category)

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))

        item = loader.load_item()
    
        options = response.css('fieldset.attributes div div label')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + option.xpath('.//input/@value').extract_first()
                option_name = ' '.join(option.xpath('text()').extract()).strip()
                if '(' in option_name:
                    price = extract_price(option_name.split('(')[-1])
                    option_name = option_name.split('(')[0].strip()
                    option_item['price'] += price
                option_item['name'] += ' ' + option_name
                yield option_item
        else:
            yield item
       
