import re
import logging
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MachinemartCoUkSpider(BaseSpider):
    name = 'machinemart.co.uk'
    allowed_domains = ['machinemart.co.uk']
    start_urls = ('http://www.machinemart.co.uk',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="LHSNavigationMenu"]//dt[@class="category"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select(u'//meta[@http-equiv="Refresh"]/@content'):
            redirect = hxs.select(u'substring-after(//meta[@http-equiv="Refresh"]/@content, "URL=")').extract()
            url = urljoin_rfc(get_base_url(response), redirect[0])
            yield Request(url, callback=self.parse_product)

        for url in hxs.select(u'//div[starts-with(@id,"cellBubble")]//div[@class="brwPic"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//div[@class="search_result"]/div/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//div[@id="search-paging-inner"]/div/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1[1]/text()')
        price = ''.join(hxs.select(u'//div/span[position()=2 and contains(text(),"VAT") and contains(text(),"ex.")]/../span[1]//text()').extract())
        product_loader.add_value('price', extract_price(price))

        product_loader.add_xpath('sku', u'substring-after(//div[contains(text(),"Product Code:")]/text(), ":")')
        product_loader.add_xpath('category', u'//span[@class="breadcrumblink" and position()=3]/a/text()')

        img = hxs.select(u'//a[starts-with(@id,"img") and contains(@class,"mainImageParent")]/@href').extract()
        if not img:
            img = hxs.select(u'//div[contains(@class,"proPicHolder")]/a/img/@src').extract()
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        js = ''.join(hxs.select(u'//script/text()').extract())
        brand = re.search(u's.prop3=Trim\("(.+)"\);', js)
        if brand:
            product_loader.add_value('brand', brand.group(1))
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()

        if not product['price'] and not product['sku']:
            rows = hxs.select(u'//table/tbody/tr[@id="rangeHeader"]/../tr[position()!=1 and position()!=last()]')
            for i, row in enumerate(rows):
                if row.select(u'./td[2]/a/@href'):
                    # Comparison table with links to products
                    break

                p = Product(product)
                p['name'] = p['name'] + ' ' + row.select(u'../tr[1]//table//tr[%d]/td/div/text()' % (i + 2)).extract()[0]
                p['sku'] = row.select(u'./td[2]/text()').extract()[0]
#p['price'] = extract_price(row.select(u'./td/div[@id="priceExcVAT1"]/text()').extract()[0])
                p['price'] = extract_price(row.select(u'./td/div/div[2]/text()').extract()[0])
                yield p
        else:            
            yield product
