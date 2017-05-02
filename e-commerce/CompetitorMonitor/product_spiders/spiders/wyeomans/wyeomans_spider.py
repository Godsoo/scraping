import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class WYeomansSpider(BaseSpider):
    '''
        NOTE: Do not use proxies for this spider, looks like some session data
        is stored for each IP (hidden inputs for FormRequest)
    '''

    name = 'yeomansoutdoors.co.uk'
    allowed_domains = ['yeomansoutdoors.co.uk']
    start_urls = ['http://www.yeomansoutdoors.co.uk/products.xml']
    pending_requests = []

    def __init__(self, *args, **kwargs):
        BaseSpider.__init__(self, *args, **kwargs)
        dispatcher.connect(self.process_pending, signals.spider_idle)

    def process_pending(self, spider):
        if spider != self: return
        if self.pending_requests:
            self.log('Yield pending request')
            while self.pending_requests:
                req = self.pending_requests.pop()
                self.crawler.engine.schedule(req, spider)
            raise DontCloseSpider('Found pending requests')

    def _start_requests(self):
        yield Request('http://www.yeomansoutdoors.co.uk/footwear.aspx/safety-boots/mens/black/progressive-footwear/contractor-safety-shoe-9/14261200009', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for i, url in enumerate(re.findall(r'<loc>(.*)</loc>', response.body)):
            yield Request(url, callback=self.parse_product, meta={'cookiejar': i})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        found_something = False
        for url in hxs.select('//div[@id="landing"]//a/@href').extract():
            found_something = True
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list)

        found = False
        for url in hxs.select('//table[@id="MainContent_NormalViewTable"]//td//a/@href').extract():
            found_something = True
            found = True
            self.pending_requests.append(Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product))
        if found:
            try:
                page = int(response.url.split('/')[-1])
                yield Request(response.url[:response.url.rindex('/') + 1] + str(page + 1), callback=self.parse_list)
            except:
                yield Request(response.url + '/2', callback=self.parse_list)

        if not found_something:
            self.log('No links found on %s' % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//*[@id="producttitle2"]/text()').extract()
        if name:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('sku', 'normalize-space(substring-after(//p[@class="productcode"]/text(),"-"))')
            loader.add_xpath('identifier', 'normalize-space(substring-after(//p[@class="productcode"]/text(),"-"))')
            loader.add_value('url', response.url)
            loader.add_value('name', name)

            size_selected = hxs.select('//select[@id="SizeDropDown"]//option[@selected]/@value').extract()
            if size_selected:
                loader.add_value('name', ' ' + size_selected[0])

            # Sometimes name already contains option name
            if ''.join(hxs.select('//select[@id="MainContent_SizeDropDown"]//option[@selected="selected"]/@value').extract()) not in name:
                loader.add_xpath('name', '//select[@id="MainContent_SizeDropDown"]//option[@selected="selected"]/@value')

            loader.add_xpath('price', '//*[@id="titleSection"]/p[@class="productprice"]/text()')

            for cat in hxs.select('//ul/li/ul/li/a'):
                if ''.join(cat.select('./@href').extract()) in response.url:
                    loader.add_value('category', ''.join(cat.select('./text()').extract()))
                    break
            img = hxs.select('//img[@id="MainContent_prodimage"]/@src').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            brand = ''.join(hxs.select('//img[@id="MainContent_imgBrandLogo"]/@src').extract())
            brands = {
                '/images/brands/hi-tec.png': 'hi-tec',
                '/images/brands/progressive.png': 'progressive safety',
            }
            loader.add_value('brand', brands.get(brand, brand.split('/')[-1].split('.')[0]))
            stock = hxs.select('//span[@id="MainContent_RemStockLabel"]/text()').re('\d+')
            if stock:
                loader.add_value('stock', stock)
            elif hxs.select('//*[@id="MainContent_RemStockLabel" and contains(@class, "remstockgreen")]'):
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', '0')

            if loader.get_output_value('price') < 50:
                loader.add_value('shipping_cost', '4.50')
            else:
                loader.add_value('shipping_cost', '0')

            yield loader.load_item()

            if not response.meta.get('formpost'):
                formdata = {}
                for input_elem in hxs.select('//input'):
                    if input_elem.select('./@name') and input_elem.select('./@value'):
                        formdata[''.join(input_elem.select('./@name').extract())] = ''.join(input_elem.select('./@value').extract())
                for size in hxs.select('//select[@id="SizeDropDown"]//option/@value').extract():
                    formdata = dict(formdata)
                    formdata['ctl00$MainContent$SizeDropDown'] = size
                    self.log('Request size %s for %s' % (size, response.url))
                    yield FormRequest('http://www.yeomansoutdoors.co.uk/Product.aspx',
                                      formdata=formdata,
                                      dont_filter=True,
                                      callback=self.parse_product,
                                      meta={'formpost':True,
                                            'size': size})

