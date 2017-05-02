import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter

from product_spiders.items import Product, ProductLoader
from scrapy.http import FormRequest

class ChapmansAnglingSpider(BaseSpider):
    name = 'chapmansangling.co.uk'
    allowed_domains = ['chapmansangling.co.uk']
    start_urls = ('http://www.chapmansangling.co.uk',)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//div[@id="crumblinks"]//a/text()').extract()
        category = category[-1] if category else ''
        image_url = hxs.select('//img[@id="product-big"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''

        product_brand = ''
        brand_url = hxs.select('//div[@class="description"]//img[@alt="Brand Image"]/parent::a/@href').extract()
        if brand_url:
            brand_url = urljoin_rfc(base_url, brand_url[0])
            product_brand = url_query_parameter(brand_url, 'search')

        name = hxs.select("//h1[@class='coarse']/text()")[0].extract().strip()
        options = hxs.select('//div[@class="generated"]/table/tr')[1:]
        select = hxs.select('//form[@id="cart_form"]//select[@class="prodoptions"]').extract()
        if options:
            # options
            for option in options:
                name2 = option.select('./td[position()=4]/text()')
                name2 = name2[0].extract().strip() if name2 else ''
                price = option.select('.//td/text()').extract()[-2].strip()
                loader = ProductLoader(item=Product(), selector=option)
                loader.add_xpath('identifier', './td[position()=2]/text()')
                loader.add_xpath('sku', './td[position()=3]/text()')
                loader.add_value('url', response.url)
                loader.add_value('name', name + ' %s %s' % (loader.get_output_value('identifier'), name2))
                loader.add_value('price', price)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('brand', product_brand)
                yield loader.load_item()
        else:
            price = "".join(hxs.select(".//span[@class='bigprice']/text()").re(r'([0-9\,\. ]+)')).strip()
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('identifier', response.url)
            loader.add_value('image_url', image_url)
            loader.add_value('category', category)
            loader.add_xpath('sku', './td[position()=2]/text()')
            loader.add_value('brand', product_brand)
            yield loader.load_item()

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//ul[@id="product-nav"]/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url))

        # additional categories
        acategory_urls = hxs.select('//div[@class="subnavboxcon"]//a/@href').extract()
        for aurl in acategory_urls:
          yield Request(urljoin_rfc(base_url, aurl))

        # products
        products = hxs.select('//div[@class="productlistcon"]//a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

