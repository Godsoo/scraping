import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class DiscountCamerasSpider(BaseSpider):
    name = "discountcameras.com.au"
    allowed_domains = ["discountcameras.com.au", ]
    start_urls = ["http://www.discountcameras.com.au/discountcameras/product_list/53?manufacturer=true&per_page=160"]
    retry_urls = {}
    user_agent = 'Opera/9.80 (Windows NT 6.1; U; es-ES) Presto/2.9.181 Version/12.00'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            retry_count = self.retry_urls.get(response.url, 0)
            retry_count += 1
            if retry_count > 100:
                self.log("ERROR MAX retry count reached (100), giving up...")
                return
            else:
                self.log("ERROR - got response that is not HTML, adding to retry queue (#{})".format(retry_count))
                self.retry_urls[response.url] = retry_count
                yield Request(url=response.url, callback=self.parse, dont_filter=True)

        hxs = HtmlXPathSelector(response)

        pages = hxs.select('//div[@class="contents"]/div//h2//div[@class="pagination"]//a/@href').extract()
        for page in pages:
            url = urljoin_rfc(get_base_url(response), page)
            yield Request(url=url, callback=self.parse)

        category = hxs.select('//div[@class="contents"]/h1/text()').extract()
        if not category:
            self.log('ERROR - No category name found!')
            category = brand = ''
        else:
            category = brand = category[0]

        products = hxs.select('//div[@class="contents"]/table//tr[td[@valign="middle"]]')
        if not products:
            self.log('ERROR - empty products list, needs investigation!')
            return
        for product in products:
            product_id = product.select('.//a[@class="buttonBig"]/@href').re(r'add_to_cart/(\d+)')
            if not product_id:
                continue

            product_loader = ProductLoader(item=Product(), selector=product)
            product_url = product.select('.//td//font//b//a/@href').extract()
            if product_url:
                product_url = urljoin_rfc(get_base_url(response), product_url[0])
                product_loader.add_value('url', product_url)
            product_image = product.select('.//img[@class="product_image"]/@src').extract()
            if product_image:
                product_image = urljoin_rfc(get_base_url(response), product_image[0])
                product_loader.add_value('image_url', product_image)
            product_loader.add_value('identifier', product_id)
            product_loader.add_xpath('name', './/td//font//b//a/text()')
            product_loader.add_xpath('price', './/td//font[@class="price"]//b/text()')
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            item = product_loader.load_item()
            yield Request(item['url'], callback=self.parse_product, meta={'item': item})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        item = response.meta['item']

        sku = hxs.select('//p/text()').re('EAN:(.*)Man')
        if sku:
            sku = sku[0].split()
            item['sku'] = sku[0] if sku else ''
            
        yield item
