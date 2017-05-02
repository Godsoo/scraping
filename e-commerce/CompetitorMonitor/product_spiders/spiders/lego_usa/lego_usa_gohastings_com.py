import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class JetSpider(BaseSpider):
    name = 'lego_usa_gohastings_com'
    allowed_domains = ['gohastings.com']
    start_urls = ('https://www.gohastings.com/catalog/search_all.cmd?Nao=&keywords=lego&Ntk=Keyword&condition=2470&department=AllSearch&N=0+2470&departmentName=AllSearch&Ntt=lego&isViewAll=true&search=true&form_state=siteSearchForm&y=5&x=38',)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[@class="next-link"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        for url in hxs.select('//div[@class="product-item fl"]/h4/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        
    @staticmethod
    def parse_product( response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//input[@name="sku"]/@value')
        loader.add_xpath('name', '//div[attribute::id="cat-product-detail-info"]/h1[1]/text()')
        loader.add_value('brand', 'Lego')
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//*[@id="cat-prod-det-reg-price"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', '//*[@id="cat-product-details-sale-price"]/span/text()')
            if not loader.get_output_value('price'):
                return
        image_url = hxs.select('//div[attribute::id="cat-product-detail-img"]/div[1]/a[1]/img[1]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        for category in hxs.select('//div[@id="cat-product-detail"]/div[@id="bc"]/div[@class="fl"]/a/text()')[1:].extract():
            loader.add_value('category', category)
        yield loader.load_item()
