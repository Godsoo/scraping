import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class RazerNeweggSpider(BaseSpider):
    retry_urls = {}
    name = 'razer-newegg.com'
    allowed_domains = ['newegg.com']
    products = [{'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16826153168',
                 'sku': 'RZ01-01210100-R3U1', 'category': 'Mice'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16826153125',
                 'sku': 'RZ01-01040100-R3U1', 'category': 'Mice'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16823114051',
                 'sku': 'RZ03-01220200-R3U1', 'category': 'Keyboards'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16823114038',
                 'sku': 'RZ03-00384600-R3U1', 'category': 'Keyboards'},
                {'url': 'http://www.newegg.com/Product/Product.aspx?Item=N82E16826153111',
                 'sku': 'RZ04-00870100-R3U1', 'category': 'Audio'}]

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
        loader.add_value('brand', 'Razer')
        loader.add_value('sku', meta['product']['sku'])
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        if image_url:
            loader.add_value('image_url', image_url[0])
        yield loader.load_item()