import re
import json
import os
import csv
import itertools
import pandas as pd
from decimal import Decimal
from cStringIO import StringIO
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from householdessentialsitem import HouseholdEssentialsMeta, Review
from urllib import urlencode


HERE = os.path.abspath(os.path.dirname(__file__))


class WayFairComSpider(Spider):
    name = 'householdessentials-wayfair.com'
    allowed_domains = ['wayfair.com']
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'

    filename = os.path.join(HERE, 'householdessentials_products.csv')

    start_urls = ('file://' + filename,)

    ajax_stock_url = 'http://www.wayfair.com/ajax/stock_total.php'

    def __init__(self, *args, **kwargs):
        super(WayFairComSpider, self).__init__(*args, **kwargs)

        self.hhe_df = pd.read_csv(self.filename, dtype=pd.np.str)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        search_url = 'http://www.wayfair.com/keyword.php?keyword='
        for row in reader:
            yield Request(search_url + row['Wayfair'], callback=self.parse_search, meta={'client_product': row})

    def parse_search(self, response):
        meta = response.meta

        no_match = bool(response.xpath('//h2[contains(@class, "nomatch_text")]'))
        if no_match:
            return

        item_found = False
        for item in self.parse_item(response):
            if isinstance(item, Product):
                item_found = True
            yield item


        if not item_found:
            items = response.xpath('//a[contains(@id, "productbox_")]/@href').extract()
            for item in items:
                yield Request(response.urljoin(item), meta=response.meta, callback=self.parse_item)

            if not items:
                retry = meta.get('retry', 0)
                if retry <= 10:
                    self.log('WARNING >>> Retry search: ' + response.url)
                    retry += 1
                    meta['retry'] = retry
                    yield Request(response.url, dont_filter=True, callback=self.parse_search, meta=meta)
                else:
                    self.log('ERROR >>> Gave up retrying: ' + response.url)

    def parse_item(self, response):
        meta = response.meta

        categories = response.css('.ProductDetailBreadcrumbs-item::text').extract()
        sku = meta['client_product']['Item Number']

        image_url = response.xpath('//div[contains(@class, "main-carousel")]//a/@data-original-src').extract()
        if not image_url:
            image_url = response.xpath('//img[contains(@class, "ProductDetailImagesBlock-carousel-image")]/@src').extract()


        prod_id = response.xpath('//input[@name="sku"]/@value') .extract()
        prod_id = prod_id[0] if prod_id else ''

        try:
            name = response.xpath('//h1/span[contains(@class, "ProductDetailInfoBlock-header-title")]/text()').extract()[0]
        except Exception:
            retry = meta.get('retry', 0)
            if retry <= 10:
                retry += 1
                meta['retry'] = retry
                self.log('ERROR >>> No name found, retry URL: ' + response.url)
                yield Request(response.url, dont_filter=True, callback=self.parse_item, meta=meta)
                return
            else:
                self.log('ERROR >>> Gave up retrying URL: ' + response.url)
                return

        name += response.xpath('//h1/text()').extract()[-1].strip()
        brand = meta['client_product'].get('Brand', '')

        products_collected = []
        sku_list = []

        options = []
        dropdown_options = response.xpath('//select[contains(@class, "stdselect")]/option[@value!="XXXXXXXXXX"]')
        option_elements = []
        if dropdown_options:
            for dropdown_option in dropdown_options:
                option = {}
                option['identifier'] = dropdown_option.xpath('@value').extract()[0]
                option['sku'] = ''
                option['desc'] = dropdown_option.xpath('.//text()').extract()[0]
                cost = dropdown_option.xpath('@cost').extract() or re.findall('\+\$([\d.]+)', option['desc'])
                option['cost'] = cost[0] if cost else '0'
                options.append(option)
            option_elements.append(options)
        else:
            dropdown_elements = response.xpath('//div[@class="pdinfoblock"]/div[@class="fl"]//select')
            for dropdown_options in dropdown_elements:
                options = []
                for dropdown_option in dropdown_options.xpath('option[@value!="XXXXXXXXXX"]'):
                    option = {}
                    option['identifier'] = dropdown_option.xpath('@value').extract()[0]
                    option['sku'] = ''
                    option['desc'] = dropdown_option.xpath('.//text()').extract()[0].split('-')[0]
                    option['cost'] = dropdown_option.xpath('@cost').extract()[0]
                    options.append(option)
                option_elements.append(options)

        image_options = response.css('.option_select_wrap .visual_option_wrap')
        if image_options:
            options = []
            for image_option in image_options:
                option = {}
                option['identifier'] = image_option.xpath('@data-pi-id').extract()[0]
                option['sku'] = ''
                option['desc'] = image_option.xpath('@data-name').extract()[0]
                option['cost'] = image_option.xpath('@data-cost').extract()[0]
                options.append(option)
            option_elements.append(options)

        if option_elements:
            if len(option_elements) > 1:
                combined_options = list(itertools.product(*option_elements))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' - ' + option['desc']
                        final_option['cost'] = final_option.get('cost', 0) + float(option['cost'])
                        final_option['identifier'] = final_option.get('identifier', '') + ' - ' + option['identifier']
                    options.append(final_option)
            else:
                options = option_elements[0]

            products_matched = self.hhe_df[self.hhe_df['Wayfair'] == meta['client_product']['Wayfair']]

            for option in options:

                price = response.xpath('//*[@class="dynamic_sku_price"]/span/text()').extract()[0]
                #price += response.xpath('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]
                option_price_value = self.option_price(price, str(option['cost']))

                # SKU not unique: match the correct client product sku
                if not products_matched.empty and products_matched.count()['Wayfair'] > 1:
                    current_diff = Decimal(0)
                    current_sku = sku
                    for i, row in products_matched.iterrows():
                        wf_price = Decimal(row['Wayfair Cost'].replace('$', '').strip())
                        price_diff = abs(option_price_value - wf_price)
                        if (current_diff == Decimal(0)) or (price_diff < current_diff):
                            current_sku = str(row['Item Number'])
                            current_diff = price_diff

                    sku = current_sku

                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', name + ' ' + option['desc'])
                product_loader.add_value('sku', sku)
                identifier = response.xpath('//input[@name="sku"]/@value').extract()[0]
                product_loader.add_value('identifier', identifier + '-' + option['identifier'])
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', categories)
                if image_url:
                    product_loader.add_value('image_url', image_url[0])
                product_loader.add_value('url', response.url)

                product_loader.add_value('price', option_price_value)
                product = product_loader.load_item()

                metadata = HouseholdEssentialsMeta()
                metadata['reviews'] = []
                product['metadata'] = metadata


                products_collected.append(product)
                sku_list.append(product['identifier'])

        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name)
            product_loader.add_value('sku', sku)
            product_loader.add_xpath('identifier', '//input[@name="sku"]/@value')
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', categories)
            if image_url:
                product_loader.add_value('image_url', image_url[0])

            price = response.xpath('//span[@data-id="dynamic-sku-price"]/text()').extract_first()
            #price += response.xpath('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]

            product_loader.add_value('price', price)

            product_loader.add_value('url', response.url)

            product = product_loader.load_item()

            metadata = HouseholdEssentialsMeta()
            metadata['reviews'] = []
            product['metadata'] = metadata

            products_collected.append(product)
            sku_list.append(product['identifier'])

        transaction_id = re.findall(r'"transactionID":"(.*)",', response.body)[0]
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest'}

        params = urlencode({'bpss': 'yes',
                            'skulist': '~^~'.join(sku_list),
                            'kitmode': '0',
                            'postalcode': '67346',
                            '_txid': transaction_id})

        yield Request(self.ajax_stock_url + '?' + params,
                      headers=headers, dont_filter=True,
                      meta={'product': products_collected, 'prod_id': prod_id, 'prod_url': response.url},
                      callback=self.parse_stock)

    def parse_review(self, response):
        product = response.meta['product']

        reviews = response.xpath(u'//tr[contains(@class, "singlereview")]')
        for review in reviews:
            item = Review()
            date = review.xpath(u'.//div[contains(@class,"ltbodytext")]/text()').extract()[0]
            date = date.split('/')
            item['date'] = date[1] + '/' + date[0] + '/' + date[2]

            title = review.xpath(u'.//p[@itemprop="reviewBody"]/text()').extract()
            if title:
                title = title[0]
            else:
                title = ''

            text = review.xpath(u'.//div[contains(@class, "bodytext")]/p/text()').extract()
            if text:
                text = text[-1]
            else:
                text = ''

            item['full_text'] = title + '\n' + text

            item['rating'] = int(float(review.xpath(u'.//span[@itemprop="ratingValue"]/text()').extract()[0]))

            item['url'] = response.url

            if isinstance(product, list):
                for p in product:
                    p['metadata']['reviews'].append(item)
            else:
                product['metadata']['reviews'].append(item)

        next_url = response.xpath('//a[contains(@class, "page-next ")]')
        self.log(next_url)
        if next_url:
            try:
                page = int(response.url.split('page_number=')[-1]) + 1
            except:
                if reviews:
                    page = 2
                else:
                    page = 1
            yield Request('http://www.wayfair.com/a/product_review_page/get_update_reviews_json?product_sku=%s&page_number=%s' % (
                response.meta['prod_id'], page), meta=response.meta, callback=self.parse_review)
        else:
            if isinstance(product, list):
                for p in product:
                    yield p
            else:
                yield product

    def parse_stock(self, response):
        try:
            data = json.loads(response.body)
        except ValueError:
            data = {}

        for p in response.meta['product']:
            if p['identifier'] in data:
                p['stock'] = int(data[p['identifier']]['Qty'])

        yield Request(response.meta['prod_url'],
                      meta=response.meta,
                      dont_filter=True,
                      callback=self.parse_review)

    def calculate_price(self, value):
        res = re.search(r'[,.0-9]+', value)
        if res:
            price = Decimal(res.group(0).replace(',', ''))
            self.log("Price: %s" % price)
            return price
        else:
            return None

    def option_price(self, base_price, cost):
        res = re.search(r'[.0-9,]+', base_price)
        cost_res = re.search(r'[.0-9,]+', cost)
        if res:
            price = Decimal(res.group(0).replace(',', ''))
            cost = Decimal(cost_res.group(0).replace(',', ''))
            self.log("Price: %s" % price)
            return price + cost
        else:
            return None

    def _blocked_response(self, response):
        return ('distil_r_captcha' in response.url) or (response.status == 405)

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return self._blocked_response(response)
