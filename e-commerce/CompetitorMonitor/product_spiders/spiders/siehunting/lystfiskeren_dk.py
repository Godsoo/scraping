import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class LystfiskerenDkSpider(BaseSpider):
    name = 'lystfiskeren.dk'
    allowed_domains = ['lystfiskeren.dk']
    start_urls = (
        'http://www.lystfiskeren.dk',
        'http://www.lystfiskeren.dk/brands',
    )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        items = hxs.select(u'//div[@class="tabs-carousel"]/ul[@class="products-grid"]/li')
        items += hxs.select(u'//li[contains(@class,"hproduct item")]')
        for item in items:
            url = item.select(u'.//h2[@class="product-name"]/a/@href').extract()
            if not url:
                url = item.select(u'.//h2/a/@href').extract()
            url = urljoin_rfc(get_base_url(response), url[0])
            yield Request(url, callback=self.parse_product)

        subcategories = hxs.select(u'.//div[@id="custommenu"]//a/@href').extract()
        subcategories += hxs.select(u'.//div[@class="shopby-list"]//div[@class="content"]//dl//a/@href').extract()
        for subcategory in subcategories:
            url = urljoin_rfc(get_base_url(response), subcategory)
            if 'limit=all' not in url:
                url = url + '?limit=all'
            yield Request(url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url
        name = hxs.select('//div[@class="product-essential"]//div[@class="product-name"]/h1/text()').extract()[0]
        sku = ''.join(hxs.select(u'//div[@class="product-essential"]//div[@class="product-name"]//span[@class="sku"]/text()').extract()).replace('Vare:', '').strip()
        # price = hxs.select(u'.//div[@class="product-shop"]//span[@class="price"]/text()[last()]').extract()[-1]
        # price = price.strip().replace('.', '').replace(',', '.')
        price = hxs.select("//div[@class='product-essential']//span[@class='regular-price']/span[@class='price']//text()").extract()
        price += hxs.select("//div[@class='product-essential']//p[@class='special-price']/span[@class='price']//text()").extract()
        price = price[0]
        price = price.strip().replace('.', '').replace(',', '.')
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('url', url)
        loader.add_value('price', price)
        yield loader.load_item()
        opthtml = hxs.select('//div[@class="product-essential"]//div[@id="product-options-wrapper"]')
        if opthtml:
            m = re.search('Product.Config\((.+?)\);', opthtml.extract()[0])
            if m:
                m = re.search('rrelse","options":(.+?)]}],', m.group(1))
                if m:
                    sizes = re.findall('label":"([^"]+)"', m.group(1))
                    for sz in sizes:
                        loader = ProductLoader(item=Product(), selector=hxs)
                        loader.add_value('name', name + ' - ' + sz)
                        loader.add_value('sku', sku + '-' + sz)
                        loader.add_value('identifier', sku + '-' + sz.replace(' ', ''))
                        loader.add_value('url', url)
                        loader.add_value('price', price)
                        yield loader.load_item()
