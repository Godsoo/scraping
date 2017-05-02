import os
import re
import xlrd
import json
import itertools
import collections

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from onestopbedroomsitems import OneStopBedroomsMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class OneStopBedroomsSpider(BaseSpider):
    name = '1stopbedrooms-1stopbedrooms.com'
    allowed_domains = ['1stopbedrooms.com']

    start_urls = ('http://www.1stopbedrooms.com/',)

    def start_requests(self):
        urls = {}
        filename = os.path.join(HERE, '1stopbedrooms.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_name('Simple With Exact Match')

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row(rownum)
            url = row[9].value
            if url:
                urls[url] = row

        sh = wb.sheet_by_name('Simple with different SKU')

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row(rownum)
            url = row[9].value
            if url:
                urls[url] = row

        _urls = [row[3].value for url, row in urls.iteritems()]
        duplicate_urls = [url for url, count in collections.Counter(_urls).items() if count > 1]

        for url, row in urls.iteritems():
            # This site is set to automatch by URL, it set empty metadata for the duplicate URLs to avoid matching
            if url not in duplicate_urls:
                meta = {'coleman_sku': row[2].value,
                        'coleman_url': row[3].value}
            else:
                meta = {'coleman_sku': '',
                        'coleman_url': ''}

            yield Request(url, meta=meta)

    def parse(self, response):
        meta = response.meta

        name = response.xpath('//*[@itemprop="name"]/text()').extract()[0].strip()
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        categories = response.xpath('//li[span[contains(text(), "Collection")]]/div/a/text()').extract()
        categories = categories[0].strip() if categories else ''
        brand = response.xpath('//li[span[contains(text(), "Brand")]]/div/a/text()').extract()[0]
        sku = response.xpath('//div[@class="product-name"]/span[@class="web-id"]/text()').extract()
        if not sku:
            sku = response.xpath('//span[@itemprop="productId"]/@content').extract()
        sku = sku[0].strip()
        identifier = response.xpath('//input[@name="product"]/@value').extract()[0]
        price = response.xpath('//div[@class="price-box"]//span[@class="price"]/text()')[0].extract()
        price = extract_price(price)

        options_bundle = re.search(r'new Product.Bundle\((.*)\)', response.body)
        if options_bundle:
            self.log('OPTION BUNDLE: ' + response.url)
            selected_options = response.xpath('//select[contains(@id, "bundle-option-")]/option[@selected]/@value').extract()
            combined_options = []
            product_data = json.loads(options_bundle.groups()[0])

            # Calculate base price, summarizing all the prices for products without options
            base_price = 0
            for id, options in product_data['options'].iteritems():
                if options['isRequire'] == '0':
                    continue
                if len(options['selections'].values()) < 2:
                    for option_id, option in options['selections'].iteritems():
                        base_price += extract_price(str(option['priceInclTax'] * option.get('qty', 1)))

            for id, options in product_data['options'].iteritems():
                element_options = []
                # Extract options only for products with option selector
                if len(options['selections'].values()) > 1:
                    for option_id, option in options['selections'].iteritems():
                        try:
                            option_name = response.xpath('//option[@value="' + option_id + '"]/text()').extract()[0].strip()
                        except IndexError:
                            option_name = option['name']
                        option_price = extract_price(str(option['priceInclTax'] * option.get('qty', 1)))
                        option_attr = (option_id, option_name, option_price)
                        element_options.append(option_attr)
                    if element_options:
                        combined_options.append(element_options)

            if combined_options:
                combined_options = list(itertools.product(*combined_options))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                        final_option['price'] = final_option.get('price', 0) + option[2]

                    options.append(final_option)

                for option in options:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', identifier + option['identifier'])
                    loader.add_value('sku', sku)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('image_url', image_url)
                    loader.add_value('category', categories)
                    option_desc = option['desc'].strip()
                    if option_desc:
                        loader.add_value('name', name + ' ' + option_desc)
                    else:
                        loader.add_value('name', name)
                    loader.add_value('price', round(base_price + option['price'], 2))
                    yield loader.load_item()
            else:
                self.log('>>> Bundle product without options: ' + response.url)
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_value('image_url', image_url)
                loader.add_value('category', categories)
                loader.add_value('name', name)
                loader.add_value('price', price)
                yield loader.load_item()

        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('image_url', image_url)
            loader.add_value('category', categories)
            loader.add_value('name', name)
            loader.add_value('price', price)
            item = loader.load_item()
            metadata = OneStopBedroomsMeta()
            metadata['coleman_sku'] = meta.get('coleman_sku')
            metadata['coleman_url'] = meta.get('coleman_url')
            item['metadata'] = metadata
            yield item

        items = response.xpath('//div[@id="product-options-wrapper"]//dd/div[@class="input-box"]')
        items += response.xpath('//div[@id="product-options-wrapper"]//dd//div[contains(@class, "bundle-content")]/ul[@class="options-list"]/li[img]')
        for item in items:
            name = item.xpath('.//p[@class="product-name"]/a/text()').extract()[0]
            url = item.xpath('.//p[@class="product-name"]/a/@href').extract()[0]
            sku = item.xpath('.//div[@class="sku"]/text()').re('Product ID:(.*)')
            sku = sku[0].strip() if sku else ''
            price = item.xpath('.//p[@class="final-price"]/span[@class="price"]/text()').extract()
            image_url = item.xpath('.//img[contains(@class, "bundle-simple-image")]/@data-zoom-image').extract()
            image_url = image_url[0] if image_url else ''
            item_identifier = item.xpath('.//input[contains(@name, "bundle_option") and @value!=""]/@value').extract()
            if not item_identifier:
                item_identifier = item.xpath('.//div[contains(@id, "section")]/@id').re('section_(.*)')
            item_identifier = item_identifier[0]

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', item_identifier)
            loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('url', url)
            loader.add_value('image_url', image_url)
            loader.add_value('category', categories)
            loader.add_value('name', name)
            loader.add_value('price', price)
            item = loader.load_item()
            yield item
