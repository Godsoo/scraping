import re
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product
from axemusic_item import ProductLoader


class ItalMelodieSpider(BaseSpider):
    name = "italmelodie.com"
    allowed_domains = ['italmelodie.com']
    # start_urls = ("http://www.italmelodie.com/?section=sitemap",)
    start_urls = ['http://www.italmelodie.com/?section=search&do=search&searchStr=&resultsQty=1000&pageNo=1&sort=']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        url = 'http://www.italmelodie.com/?section=search&do=search&searchStr=&resultsQty=1000&pageNo=%s&sort='
        products = hxs.select('//table/tr/td/table[@class="greyBox"]/tr/td/table/tr/td/table/tr/td/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)
        last_page = int(hxs.select('//table[@class="center pagingTable white text11"]//td[@class="num hand"]/text()').extract()[-1])
        next_page = hxs.select('//table[@class="center pagingTable white text11"]//td[@class="hand white text11 bold" and text()="NEXT"]/@onclick').extract()[-1]
        next_page = int(re.findall(r'\b\d+\b', next_page)[0])
        if last_page >= next_page:
            yield Request(url % next_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        meta_url = hxs.select('//meta[@property="og:url"]/@content').extract()[0]
        parsed = urlparse.urlparse(meta_url)
        params = urlparse.parse_qs(parsed.query)

        name = hxs.select('//td[@class="text11 bold"]//h1/text()').extract()
        sku = hxs.select('//div[@class="grey text12"]/text()').re(r'Model: ([\w-]+)')
        price = hxs.select('//table[@class="bold text11"]//tr[@class="bold darkBlue"]/td[2]/text()').extract()
        category = hxs.select('//div[@id="breadcrums"]/a[1]/text()').extract()
        img_url = hxs.select('//img[@id="itemImage"]/@src').extract()[0]
        base_url = get_base_url(response)
        img_url = urljoin_rfc(base_url, img_url)
        brand = hxs.select('//div[@class="grey text12"]/following-sibling::img[1]/@src').extract()
        if (brand):
            brand = brand[0]
            brand = re.search('([\w]+)\.+', brand).group(1)

        if not price:
            # If product has sub-products
            prod_list = hxs.select('//div[@class="grey text12"]/following-sibling::table[1]//select/option/@value').extract()
            for prod in prod_list:
                item_id = str('itemID=' + prod)
                url = re.sub('itemID=([\d]+)', item_id, response.url)
                yield Request(url, callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', [u'$0.0'])

        loader.add_value('identifier', params['itemID'])
        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('category', category)
        loader.add_value('image_url', img_url)
        if (brand):
            loader.add_value('brand', brand)

        # Not Found - Shipping cost
        yield loader.load_item()




