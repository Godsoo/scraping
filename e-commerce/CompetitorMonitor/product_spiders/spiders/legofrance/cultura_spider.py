import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class CulturaSpider(BaseSpider):
    name = 'legofrance-cultura.com'
    allowed_domains = ['cultura.com']

    re_sku = re.compile('(\d+) *$')

    products = {}
    
    def start_requests(self):
        yield(Request('http://www.cultura.com/lego-reg.html'))
        yield(Request('http://www.cultura.com/jouets-et-activites-creatives/par-age-138.html', callback=self.parse_other_categories))
        yield(Request('http://www.cultura.com/catalogsearch/result/index/?q=lego+%27+%27', callback=self.parse_products))

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        lego_categories = hxs.select('//div[@id="category-left-menu"]//a/@href').extract()
        for category in lego_categories:
            yield Request(category, callback=self.parse_products)

    def parse_other_categories(self, response):
        hxs = HtmlXPathSelector(response)
        lego_categories = hxs.select('//a[@title="Lego"]/@href').extract()
        for category in lego_categories:
            yield Request(category, callback=self.parse_products)
            
    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//ul[@class="products-grid clearfix"]/li')
        category = hxs.select('//div[@id="breadcrumbs"]/ul/li[last()]/strong/text()').extract()
        for product in products:
            name = product.select('.//*[@class="product-name"]/a/@title').extract()
            if not name:
                continue
            name = name.pop()
            url = product.select('.//*[@class="product-name"]/a/@href').extract()[0]
            category = product.select('.//div[@class="label-main-category"]/a/span/text()').extract() or category
            image_url = product.select('div/a[@class="product-image"]/img/@src').extract()[0]
            identifier = self.re_sku.findall(name)
            sku = identifier
            if not identifier:
                identifier = url.split('-')[-1].split('.html')[0]
            stock = product.select(".//span[contains(@class,'in-stock')]").extract()
            stock = 1 if stock else 0

            l = ProductLoader(item=Product(), selector=product)
            l.add_value('identifier', identifier)
            l.add_value('name', name)
            l.add_value('category', category)
            l.add_value('brand', 'LEGO')
            l.add_value('sku', sku)
            l.add_value('url', url)
            l.add_value('stock', stock)

            price = product.select('div/div/span/span[@class="price"]/text()').extract()
            if price:
                price = price[0].replace(',', '.')
            else:
                price = product.select('div/div/p/span[@class="price"]/text()').extract()
                if price:
                    price = price[0].replace(',', '.')
                else:
                    price = '0.0'
            l.add_value('price', price)
            l.add_value('image_url', image_url)
            p = l.load_item()
            if p['identifier'] in self.products:
                p['name'] = self.products[p['identifier']]
            else:
                self.products[p['identifier']] = p['name']
            yield p

        next_p = hxs.select('//a[@class="next"]/@href').extract()
        if next_p:
            yield Request(next_p[0], callback=self.parse_products)
