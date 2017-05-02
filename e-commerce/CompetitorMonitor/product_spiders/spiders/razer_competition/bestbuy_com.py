from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from scrapy.utils.url import url_query_parameter


class RazerCompBestbuySpider(BaseSpider):
    name = 'razer_competition-bestbuy.com'
    allowed_domains = ['bestbuy.com']
    products = [{'url': 'http://www.bestbuy.com/site/logitech-g100s-optical-gaming-mouse-black/8785559.p?id=1218893507276&skuId=8785559',
                 'sku': '910-003533', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.bestbuy.com/site/logitech-g600-mmo-gaming-mouse/5608091.p?id=1218672047470&skuId=5608091',
                 'sku': '910-002864', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.bestbuy.com/site/corsair-vengeance-gaming-keyboard-black/1311833172.p?id=mp1311833172&skuId=1311833172',
                 'sku': 'CH-9000011-NA', 'category': 'Keyboards', 'brand': 'Corsair'},
                {'url': 'http://www.bestbuy.com/site/logitech-g710-mechanical-gaming-keyboard/6819135.p?id=1218808243010&skuId=6819135',
                 'sku': '920-003887', 'category': 'Keyboards', 'brand': 'Logitech'},
                {'url': 'http://www.bestbuy.com/site/logitech-g930-wireless-gaming-headset/1388362.p?id=1218255234461&skuId=1388362',
                 'sku': '981-000257', 'category': 'Audio', 'brand': 'Logitech'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        name = hxs.select('//*[@id="sku-title"]/h1/text()').extract()
        if not name:
            return
        name = name[0]
        image_url = hxs.select('//*[@id="postcard-thumbnail"]//img[@itemprop="image"]/@src').extract()
        identifier = url_query_parameter(response.url, 'id')
        price = hxs.select('//*[@id="priceblock-wrapper-wrapper"]//div[@class="item-price"]/text()').extract()[0]
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