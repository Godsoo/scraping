import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


from scrapy.item import Item, Field


class YMeta(Item):
    Author = Field()

class TheworksSpider(BaseSpider):

    name = 'theworks'
    start_urls = ['http://www.theworks.co.uk/page/books']
    cookie_num = 0
    id_seen = []


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for link in hxs.select('//div[@class="landing-nav"]/ul/li/a/@href').extract():
            url = urljoin_rfc(base_url, link)
            self.cookie_num += 1
            yield Request(url, meta={'cookiejar':self.cookie_num}, callback=self.parse_products_list)


    def parse_products_list(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = hxs.select('//div[@class="landing-nav"]/ul/li/a/@href').extract()
        shop_all_button = hxs.select('//div[@class="landing-nav"]//a[contains(text(),"Shop All")]/@href').extract()

        if shop_all_button:
            url = urljoin_rfc(base_url, shop_all_button[0])
            yield Request(url, meta={'cookiejar':self.cookie_num},callback=self.parse_products_list)
        else:
            if links:
                for link in links:
                    url = urljoin_rfc(base_url, link)
                    self.cookie_num += 1
                    yield Request(url, meta={'cookiejar':self.cookie_num},callback=self.parse_products_list)
                return

        links = hxs.select('//div[@id="product-list"]/ol/li//h2/a/@href').extract()
        for link in links:
            url = urljoin_rfc(base_url, link)
            yield Request(url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_product)

        next_page = hxs.select('//ul[@data-component-name="pagination"]/li/a[text()="next"]/@href').extract()
        if next_page:
            yield Request(next_page[0], meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_products_list)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        r = re.findall(r'/(\d+)$', response.url) or response.xpath('//meta[@itemprop="sku"]/@content').extract()
        if r:
            loader.add_value('identifier', r[0].strip())
            loader.add_value('sku', r[0].strip())
        else:
            self.log('### No product ID at ' + response.url)
            return

        loader.add_xpath('name', '//h1[@itemprop="name"]/span/text()')
        
        try:
            product_price = response.css('.attr-price-now, .attr-price')[0].css('.integer, .decimal').xpath('text()').extract()
            price = ''.join(product_price).replace(',', '')
            if price.endswith('p'):
                price = '0.' + price
            price = extract_price(price)
        except IndexError:
            price = 0
        loader.add_value('price', price)

        product_stock = hxs.select('//div[@class="product-stock-status"]/span[@class="in-stock"]')
        if not product_stock:
            loader.add_value('stock', 0)

        product_image = response.xpath('//div[@class="product-image"]//img/@src').extract()
        if product_image:
            url = urljoin_rfc(base_url, product_image[0])
            loader.add_value('image_url', url)

        categories = hxs.select('//div[@class="breadcrumb"]/ol/li/a/text()').extract()
        if len(categories) > 1:
            for s in categories[1:]:
                loader.add_value('category', s.strip())

        if price < 20:
            loader.add_value('shipping_cost', '2.99')

        product = loader.load_item()

        author = hxs.select('//h2[@class="product-attr" and contains(text(),"Author")]/a/text()').extract()
        if author:
            metadata = YMeta()
            metadata['Author'] = author[0]
            product['metadata'] = metadata

        yield product
