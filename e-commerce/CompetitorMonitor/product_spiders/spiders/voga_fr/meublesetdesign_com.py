from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BauhausreeditionSpider(BaseSpider):
    name = 'voga_fr-meublesetdesign.com'
    allowed_domains = ['meublesetdesign.com']
    start_urls = ['http://www.meublesetdesign.com/search?q=']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//figure[@class="produit-image"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = hxs.select("//div[@id='fiche-produit-description-inspiration']/text()").extract()
        brand = brand[0].split(' par')[1].strip() if brand else ''

        product_name = ''.join(hxs.select('//*[@id="fiche-produit-description-titre1"]/text()').extract()).strip()
        img = hxs.select('//*[@id="product-main-image"]/@src').extract()
        category = hxs.select('//ul[@class="breadcrumb"]//span[@itemprop="title"]/text()').extract()[:-1]
        product_identifier = hxs.select('//input[@name="product_id"]/@value').extract()[0]

        for option in hxs.select('//*[@id="product-option-selector"]//option'):
            loader = ProductLoader(item=Product(), selector=hxs)
            name = option.select('./text()').extract()[0].strip()
            name = ' '.join(s.strip() for s in name.split('\n'))
            name = name.replace('(Hors stock)', '').strip()
            if name != '':
                name = product_name + ' - ' + name
            price = option.select('./@data-price').extract()[0].replace(u'\u20ac', '').strip()
            price = extract_price_eu(price)
            identifier = option.select('./@value').extract()[0]
            loader.add_value('identifier', product_identifier + '_' + identifier)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('price', price)
            stock = option.select('./@data-quantity').extract()[0]
            if stock == '0':
               loader.add_value('stock', 0)
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
            if price < 300:
                loader.add_value('shipping_cost', 19)
            loader.add_value('category', category)
            yield loader.load_item()
