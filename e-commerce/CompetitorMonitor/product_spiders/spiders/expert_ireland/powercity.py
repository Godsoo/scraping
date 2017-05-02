from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin, parse_qsl, urlparse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
import re

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class PowerCity(BaseSpider):
    name = "expert_ireland_powercity"
    allowed_domains = ['powercity.ie']
    start_urls = ('http://www.powercity.ie',)
    
    deduplicate_identifiers = True
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//ul[@id="sddm"]//a/@href').extract()
        for cat in categories:
            yield Request(response.urljoin(cat), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        #pages
        parameters = parse_qsl(urlparse(response.url).query)
        for page in xrange(1, 50):
            url = 'http://www.powercity.ie/slider271014.php?npages=%d&totrows=1' %page
            for par in parameters:
                url = add_or_replace_parameter(url, *par)
            yield Request(url, callback=self.parse_category)
            
        #products
        for item in hxs.select('//table/tr/td[3]//a/@href').extract():
            url = urljoin(base_url, item)
            yield Request(url, callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        flix = '//script[@type="text/javascript"]/@data-flix-%s'
        
        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//td/div[@align="center"]/b/text()').extract()
        if not name:
            return
        loader.add_value('name', name[0].strip(' ,'))
        identifier = hxs.select(flix %'ean').extract()
        if not identifier or not identifier[0].strip():
            identifier = hxs.select('//b[contains(text(), "Model :")]/../text()[1]').extract()
        sku = hxs.select(flix %'mpn').extract()
        if not sku or not sku[0]:
            sku = hxs.select('//b[contains(text(), "Model")]/../text()[1]').extract()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = re.findall(u'POST.+?> *&#8364;(.+?) *<', response.body)
        loader.add_value('price', price)
        loader.add_xpath('category', '//h8//a[position()>1]/text()')
        image_url = hxs.select('//div[@id="big-photo"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@alt="%s"]/@src' %sku[0].strip()).extract() or response.xpath('//tr/td[@colspan="2"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))
        loader.add_xpath('brand', flix %'brand')
        stock = re.findall(u"POST.+?> *&#8364;.+(buy.png)", response.body)
        if not stock:
            loader.add_value('stock', 0)
        item = loader.load_item()
        if response.xpath('//img[@alt="Exdisplay"]'):
            item['metadata'] = {'Ex Display': 'Ex Display'}
        
        yield item