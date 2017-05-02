import os
import re
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from datetime import datetime

from arrisitems import ReviewLoader, Review


from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class NeweggSpider(BaseSpider):
    retry_urls = {}
    name = 'arris_international-newegg.com'
    allowed_domains = ['newegg.com']
    start_urls = ('http://www.newegg.com/Product/ProductList.aspx?Submit=ENE&DEPA=0&Order=BESTMATCH&Description=surfboard&N=-1&isNodeId=1&Page=1',)

    def parse(self, response):
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
                yield Request(url, dont_filter=True, callback=self.parse, meta={'dont_redirect': True,
                                                                                'handle_httpstatus_list': [302]})
            return

        for product in products:
            try:
                dollars = product.css('li.price-current strong::text').extract()[0]
                cents = product.css('li.price-current sup::text').extract()[0]
                price = dollars + cents
            except IndexError:
                price = ''.join(product.select('.//li[contains(@class, "price-current") '
                                               'and contains(@class, "is-price-current-list")]//text()').extract()[2:4])
            url = product.css('a.item-title::attr(href)').extract_first()
            yield Request(url, callback=self.parse_product, meta={'price': price})

        pages = response.css('div#page_NavigationBar button::text').re('\d+')
        for page in pages:
            yield Request(add_or_replace_parameter(response.url, 'Page', page))

    def parse_product(self, response):
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
                              meta={'price': response.meta['price']})
            return
        # end of redirects workaround

        meta = response.meta
        name = response.xpath('//div[@class="grpArticle"]/div[@class="grpDesc boxConstraint"]/'
                              'div/h1/span[@itemprop="name"]/text()').extract()[0]
        #brand = response.xpath('//div[@id="baBreadcrumbTop"]/dl/dd/a/text()').extract()[-1]
        brand = 'SURFboard'
        category = response.xpath('//div[@id="baBreadcrumbTop"]/dl/dd/a/text()').extract()[-3:]
        image_url = response.xpath('//a[@id="A2"]/span/img[contains(@src, "http://")]/@src').extract()
        price = response.xpath('//meta[@itemprop="price"]/@content').extract()[0]
        identifier = re.findall(r'Item=([0-9a-zA-Z\-]+)', response.url)[0]
        stock = 0
        tmp = re.findall(r"product_instock:\['(\d)'\]", response.body)
        if tmp:
            stock = int(tmp[0])
        shipping = re.findall(r"product_default_shipping_cost:\['([0-9.]+)'\]", response.body)
        sku = response.xpath('//script/text()').re("product_model:\['(.+)'\]")

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('category', category)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        if image_url:
            loader.add_value('image_url', image_url[0])
        if shipping:
            loader.add_value('shipping_cost', shipping.pop())
        item = loader.load_item()

        item['metadata'] = {'reviews': []}

        reviews_url = re.findall("Biz.Product.ProductReview.switchReviewTab\('(.*)'\);", response.body)
        if reviews_url:
            reviews_url = 'http://www.newegg.com/Common/AJAX/ProductReview2016.aspx?action=proxy' + reviews_url[0]
            yield Request(reviews_url, callback=self.parse_reviews, meta={'item': item})
        else:
            yield item

    def parse_reviews(self, response):
        item_ = response.meta['item']

        reviews_data = re.findall("proxy\((.*)\);", response.body)
        if reviews_data:
            reviews_data = json.loads(reviews_data[0])['ReviewList']
            hxs = HtmlXPathSelector(text=reviews_data)
            reviews = hxs.select('//tr')
            for review in reviews:
                l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
                author = review.xpath('th[@class="reviewer"]//em/text()').extract()
                if not author:
                    continue

                rating = review.xpath('.//span[@class="itmRating"]/span/text()').re('\d+')[0]
                date = review.xpath('th/ul/li[not(@class)]/text()').extract()[0]
                review = ' '.join(review.xpath('.//div[@class="details"]//p//text()').extract())

                l.add_value('rating', rating)
                l.add_value('author', author[0])
                l.add_value('url', response.url)
                l.add_value('date', datetime.strptime(date, '%m/%d/%Y %I:%M:%S %p').strftime('%m/%d/%Y'))
                l.add_value('full_text', review + ' by ' + author[0])
                item_['metadata']['reviews'].append(l.load_item())

            next = hxs.xpath('//span[@class="enabled"]/a[@class="next"]')
            if next:
                next_page = str(int(url_query_parameter(response.url, 'Page', '1')) + 1)
                next_url = add_or_replace_parameter(response.url, 'Page', next_page)
                yield Request(next_url, callback=self.parse_reviews, meta={'item': item_})
            else:
                yield item_
