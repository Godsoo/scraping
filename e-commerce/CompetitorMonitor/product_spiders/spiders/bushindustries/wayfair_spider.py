import re
import json
import os
import itertools
from decimal import Decimal
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urllib import urlencode


HERE = os.path.abspath(os.path.dirname(__file__))


class WayFairComSpider(Spider):
    name = 'bushindustries-wayfair.com'
    allowed_domains = ['wayfair.com']
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'

    start_urls = ('https://www.wayfair.com/Furniture-C45974.html',)
    collected_identifiers = set()
    ajax_stock_url = 'http://www.wayfair.com/ajax/stock_total.php'

    product_urls = ('https://www.wayfair.com/Bush-Industries-Universal-72-Bookcase-BU4156.html?redir=WL12436-03&rtype=8',
            'https://www.wayfair.com/Cabot-L-Shape-Desk-with-Hutch-RDBS3247-RDBS3247.html',
            'https://www.wayfair.com/Cabot-Corner-Desk-with-Hutch-RDBS3254-RDBS3254.html',
            'https://www.wayfair.com/Powder-Hollow-Computer-Desk-RDBS1586-RDBS1586.html',
            'https://www.wayfair.com/Capital-2-Drawer-Lateral-File-RDBS1593-RDBS1593.html?rtype=8&redir=RDBS1593',
            'https://www.wayfair.com/Capital-36-60-Hutch-RDBS1592-RDBS1592.html?rtype=8&redir=RDBS1592',
            'https://www.wayfair.com/Capital-46.63-Cube-Unit-RDBS2291-RDBS2291.html?rtype=8&redir=RDBS2291')

    def start_requests(self):
        for url in self.product_urls:
            yield Request(url, callback=self.parse_item)

    def parse(self, response):
        #categories = response.xpath('//div[@class="cms_page page_type_category"]//a/@href').extract()
        categories = response.xpath('//div[contains(@class,"cms_left_nav_section")]/div[div/span[contains(text(),"Featured Categories")]]//a/@href').extract()
        categories += response.xpath('//div[contains(@class,"js-image-block")]/a[img and contains(@href,"/All-")]/@href').extract()
        categories += response.xpath('//div[@data-hover-event-track="TopNav_Furniture"]//a/@href').extract()
        categories += response.xpath('//div[contains(@class,"subCat")]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        next_page = response.xpath('//a[contains(@class,"js-next-page")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

        products = response.xpath('//a[contains(@class,"SbProductBlock") and @data-sku]/@href').extract()
        products += response.xpath('//a[contains(@class,"js-prod-content") and @data-sku]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_item)

    def parse_item(self, response):
        meta = response.meta
        prev_price = response.xpath('//div[contains(@class,"js-consumer-discount-block ")]'
                                    '//span[@class="ProductDetailInfoBlock-pricing-strikethrough js-listprice"]/text()').extract()
        brand = response.xpath('//a[@data-event-name="manu_view_all"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        categories = response.css('.ProductDetailBreadcrumbs-item::text').extract()
        sku = response.xpath('//span[@class="ProductDetailBreadcrumbs-item--product"]/text()').re('SKU: (.*)')

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

        products_collected = []
        sku_list = []

        options = []
        dropdown_options = response.xpath('//select[contains(@class, "stdselect") or contains(@class,"js-dropdown-option")]/option[@value!="XXXXXXXXXX"]')
        option_elements = []
        if dropdown_options:
            for dropdown_option in dropdown_options:
                option = {}
                option['identifier'] = dropdown_option.xpath('@value').extract()[0]
                option['sku'] = sku[0] if sku else ''
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
                    option['sku'] = sku[0] if sku else ''
                    option['desc'] = dropdown_option.xpath('.//text()').extract()[0].split('-')[0]
                    cost = dropdown_option.xpath('@cost').extract() or re.findall('\+\$([\d.]+)', option['desc'])
                    option['cost'] = cost[0] if cost else '0'
                    options.append(option)
                option_elements.append(options)

        image_options = response.css('.option_select_wrap .visual_option_wrap')
        image_options += response.css('a.ProductDetailOptions-thumbnail')
        if image_options:
            options = []
            for image_option in image_options:
                option = {}
                option['identifier'] = image_option.xpath('@data-pi-id').extract()[0]
                option['sku'] = sku[0] if sku else ''
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

            for option in options:
                price = response.xpath('//meta[@property="og:price:amount"]/@content').extract()
                if not price:
                    price = response.xpath('//*[@class="dynamic_sku_price"]/span/text()').extract()
                if not price:
                    price = response.xpath('//*[@data-id="dynamic-sku-price"]/text()').extract()
                if price:
                    price = price[0]
                #price += response.xpath('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]
                option_price_value = self.option_price(price, str(option['cost']))

                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', name + ' ' + option['desc'])
                product_loader.add_xpath('sku', '//span[@class="ProductDetailBreadcrumbs-item--product"]/text()',
                                         re='SKU: (.*)')
                identifier = response.xpath('//input[@name="sku"]/@value').extract()[0]
                product_loader.add_value('identifier', identifier + '-' + option['identifier'])
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', categories)
                if image_url:
                    product_loader.add_value('image_url', image_url[0])
                product_loader.add_value('url', response.url)

                product_loader.add_value('price', option_price_value)
                product = product_loader.load_item()
                if prev_price and prev_price[0].strip():
                    product['metadata'] = {'was': prev_price[0].strip()}
                if product['identifier'] not in self.collected_identifiers:
                    self.collected_identifiers.add(product['identifier'])
                    sku_list.append(product['identifier'].split('-') + [product])

        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name)
            product_loader.add_xpath('sku', '//span[@class="ProductDetailBreadcrumbs-item--product"]/text()',
                                     re='SKU: (.*)')
            product_loader.add_xpath('identifier', '//input[@name="sku"]/@value')
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', categories)
            if image_url:
                product_loader.add_value('image_url', image_url[0])
            price = response.xpath('//meta[@property="og:price:amount"]/@content').extract_first()
            if not price:
                price = response.xpath('//span[@data-id="dynamic-sku-price"]/text()').extract_first()
            #price += response.xpath('//*[@class="dynamic_sku_price"]/span/sup/text()').extract()[0]

            product_loader.add_value('price', price)

            product_loader.add_value('url', response.url)

            product = product_loader.load_item()
            if prev_price and prev_price[0].strip():
                product['metadata'] = {'was': prev_price[0].strip()}

            if product['identifier'] not in self.collected_identifiers:
                self.collected_identifiers.add(product['identifier'])
                sku_list.append([product['identifier'], None, product])

        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest'}
        for sku, option_id, product in sku_list:
            params = {'event_id': '',
                     'is_fully_configured': 'true',
                     'kitmode': '0',
                     'postal_code': '67346',
                     'product_data[0][qty]': '1',
                     'product_data[0][sku]': sku,
                     'quantity': '1'}
            if option_id:
                params['product_data[0][option_ids][]'] = option_id
            stock_url = 'https://www.wayfair.com/a/product/get_liteship_and_inventory_data? '
            yield Request(stock_url + urlencode(params),
                          headers=headers, dont_filter=True,
                          meta={'product': product, 'prod_id': prod_id, 'prod_url': response.url},
                          callback=self.parse_stock)

    def parse_stock(self, response):
        data = json.loads(response.body)

        p = response.meta.get('product')
        p['stock'] = int(data['inventory'][0]['available_quantity'])
        yield p

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
            #self.log("Price: %s" % price)
            return price + cost
        else:
            return None

    def _blocked_response(self, response):
        return ('distil_r_captcha' in response.url) or (response.status == 405)

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return self._blocked_response(response)
