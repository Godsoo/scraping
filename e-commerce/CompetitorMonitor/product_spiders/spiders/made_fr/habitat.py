from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.utils import remove_punctuation_and_spaces
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader


class HabitatSpider(BaseSpider):
    name = 'habitat.fr'
    allowed_domains = ['habitat.fr']
    start_urls = ['http://www.habitat.fr/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//menu[@id="menu_container"]//a/@href').extract():
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_cat, meta={'dont_merge_cookies':True})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@class="product-list"]/div[not (contains(@class, "pagination"))]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        
        for url in hxs.select('//div[@class="product-list"]/div[contains(@class, "pagination")]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        
        try:
            identifier = hxs.select('//div[@id="product_description"]/@data-product_id').extract()[0]
        except IndexError:
            yield Request(response.url, dont_filter=True, callback=self.parse_cat)
            return
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//script/text()', re='"prdref","(.+)"')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()', re='.+')
        loader.add_xpath('name', '//div/text()', re='Couleur.*:(.+)')
        loader.add_xpath('category', '//nav[@id="breadcrumb"]//a[position()>1]/span/text()')
        price = ''.join(hxs.select('//div[@class="product_container"]//div[@class="product-price"]/span[@data-product_id="%s"]//text()' %identifier).extract())
        loader.add_value('price', ''.join(price.split()))
        loader.add_xpath('image_url', '//script/text()', re='"prdparam-image_url","(.+)"')
        if not hxs.select('//input[contains(@id, "addToCart")]'):
            loader.add_value('stock', '0')
        yield loader.load_item()
        
        siblings = hxs.select('//div[@id="slider_collection-container"]//a/@href').extract()
        siblings += hxs.select('//div[contains(@class, "siblings")]//a/@href').extract()
        for url in siblings:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
