import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from phantomjs import PhantomJS


class SainsBurysSpider(BaseSpider):
    name = u'legouk-sainsburys.co.uk'
    allowed_domains = [u'www.sainsburys.co.uk']
    start_urls = ['http://www.sainsburys.co.uk']

    def __init__(self, *args, **kwargs):
        super(SainsBurysSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self._browser.quit()

    def start_requests(self):
        yield Request('http://www.sainsburys.co.uk/sol/shop/toys_and_nursery/lego_and_construction/lego/list.html')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = [urljoin_rfc(base_url, url) for url in hxs.select('//div[@class="option"]/ul/li/a/@href').extract()]
        urls.append('http://www.sainsburys.co.uk/sol/shop/toys_and_nursery/list.html?search_term1=lego'
            '&searchType=%2Fsol%2Fshop%2Ftoys_and_nursery%2Flist.html&bmUID=1387823073231&sort=default&search=lego&fnav=4294965454')
        urls.append('http://www.sainsburys.co.uk/sol/shop/toys_and_nursery/list.html?'+
                    'sort=default&search=lego&search_term1=lego&searchType=%2Fsol%2Fshop%2Ftoys_and_nursery%2'+
                    'Flist.html&bmUID=1401289702846&pageNumber=1')

        items = []

        for url in urls:
            find_more = True
            while find_more:
                self.log('GET => %s' % url)
                self._browser.get(url)
                self.log('>> OK')

                item_links = self._browser.find_elements_by_xpath('//h3/span/a')
                new_items = [link.get_attribute('href') for link in self._browser.find_elements_by_xpath('//h3/span/a')]
                self.log('>> %d ITEMS FOUND' % len(new_items))
                items.extend(new_items)

                try:
                    next_page = self._browser.find_element_by_xpath('//ol/li[@class="next"]/a')
                    url = next_page.get_attribute('href')
                    self.log('>> NEXT PAGE FOUND => %s' % url)
                except:
                    self.log('NO NEXT PAGE IN %s' % self._browser.current_url)
                    find_more = False

        for item_url in items:
            yield Request(item_url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_url = urljoin_rfc(base_url, response.url)

        image_xpath = '//img[@id="bigImage"]/@src'
        image = hxs.select(image_xpath).extract().pop()
        image_url = urljoin_rfc(base_url, image)

        quantity = hxs.select('//span[@id="stockStatus"]/text()').extract()
        if quantity and "In stock" in quantity.pop():
            quantity = None
        else:
            quantity = 0

        price_int = hxs.select('//span[@id="nowPrice"]/text()').extract()[0]
        price_decimal = hxs.select('//span[@id="nowPrice"]/span[@id="nowPricePence"]/text()').extract()[0]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', product_url)
        loader.add_xpath('name', '//div[@class="productHeaderTextInner"]/h3/text()')
        loader.add_value('image_url', image_url)
        loader.add_value('price', price_int + price_decimal)
        loader.add_xpath('category', '//table[@class="featuresTable"]//tr[td/div[@title="Brand"]]/td[2]/text()')
        loader.add_xpath('brand', '//table[@class="featuresTable"]//tr[td/div[@title="Brand"]]/td[2]/text()')
        loader.add_xpath('identifier', '(//input[@id="skuCode"])[1]/@value')
        loader.add_xpath('sku', '(//input[@id="skuCode"])[1]/@value')

        if quantity == 0:
            loader.add_value('stock', 0)

        yield loader.load_item()
