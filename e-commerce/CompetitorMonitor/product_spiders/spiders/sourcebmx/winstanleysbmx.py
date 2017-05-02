from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price


class WinstanleysbmxSpider(BaseSpider):
    name = 'winstanleysbmx'
    allowed_domains = ['winstanleysbmx.com']
    start_urls = ('http://www.winstanleysbmx.com/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="left_nav"]//a[@class="links_left_nav subcat"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        url = hxs.select('//input[@name="next"]/@onclick').extract()
        if url:
            url = url[0].partition("href='")[2][:-1]
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)
        category_name = hxs.select('//*[@id="cat_hdr"]/tr/td[1]/b/text()').extract()
        if category_name:
            category_name = category_name[0]
        else:
            category_name = ''
        #products
        urls = hxs.select('//*[@id="catprods_tbl"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), meta={'category_name': category_name}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        image_url = hxs.select('//img[@style="cursor : hand;"]/@src').extract()
        category = response.meta.get('category_name')

        product_rows = hxs.select('//*[@id="item_Tbl"]//tr')

        first_row = True
        product_name = None
        for row in product_rows:
            name = ''.join(row.select('./td[1]//text()').extract()).strip()
            if name == 'Name:':
                if not first_row:
                    product_loader.add_value('name', product_name)
                    product_loader.add_value('shipping_cost', 3.99)
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('category', category)
                    if image_url:
                        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                    product = product_loader.load_item()
                    yield product
                first_row = False
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_name = ''.join(row.select('./td[2]//text()').extract()).strip()
            if name and name not in ('Name:', 'Price:', 'Product Code:', 'Availability:', 'Qty:'):
                product_name += ' - ' + ''.join(row.select('./td[2]//text()').extract()).strip()
            if name == 'Price:':
                price = row.select('./td[2]//text()').extract()[0]
                product_loader.add_value('price', extract_price(price))
            if name == 'Product Code:':
                sku = row.select('./td[2]//text()').extract()[0]
                product_loader.add_value('identifier', sku)
                product_loader.add_value('sku', sku)
            if name == 'Availability:':
                stock = row.select('./td[2]//text()').extract()[0]
                if 'In stock.' not in stock:
                    product_loader.add_value('stock', 0)
        if product_name:
            product_loader.add_value('name', product_name)
            product_loader.add_value('shipping_cost', 3.99)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product = product_loader.load_item()
            yield product