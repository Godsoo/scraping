# -*- coding: utf-8 -*-
import re
import json

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from scrapy import log

from scrapy.utils.url import add_or_replace_parameter


class ChainReactionCyclesComSpider(BaseSpider):
    name = 'newitts-chainreactioncycles.com'
    allowed_domains = ['chainreactioncycles.com', 'competitormonitor.com']
    start_urls = ('http://www.chainreactioncycles.com/',)


    def parse(self, response):
        base_url = get_base_url(response)

        change_loc_form = response.xpath('//div[@id="localepickerpage"]/form')
        action_url = urljoin_rfc(base_url, change_loc_form.select('./@action').extract()[0])
        input_vals = dict(zip(change_loc_form.select('.//input/@name').extract(),
                              change_loc_form.select('.//input/@value').extract()))
        params = {u'/atg/userprofiling/ProfileFormHandler.value.country': u'GB',
                  u'/atg/userprofiling/ProfileFormHandler.value.currency': u'GBP',
                  u'/atg/userprofiling/ProfileFormHandler.value.language': u'en',
                  u'Update': u'Update',
                  u'_D:Update': ''}
        input_vals.update(params)

        yield FormRequest(action_url,
                          formdata=input_vals,
                          callback=self.parse_currency,
                          dont_filter=True)

    def parse_currency(self, response):
        yield Request('http://www.chainreactioncycles.com/', callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@class="crcHeaderMegaMenuHolder"]//a/@href').extract()
        categories += response.xpath('//ul[@class="categories"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_products)

        products = response.xpath('//div[contains(@class, "products_details")]//li/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        pages = response.xpath('//div[@class="pagination"]/a/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_products)

    def parse_product(self, response):
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        name = ' '.join(map(lambda x:x.strip(), response.xpath('//h1//text()').extract())).strip()
        product_loader.add_value('name', name)
        product_loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        product_loader.add_xpath('identifier', '//input[@id="defaultSKUID"]/@value')
        category = response.xpath('//div[@class="breadcrumb"]/ul/li/a/text()').extract()[1:]
        product_loader.add_value('category', category)

        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            image_url = image_url[0].split('?$')[0]
            product_loader.add_value('image_url', image_url)

        options_values = response.xpath('//script[contains(text(), "var allVariants={")]/text()').re(r'var variantsAray=(\[.*\]);')
        if options_values:
            options_values = eval(options_values[0])
        options = response.xpath('//script[contains(text(), "var allVariants={")]/text()').re(r'allVariants={"variants":(\[.*\,])\}\;')
        if options:
            options = eval(options[0])

        option_images = {}
        media_json = re.findall("var mediaJSON='(.*)';if", response.body)
        if media_json and media_json[0]:
            images = json.loads(media_json[0])
            for image in images["imageList"]:
                sku = image.get('skuId', None)
                if sku:
                    option_image = response.xpath('//div[@data-value="'+image['colour']+'"]/img/@src').extract()
                    image_url = option_image[0] if option_image else ''
                    if option_image:
                        image_url = add_or_replace_parameter(option_image[0], 'wid', '500')
                        image_url = add_or_replace_parameter(image_url, 'hei', '500')
                        option_images[image['skuId']] = image_url
                    else:
                        option_images[image['skuId']] = ''

            initial_image = images['initialImage']['imageURL']
            product_loader.add_value('image_url', initial_image)

        product = product_loader.load_item()

        if options and options_values:
            for option in options:
                prod = Product(product)
                sku = option['skuId']
                if not sku:
                    log.msg(' >>>>> ERROR: NO IDENTIFIER' + response.url)
                    continue
                prod['identifier'] = sku
                prod['sku'] = sku
                prod['name'] = prod['name'].strip() + ' ' + ' '.join(option[k] for k in options_values if option[k] is not 'null').decode('utf-8')
                prod['price'] = extract_price(option['RP'])
                if option['isInStock'] != 'true':
                    prod['stock'] = 0
                if option_images and option_images.get(sku, ''):
                    prod['image_url'] = option_images.get(sku, '')
                yield prod
        else:
            if not product.get('sku'):
                log.msg(' >>>>> ERROR: NO IDENTIFIER' + response.url)
            else:
                yield product
