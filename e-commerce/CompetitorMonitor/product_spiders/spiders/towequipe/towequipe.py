from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader

class TowEquipeCoUkSpider(BaseSpider):
    name = 'towequipe.co.uk'
    allowed_domains = ['www.towequipe.co.uk']
    start_urls = ('http://www.towequipe.co.uk/itemlist.html?searchquery=Witter&submit=Submit',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="Products-Row-list"]/div/div/div/a[@class="Product-Text-Link"]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next_page = hxs.select('//p[@class="Paging"]/a[@title="Next Page"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', '//h1[@class="Detail-Heading"]/text()')
        product_loader.add_xpath('price', '//div[@id="Item-Details-Container"]//span[@class="now"]/text()')
        product_loader.add_xpath('price', '//div[@style="position:relative;"]//span[@class="now"]/text()')
        product_loader.add_xpath('sku', '//ul[@class="Product-Detail-List"]//li[contains(text(),"Stock")]/b/text()')
        product_loader.add_xpath('identifier', '//ul[@class="Product-Detail-List"]//li[contains(text(),"Stock")]/b/text()')
        product_loader.add_value('url', response.url)
        yield product_loader.load_item()
