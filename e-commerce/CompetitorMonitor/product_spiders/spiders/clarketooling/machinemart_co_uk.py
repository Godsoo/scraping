import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MachinemartCoUkSpider(BaseSpider):
    name = 'clarketooling-machinemart.co.uk'
    allowed_domains = ['machinemart.co.uk']
    start_urls = ('http://www.machinemart.co.uk',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="MainMenu"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select(u'//meta[@http-equiv="Refresh"]/@content'):
            redirect = hxs.select(u'substring-after(//meta[@http-equiv="Refresh"]/@content, "URL=")').extract()
            url = urljoin_rfc(get_base_url(response), redirect[0])
            yield Request(url, callback=self.parse_product)

        for url in hxs.select('//div[@class="productCategory"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product_list)
            
        brands = hxs.select('//div[@class="toggleFilter"]/h3[text()="Brands"]/../following-sibling::div[@class="categoryDrop"]/a')
        brands += hxs.select('//div[@class="toggleFilter"]/h3[text()="Brands"]/../following-sibling::div[@class="categoryDrop"]/div[@class="facetListExtra"]/a')
        for brand in brands:
            name = brand.select('text()').extract()[0].strip()
            url = brand.select('@href').extract()
            if not url:
                continue
            url = urljoin_rfc(get_base_url(response), url[0])
            yield Request(url, callback=self.parse_brand, meta={'brand':name})
            
    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[contains(@class, "productView")]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for page in hxs.select('//div[@class="pagination"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), page)
            yield Request(url, callback=self.parse_brand, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        name = hxs.select(u'//h1[1]/text()').extract()[0]
        product_loader.add_value('name', name)
        price = hxs.select('//div[@class="lightBlue"]/strong/text()').extract() or hxs.select('//div[@class="darkBlue"]/strong/text()').extract()
        product_loader.add_value('price', price)

        product_loader.add_xpath('sku', '//input[@name="ProductSku"]/@value')
        product_loader.add_xpath('identifier', '//input[@name="ProductSku"]/@value')
        product_loader.add_xpath('category', '//div[contains(@class, "breadcrumbs")]/ul/li[position()=3]/a/text()')

        img = hxs.select('//div[@class="imageView"]/img/@src').extract()
        if not img:
            img = hxs.select(u'//div[contains(@class,"proPicHolder")]/a/img/@src').extract()
        try:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        except:
            pass

        product_loader.add_value('brand', response.meta['brand'])
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()

        if not product['price'] and not product['sku']:
            rows = hxs.select(u'//table/tbody/tr[@id="rangeHeader"]/../tr[position()!=1 and position()!=last()]')
            for i, row in enumerate(rows):
                if row.select(u'./td[2]/a/@href'):
                    # Comparison table with links to products
                    break

                try:
                    p = Product(product)
                    p['name'] = p['name'] + ' ' + row.select(u'../tr[1]//table//tr[%d]/td/div/text()' % (i + 2)).extract()[0]
                    p['sku'] = row.select(u'./td[@align="center"]/text()').extract()[0]
                    p['identifier'] = p['sku']
                    p['price'] = extract_price(row.select(u'./td/div/div[2]/text()').extract()[0])
                    if p['sku']:
                        yield p
                except:
                    pass
        else:
            yield product
