from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import itertools
import re


class EwigsnaSpider(BaseSpider):
    name = 'ewigsna.com'
    allowed_domains = ['ewigsna.com']
    start_urls = ['http://www.ewigsna.com/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="custommenu"]//a/@href').extract():
            if url != 'javascript:void(0);':
                yield Request(urljoin_rfc(base_url, url + '?limit=240'), callback=self.parse_category)
        for url in hxs.select('//*[@id="custommenu"]//div[@class="parentMenu"]/a/@rel').extract():
            yield Request(urljoin_rfc(base_url, url + '?limit=240'), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = hxs.select('//div[@class="web_map_nav"]//strong/text()').extract()[0].strip()
        for url in hxs.select('//div[@class="web_pro_list_content"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)

        product_name = ''.join(hxs.select('//div[@class="web_pro_detail_title"]/h1/text()').extract()).strip()
        identifier = hxs.select('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()[0]
        sku = hxs.select('//span[@class="sku_block"]/text()').extract()[0].strip()
        img = hxs.select('//div[@class="pro_img"]//img/@src').extract()
        category = response.meta.get('category')
        price = hxs.select('//span[@id="product-price-{}"]/text()'.format(identifier)).extract()
        if not price:
            price = hxs.select('//*[@id="product_addtocart_form"]//span[@class="price"]').extract()
        price = extract_price(price[0])

        sizes = hxs.select('//select[@class=" product-custom-option sizecc"]/option')
        if len(sizes) > 1:
            size_variations = []
            for size in sizes[1:]:
                size_id = size.select('./@value').extract()[0]
                size_name = size.select('./text()').extract()[0]
                size_variations.append([size_id, size_name])
            colors = hxs.select('//div[@id="colour_options_hidden"]//img')
            color_variations = []
            for color in colors:
                color_id = color.select('./@valueid').extract()[0]
                color_name = color.select('./@val').extract()[0]
                color_variations.append([color_id, color_name])
            options = itertools.product(size_variations, color_variations)

            for option in options:
                product_identifier = identifier + '_'+option[0][0] + '_' + option[1][0]
                size_name = option[0][1]
                result = re.findall(r"(?sim)\( \+\$([\d.]+)\)", size_name)
                if result:
                    add_price = extract_price(result[0])
                    size_name = size_name.replace('( +${})', '').strip()
                else:
                    add_price = extract_price('0')
                name = product_name + ' ' + size_name + ' ' + option[1][1]
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price + add_price)
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                loader.add_value('category', category)
                yield loader.load_item()
        else:
            colors = hxs.select('//div[@id="colour_options_hidden"]//img')
            if colors:
                for color in colors:
                    color_id = color.select('./@valueid').extract()[0]
                    color_name = color.select('./@val').extract()[0]
                    product_identifier = identifier + color_id
                    name = product_name + ' ' + color_name
                    loader = ProductLoader(item=Product(), selector=hxs)
                    loader.add_value('identifier', product_identifier)
                    loader.add_value('sku', sku)
                    loader.add_value('url', response.url)
                    loader.add_value('name', name)
                    loader.add_value('price', price)
                    if img:
                        loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                    loader.add_value('category', category)
                    yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', product_name)
                loader.add_value('price', price)
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                loader.add_value('category', category)
                yield loader.load_item()

