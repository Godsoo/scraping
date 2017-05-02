from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price2uk

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import string

class axemusicSpider(BaseSpider):
    name = 'axemusic.com'
    allowed_domains = ['www.axemusic.com']
    start_urls = ['http://www.axemusic.com/store/']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//ul[@id="tabnav"]/li/a/@href').extract()
        for page in pages:
            yield Request(page, meta=response.meta, callback=self.parseDepartmentPage)
        pages = hxs.select('//ul[@id="tabnav"]/li/ul//a/@href').extract()
        for page in pages:
            yield Request(page, meta=response.meta, callback=self.parseCategoryPage)


    def parseDepartmentPage(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        subCategories = hxs.select('//table[@class="CatHeader"]//td[@class="subcatname"]/a/@href').extract()
        for subCat in subCategories:
            yield Request(urljoin_rfc(base_url, subCat), meta=response.meta, callback=self.parseCategoryPage)

    def parseCategoryPage(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//table[@class="pagination"]//a/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), meta=response.meta, callback=self.parseCategoryPage)
        category = hxs.select('//table//td[@valign="top"]/strong/font/text()').extract()
        productRows = hxs.select('//table[@class="productlisttable"]//tr[contains(@class, "productlist-row")]').extract()
        for productRow in productRows:
            hxs2 = HtmlXPathSelector(text=productRow)
            loader = ProductLoader(item=Product(), selector=hxs2)
            name = hxs2.select(u'.//td[2]//a[@class="product-link"]/text()')[0].extract().strip()
            loader.add_xpath('price', u'//td[3]//span[@class="list_prod_price"]/text()')
            loader.add_xpath('url', u'//td[2]//a[@class="product-link"]/@href')
            loader.add_value('category', category[0])
            sku = hxs2.select(u'.//td[3]//span[@class="list_prod_prodcode"]/text()')[0].extract()
            sku = re.search(u'Product Code: (.*)', sku).group(1).strip()
            loader.add_value('sku', sku)
            if loader.get_collected_values("price") and loader.get_collected_values("price")[0]:
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', 0)
            loader.add_value('identifier', sku)
            loader.add_value('name', name)
            yield Request(loader.get_output_value('url'), meta={'loader': loader}, callback=self.parseProductPage)

    def parseProductPage(self, response):
        hxs = HtmlXPathSelector(response)
        brand = re.search('Brand .*?: (.*?)<', response.body, re.DOTALL).group(1).strip()
        loader = response.meta['loader']
        loader.add_value('brand', brand)
        image_url = hxs.select(u'//img[@id="productphoto"]/@src')[0].extract()
        loader.add_value('image_url', image_url)
        yield loader.load_item()
