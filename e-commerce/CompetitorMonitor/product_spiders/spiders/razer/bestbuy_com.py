from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from scrapy.utils.url import url_query_parameter


class RazerBestbuySpider(BaseSpider):
    name = 'razer-bestbuy.com'
    allowed_domains = ['bestbuy.com']
    products = [{'url': 'http://www.bestbuy.com/site/razer-deathadder-chroma-optical-gaming-mouse-black/8501032.p?id=1219340874786&skuId=8501032',
                 'sku': 'RZ01-01210100-R3U1', 'category': 'Mice'},
                {'url': 'http://www.bestbuy.com/site/razer-naga-expert-mmo-gaming-mouse-black/1653812.p?id=1219058303220&skuId=1653812',
                 'sku': 'RZ01-01040100-R3U1', 'category': 'Mice'},
                {'url': 'http://www.bestbuy.com/site/razer-blackwidow-chroma-rgb-mechanical-gaming-keyboard/8501005.p?id=1219340875088&skuId=8501005',
                 'sku': 'RZ03-01220200-R3U1', 'category': 'Keyboards'},
                {'url': 'http://www.bestbuy.com/site/razer-blackwidow-ultimate-elite-mechanical-gaming-keyboard/4988007.p?id=1219106633128&skuId=4988007',
                 'sku': 'RZ03-00384600-R3U1', 'category': 'Keyboards'},
                {'url': 'http://www.bestbuy.com/site/razer-kraken-pro-analog-gaming-headset/6899651.p?id=1218811915148&skuId=6899651',
                 'sku': 'RZ04-00870100-R3U1', 'category': 'Audio'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        name = hxs.select('//*[@id="sku-title"]/h1/text()').extract()[0]
        image_url = hxs.select('//*[@id="postcard-thumbnail"]//img[@itemprop="image"]/@src').extract()
        identifier = url_query_parameter(response.url, 'id')
        price = hxs.select('//*[@id="priceblock-wrapper-wrapper"]//div[@class="item-price"]/text()').extract()[0]
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