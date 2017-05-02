# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class ThebodyshopSpider(BaseSpider):
    name = u'thebodyshop-thebodyshop.co.uk'
    allowed_domains = ['thebodyshop.co.uk']
    start_urls = [
        'http://www.thebodyshop.co.uk/shop-by-range/shea/shea-body-butter.aspx',
        'http://www.thebodyshop.co.uk/shop-by-range/hemp/hemp-hand-protector.aspx',
        'http://www.thebodyshop.co.uk/bath-body-care/shower-gels-shower-creams/strawberry-shower-gel.aspx',
        'http://www.thebodyshop.co.uk/shop-by-range/white-musk/white-musk-eau-de-toilette.aspx',
        'http://www.thebodyshop.co.uk/fragrance/view-all-fragrance/indian-night-jasmine-eau-de-toilette.aspx',
        'http://www.thebodyshop.co.uk/make-up/lips/colour-crush-lipstick.aspx',
        'http://www.thebodyshop.co.uk/make-up/face/all-in-one-bb-cream.aspx',
        'http://www.thebodyshop.co.uk/shop-by-range/vitamin-e/vitamin-e-moisture-cream.aspx',
        'http://www.thebodyshop.co.uk/shop-by-range/nutriganics-skin-care/drops-of-youth-concentrate.aspx',
        'http://www.thebodyshop.co.uk/mens/skincare/for-men-maca-root-energetic-face-protector.aspx'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = hxs.select('//*[@id="breadcrumb_product"]//a/text()').extract()[1:]
        product_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
        product_price = hxs.select('//p[@itemprop="price"]/text()').extract()[0]

        options = hxs.select('//*[@id="main-form"]/div[2]/select/option')
        for option in options:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            option_name = option.select('./text()').extract()[0]
            if response.url == 'http://www.thebodyshop.co.uk/shop-by-range/hemp/hemp-hand-protector.aspx':
                if '100ml' not in option_name:
                    continue
            elif response.url == 'http://www.thebodyshop.co.uk/bath-body-care/shower-gels-shower-creams/strawberry-shower-gel.aspx':
                if '250ml' not in option_name:
                    continue
            elif response.url == 'http://www.thebodyshop.co.uk/shop-by-range/white-musk/white-musk-eau-de-toilette.aspx':
                if '60ml' not in option_name:
                    continue
            elif response.url == 'http://www.thebodyshop.co.uk/shop-by-range/nutriganics-skin-care/drops-of-youth-concentrate.aspx':
                if '30ml' not in option_name:
                    continue
            elif response.url == 'http://www.thebodyshop.co.uk/shop-by-range/shea/shea-body-butter.aspx':
                if '200ml' not in option_name:
                    continue

            option_data = option.select('./@value').extract()[0].replace(u'\xa3', '')
            option_data = option_data.split('#')
            identifier = option_data[4]
            if len(option_data) > 5:
                price = option_data[-1]
            else:
                price = product_price
            price = extract_price(price)
            product_loader.add_value('price', price)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('name', product_name + ' ' + option_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('sku', identifier)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            if price < 25:
                product_loader.add_value('shipping_cost', 2.49)
            product = product_loader.load_item()
            yield product
            if response.url in ('http://www.thebodyshop.co.uk/make-up/face/all-in-one-bb-cream.aspx',
                                'http://www.thebodyshop.co.uk/make-up/lips/colour-crush-lipstick.aspx'):
                break
