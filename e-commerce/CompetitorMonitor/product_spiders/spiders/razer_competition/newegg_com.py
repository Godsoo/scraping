import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class RazerCompNeweggSpider(BaseSpider):
    retry_urls = {}
    name = 'razer_competition-newegg.com'
    allowed_domains = ['newegg.com']
    products = [{'url': 'http://www.newegg.com/Product/Product.aspx?Item=9SIA24G28N4858',
                 'sku': '910-003533', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16826104674',
                 'sku': '910-002864', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=9SIA0AJ2CS7944',
                 'sku': 'CH-9000011-NA', 'category': 'Keyboards', 'brand': 'Corsair'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16823126299',
                 'sku': '920-003887', 'category': 'Keyboards', 'brand': 'Logitech'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16826104399',
                 'sku': '981-000257', 'category': 'Audio', 'brand': 'Logitech'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):

        # random redirect issue workaround
        if 'redirect_urls' in response.meta:
            url = response.meta['redirect_urls'][0]
            rc = self.retry_urls.get(url, 0)
            rc += 1
            if rc > 30:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                self.retry_urls[url] = rc
                yield Request(url, dont_filter=True, callback=self.parse,
                              meta=response.meta)
            return
        # end of redirects workaround

        hxs = HtmlXPathSelector(response)
        meta = response.meta
        name = hxs.select('//div[@class="grpArticle"]/div[@class="grpDesc boxConstraint"]/div/h1/span[@itemprop="name"]/text()').extract()[0]
        image_url = hxs.select('//a[@id="A2"]/span/img[contains(@src, "http://")]/@src').extract()
        identifier = re.findall(r'Item=([0-9a-zA-Z\-]+)', response.url)[0]
        price = re.findall(r"product_sale_price:\['([0-9.]+)'\]", response.body)[0]
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('category', meta['product']['category'])
        loader.add_value('brand', meta['product']['brand'])
        loader.add_value('sku', meta['product']['sku'])
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        if image_url:
            loader.add_value('image_url', image_url[0])
        yield loader.load_item()