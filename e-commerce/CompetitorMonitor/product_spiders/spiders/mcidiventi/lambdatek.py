import time
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import canonicalize_url, urljoin_rfc, add_or_replace_parameter
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.utils import extract_price


class LambdaTekSpider(BaseSpider):

    handle_httpstatus_list = [404, 500]
    name = "lambda-tek.com"
    allowed_domains = ["lambda-tek.com"]
    start_urls = ["http://www.lambda-tek.com/componentshop/index.pl?region=GB"]
    product_ids = []
    rotate_agent = True


    def parse(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Extract categorial level 1
        catlevel1s = hxs.select('//*[@id="termsnav"]/tr/td/a/@href').extract()
        for catUrl in catlevel1s[1:]:
            yield Request(
                url=canonicalize_url(urljoin_rfc(base_url, catUrl)),
                callback=self.parse_categories,
                meta={'dont_merge_cookies': True},
                errback=self._retry_request)


    def parse_categories(self, response):

        if 'It appears that a program on your network is attempting to spider our site' in response.body:
            self.log('ERRROR! Spider detected!')
            yield self._retry_request(response, self.parse_categories)
            return
        if response.status == 404 or response.status == 500:
            self.log('ERRROR! Page accessing error!')
            yield self._retry_request(response, self.parse_categories)
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        subcats = hxs.select('//div[@id="SubCatTitle"]//ul[@id="Current"]/li/a/@href').extract()
        subcats += hxs.select('//div[@id="SubCatTitle"]//ul[@id="CurrentOn"]/li/a/@href').extract()
        for subcat in subcats:
            yield Request(
                url=urljoin_rfc(base_url, subcat),
                callback=self.parse_categories,
                meta=response.meta,
                errback=self._retry_request)

        for item in self.parse_subcats(response):
            yield item


    def parse_subcats(self, response):

        if 'It appears that a program on your network is attempting to spider our site' in response.body:
            self.log('ERRROR! Spider detected!')
            yield self._retry_request(response, self.parse_subcats)
            return
        if response.status == 404 or response.status == 500:
            self.log('ERRROR! Page accessing error!')
            yield self._retry_request(response, self.parse_subcats)
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            category = hxs.select('//span[@class="subText" and contains(text(), "Category:")]//span[@class="blue"]/text()').extract()[-1]
        except:
            category = ''

        products = hxs.select('//div[@class="ProductInfo"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('identifier', '@id', re=r'ID_(.*)')
            loader.add_xpath('name', 'h1/text()')
            loader.add_xpath('url', './table/tr/td/a[img]/@href')
            loader.add_xpath('price', './/div[@id="ProductOverviewPrice"]/text()')
            loader.add_xpath('sku', './/div[@id="ProductDetails"]/p[contains(text(), "Mfr Num:")]/strong/text()', lambda l: l[0].strip())
            loader.add_value('category', category.strip())
            image_url = product.select('./table/tr/td/a/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_xpath('brand', './/div[@id="ProductDetails"]/p[contains(text(), "Mfr Name:")]/strong/text()', lambda l: l[0].strip())
            stock = product.select('.//div[@class="ProductOverviewForm"]/b[contains(text(), "Availability:")]/text()').re(r'(\d+)')
            if stock:
                loader.add_value('stock', stock[0])
                if stock[0] == '0':
                    continue

            item = loader.load_item()

            if item['price'] and not ('REFURBISHED' in item['name'].upper() or 'SECOND HAND' in item['name'].upper() or
                'SPARES' in item['name'].upper() or 'OPEN BOX' in item['name'].upper()):
                    if item['identifier'] not in self.product_ids:
                        self.product_ids.append(item['identifier'])
                        yield item

        # Next page
        nextpage = hxs.select('//*[@id="MainContent"]/div[2]/table[1]/tr[3]/td/form/p/span[2]/b/a/@href').extract()
        if nextpage and products:
            yield Request(
                url=urljoin_rfc(base_url, nextpage[0]),
                callback=self.parse_subcats,
                errback=self._retry_request)


    def parse_product(self, response):

        if 'It appears that a program on your network is attempting to spider our site' in response.body:
            self.log('ERRROR! Spider detected!')
            yield self._retry_request(response, self.parse_product)
            return
        if response.status == 404 or response.status == 500:
            self.log('ERRROR! Page accessing error!')
            yield self._retry_request(response, self.parse_product)
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # Fill up the Product model fields
        identifier = hxs.select('//*[@id="ProductDetails"]/p[1]/b[2]/text()').extract()[0]
        url = canonicalize_url(response.url)
        name = hxs.select('//*[@id="MainContent"]/div[2]/h1/text()').extract()[0]
        price = hxs.select('//*[@id="ProductOverviewPrice"]/span[1]/text()').extract()[0]
        sku = hxs.select('//*[@id="ProductDetails"]/p[3]/text()').extract()[0].strip()
        category = hxs.select('//*[@id="BreadCrumb"]/a[3]/text()').extract()[0]
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        brand = hxs.select('//*[@id="ProductDetails"]/p[2]/span/text()').extract()[0].strip()
        stock = hxs.select('//span[@class="ProductOverviewStock"]/text()').re(r'(\d+)')
        if price:
            l = ProductLoader(response=response, item=Product())
            l.add_value('identifier', identifier)
            l.add_value('url', url)
            l.add_value('name', name)
            l.add_value('price', extract_price(price))
            l.add_value('sku', sku)
            l.add_value('category', category)
            if image_url:
                l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            l.add_value('brand', brand)
            if stock:
                l.add_value('stock', stock[0])
                if stock[0] == '0':
                    return
            yield l.load_item()


    def _retry_request(self, response, callback):

        time.sleep(20)
        retry = int(response.meta.get('retry', 0))
        if retry < 10:
            retry += 1
            meta = response.meta.copy()
            meta['retry'] = retry
            return Request(response.url,
                           callback=callback,
                           dont_filter=True,
                           meta=meta)
        else:
            self.log('ERROR - Retry limit reached: %s' % response.url)
            return None

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return ('It appears that a program on your network is attempting to spider our site' in response.body)
