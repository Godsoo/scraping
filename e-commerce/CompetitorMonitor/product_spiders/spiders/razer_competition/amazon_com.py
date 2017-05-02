from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
import re
import json


class RazerCompAmazonComSpider(BaseSpider):
    name = 'razer_competition-amazon.com'
    allowed_domains = ['amazon.com']
    products = [{'url': 'http://www.amazon.com/Logitech-G100s-Optical-Gaming-Mouse/dp/B00BCEK2LK/ref=sr_1_1?ie=UTF8&qid=1419328799&sr=8-1&keywords=910-003533',
                 'sku': '910-003533', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.amazon.com/Logitech-G600-Gaming-Mouse-Black/dp/B0086UK7IQ/ref=sr_1_1?ie=UTF8&qid=1419328827&sr=8-1&keywords=910-002864',
                 'sku': '910-002864', 'category': 'Mice', 'brand': 'Logitech'},
                {'url': 'http://www.amazon.com/Corsair-Vengeance-Mechanical-Gaming-Keyboard/dp/B00CD1FC6G/ref=sr_1_1?ie=UTF8&qid=1419328838&sr=8-1&keywords=CH-9000011-NA',
                 'sku': 'CH-9000011-NA', 'category': 'Keyboards', 'brand': 'Corsair'},
                {'url': 'http://www.amazon.com/Logitech-Mechanical-Keyboard-Tactile-High-Speed/dp/B009C98NPY/ref=sr_1_1?ie=UTF8&qid=1419328850&sr=8-1&keywords=920-003887',
                 'sku': '920-003887', 'category': 'Keyboards', 'brand': 'Logitech'},
                {'url': 'http://www.amazon.com/Logitech-Wireless-Gaming-Headset-Surround/dp/B003VANOFY/ref=sr_1_1?ie=UTF8&qid=1419328860&sr=8-1&keywords=981-000257',
                 'sku': '981-000257', 'category': 'Audio', 'brand': 'Logitech'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        name = hxs.select("//h1[@class='parseasinTitle']/span/span//text()").extract()
        if not name:
            name = hxs.select("//span[@id='productTitle']/text()").extract()
        if not name:
            name = hxs.select("//h1[contains(@class, 'parseasinTitle')]/span/text()").extract()
        name = name[0]

        asin = re.findall(r'current_asin\":\"([^,]*)\",',
                          response.body_as_unicode().replace('\n', ''))
        if not asin:
            asin = hxs.select("//input[@id='ASIN']/@value").extract()
        if not asin:
            asin = hxs.select("//input[@name='ASIN']/@value").extract()
        if not asin:
            asin = hxs.select("//input[@name='ASIN.0']/@value").extract()
        if not asin:
            asin = hxs.select("//li[b[contains(text(), 'ASIN:')]]/text()").extract()
        asin = asin[0].strip()

        price = None
        if not price:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
        if not price:
            price = hxs.select('//span[@id="priceblock_saleprice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="actualPriceValue"]/*[@class="priceLarge"]/text()').extract()
        if not price:
            price = hxs.select('//*[@class="priceLarge"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = None

        image_url = hxs.select("//img[@id='main-image']/@src").extract()
        if not image_url:
            image_url = hxs.select("//img[@id='landingImage']/@src").extract()
        image_url = image_url[0] if image_url else None

        if image_url is not None and len(image_url) > 1024:
            image_url = hxs.select('//img[@id="main-image-nonjs"]/@src').extract()
            if not image_url:
                image_data_json = hxs.select("//img[@id='landingImage']/@data-a-dynamic-image").extract()
                if image_data_json:
                    image_data = json.loads(image_data_json[0])
                    try:
                        image_url = image_data.keys()[0]
                    except (AttributeError, IndexError):
                        image_url = ''

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', asin)
        loader.add_value('name', name)
        loader.add_value('category', meta['product']['category'])
        loader.add_value('brand', meta['product']['brand'])
        loader.add_value('sku', meta['product']['sku'])
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        if image_url:
            loader.add_value('image_url', image_url)
        yield loader.load_item()