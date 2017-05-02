from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.url import url_query_parameter
from decimal import Decimal


class BauhausreeditionSpider(BaseSpider):
    name = 'voga_it-bauhausreedition.com'
    allowed_domains = ['bauhausreedition.com']
    start_urls = ['http://www.bauhausreedition.com/complementi-arredamento-arredo-design-bauhaus/interior-design-mobili-complementi-arredo-bauhaus.asp',
                  'http://www.bauhausreedition.com/complementi-arredamento-arredo-design-bauhaus/mobili-designers-bauhaus.asp']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="block-01" or @class="block-02"]//h3[@class="prod"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="block-01" or @class="block-02"]//h3[@class="prod"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_name = ''.join(hxs.select('//*[@id="content"]/h2[1]//text()').extract()).strip()
        product_name = product_name.replace(u'\xa0', ' ')
        sku = hxs.select('//li[@class="codice"]/span/text()').extract()
        sku = sku[0] if sku else ''

        img = hxs.select('//div[@class="img-big"]//img/@src').extract()
        category = ''.join(hxs.select('//*[@id="content"]//p[@class="briciola"]//text()').extract()).strip()
        category = category.split(' / ')[2:]

        for option in hxs.select('//ul[@class="buy"]'):
            loader = ProductLoader(item=Product(), selector=hxs)
            name = option.select('./li[@class="prezzo"]//text()').extract()[0].replace(':', '').strip()
            if name != '':
                name = ' - ' + name
            price = option.select('./li[@class="prezzo"]//text()').extract()[1].strip().replace(u'\u20ac', '')
            price = extract_price_eu(price) * Decimal('1.22')
            product_identifier = option.select('./li[@class="acquista"]/a/@href').extract()[0]
            product_identifier = url_query_parameter(urljoin_rfc(get_base_url(response), product_identifier), 'id_opzione')

            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name + name)
            loader.add_value('price', price)
            loader.add_xpath('brand', '//p[@class="desc-prod"]/a/text()')
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
            loader.add_value('category', category)
            yield loader.load_item()
