import os
import re
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from scrapy.shell import inspect_response

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class NeweggSpider(BaseSpider):
    retry_urls = {}
    name = 'legousa-newegg.com'
    allowed_domains = ['newegg.com']
    start_urls = ('http://www.newegg.com/Product/ProductList.aspx?Submit=ENE&DEPA=0&Order=BESTMATCH&Description=LEGO&N=-1&isNodeId=1&Page=1',)

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'newegg_map_deviation.csv')

    def start_requests(self):
        return [Request(self.start_urls[0], cookies={"NVTC": ""})]

    def parse(self, response):
        #yield Request('http://www.newegg.com/Product/Product.aspx?Item=9SIA3G61658468&cm_re=LEGO-_-78-330-087-_-Product', callback=self.parse_product, meta={'sku':'sku', 'price':'price', 'seller_name':'seller_name'})
        #return
        hxs = HtmlXPathSelector(response)
        products = response.css('div.item-container')
        if not products or "newegg.com/Error.aspx" in response.url:
            url = response.meta['redirect_urls'][0]
            rc = self.retry_urls.get(url, 0)
            rc += 1
            if rc > 30:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                self.retry_urls[url] = rc
                yield Request(url, dont_filter=True, callback=self.parse, meta={'dont_redirect': True, 'handle_httpstatus_list': [302]})
            return

        for product in products:
            try:
                dollars = product.css('li.price-current strong::text').extract()[0]
                cents = product.css('li.price-current sup::text').extract()[0]
                price = dollars + cents
            except:
                price = ''.join(product.select('.//li[contains(@class, "price-current") '
                    'and contains(@class, "is-price-current-list")]//text()').extract()[2:4])
            seller_name = ''.join(product.select('div//a[@title="View Seller Profile"]/text()').extract())
            url = product.css('a.item-title::attr(href)').extract_first()
            name = product.css('a.item-title::text').extract_first()
            sku = 0
            for item in re.findall("\d+", name):
                if int(item) > sku:
                    sku = int(item)

            if sku < 1000:
                sku = ''.join(product.select('div[@class="itemText"]/ul[@class="featureList"]/li[b/text()="Model #: "]/text()').extract())

            yield Request(url, callback=self.parse_product, meta={'sku':sku, 'price':price, 'seller_name': seller_name})

        pages = response.css('div#page_NavigationBar button::text').re('\d+')
        for page in pages:
            yield Request(add_or_replace_parameter(response.url, 'Page', page), meta={'sku':sku})
        return
    
        pagination = response.xpath('//div[contains(@class, "pagination")]/ul/li/@class').extract()[-1]
        if pagination == 'enabled':
            page = int(url_query_parameter(response.url, 'Page'))
            yield Request(add_or_replace_parameter(response.url, 'Page', str(page + 1)), meta={'sku':sku, 'dont_redirect': True, 'handle_httpstatus_list': [302]})
        elif pagination != 'disabled':
            url = response.meta['redirect_urls'][0]
            rc = self.retry_urls.get(url, 0)
            rc += 1
            if rc > 30:
                self.log('Redirect retry max count reached, giving up: {}'.format(url))
            else:
                self.log('Redirected, trying again: #{}'.format(rc))
                self.retry_urls[url] = rc
                yield Request(url, dont_filter=True, callback=self.parse, meta={'dont_redirect': True, 'handle_httpstatus_list': [302]})
            return


    def parse_product(self, response):
        #inspect_response(response, self)
        #return

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
                yield Request(url, dont_filter=True, callback=self.parse_product,
                              meta={'sku': response.meta['sku'], 'price': response.meta['price'],
                                    'seller_name': response.meta['seller_name']})
            return
        # end of redirects workaround

        hxs = HtmlXPathSelector(response)
        meta = response.meta
        sellers_url = 'http://www.newegg.com/LandingPage/ItemInfo4ProductDetail2013.aspx?Item=%s&v2=2012'
        name = hxs.select('//div[@class="grpArticle"]/div[@class="grpDesc boxConstraint"]/div/h1/span[@itemprop="name"]/text()').extract()[0]
        brand = hxs.select('//div[@id="baBreadcrumbTop"]/dl/dd/a/text()').extract()[-1]
        category = hxs.select('//div[@id="baBreadcrumbTop"]/dl/dd/a/text()').extract()[-2]
        image_url = hxs.select('//a[@id="A2"]/span/img[contains(@src, "http://")]/@src').extract()
        identifier = re.findall(r'Item=([0-9a-zA-Z\-]+)', response.url)[0]
        sellers = hxs.select('//table[@class="gridSellerList"]')
        stock = 0
        tmp = re.findall(r"product_instock:\['(\d)'\]", response.body)
        if tmp:
            stock = int(tmp[0])
        shipping = re.findall(r"product_default_shipping_cost:\['([0-9.]+)'\]", response.body)
        sku = meta['sku']
        if not sku:
            sku = response.xpath('//script/text()').re("product_model:\['(.+)'\]")
        if sellers:
            item_id = response.url.split('Item=')[-1].split('&')[0]
            yield Request(sellers_url % item_id,
                          callback=self.parse_sellers,
                          meta={'name':name,
                                'brand':brand,
                                'category':category,
                                'identifier': identifier,
                                'sku': sku,
                                'image_url':image_url,
                                'stock':stock,
                                'url':response.url})
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', identifier)
            loader.add_value('name', name)
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('price', meta['price'])
            loader.add_value('stock', stock)
            if image_url:
                loader.add_value('image_url', image_url[0])
            if shipping:
                loader.add_value('shipping_cost', shipping.pop())
            loader.add_value('dealer', 'NEgg - ' + meta['seller_name'])
            yield loader.load_item()

    def parse_sellers(self, response):
        #inspect_response(response, self)
        #return
        sellers_lists = []
        for line in response.body.split('\n'):
            if "rawSellerList=" in line:
                sellers_lists = json.loads('[' + re.search(r"[^[]*\[([^]]*)\]", line).group(1) + ']')

        for sellers_list in sellers_lists:
            hxs = HtmlXPathSelector(text=sellers_list.get('sellerInfo'))

            meta = response.meta

            sellers = hxs.select('//tr')
            total_sellers = len(sellers)
            for seller in sellers:
                #price = ''.join(seller.select('.//li[contains(@class, "price-current")]//text()').extract()[1:4]).strip()
                price = ''.join(seller.select('.//li[contains(@class, "price-current")]/*[self::strong or self::sup]/text()').extract()).strip()
                shipping = "".join(seller.select('.//li[contains(@class, "price-ship")]//text()').extract())
                seller_name = seller.select('.//a[contains(@class, "noLine")]/@title').extract()
                if not seller_name:
                    continue
                identifier = seller.select('.//input/@id').re(r'addCartHref(\w+)')
                if not identifier:
                    continue

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', identifier.pop())
                loader.add_value('name', meta['name'])
                loader.add_value('category', meta['category'])
                loader.add_value('brand', meta['brand'])
                loader.add_value('sku', meta['sku'])
                loader.add_value('url', meta['url'])
                loader.add_value('price', price)
                loader.add_value('stock', meta['stock'])
                loader.add_value('shipping_cost', '0.00' if 'FREE' in shipping else shipping)
                loader.add_value('image_url', meta['image_url'])
                loader.add_value('dealer', 'NEgg - ' + seller_name.pop())

                yield loader.load_item()
