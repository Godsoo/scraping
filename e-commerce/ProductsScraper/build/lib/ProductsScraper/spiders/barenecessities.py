import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class BarenecessitiesSpider(scrapy.Spider):
    name = "barenecessities"
    start_urls = ["http://www.barenecessities.com/search.aspx?search=clearanceCMD&drv=4294962061&gb=PV_PFID_Price&mode=1&noin=x&dscnt=1&msg=Clearance&drvOld=0"]

    def parse(self, response):
        sel = Selector(response)

        for prod in sel.xpath('//div[@id="mainResults"]/ul/li[@class="item thumbnail-item"]'):
            item = Product()

            item['Name'] = prod.xpath('ul[@class="feature-list"]/li[@class="fl-item title"]/a/text()').extract_first().strip()
            item['original_url'] = prod.xpath('ul[@class="feature-list"]/li[@class="fl-item title"]/a/@href').extract_first().strip()
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('ul[@class="feature-list"]/li[@class="fl-item price"]/a/span[@class="plp_product__strikeoutprice"]/b/text()').extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('ul[@class="feature-list"]/li[@class="fl-item price"]/a/span[@class="fontSale plp_product_price"]/b/text()').extract_first()).strip()
            item['website_id'] = 9
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
        #     break
        # return

        try:
            nextpage_url = response.urljoin(sel.xpath('//ul[@class="no-bullet paging"]/li[@class="next"]/a/@href').extract_first()).strip()
            if (nextpage_url is None) or (nextpage_url == ''):
                return
            yield Request(nextpage_url, callback=self.parse)
        except:
            pass

    def parse_detail(self, response):
        sel = Selector(response)
        item = response.meta['item']

        # currency problem
        # price = sel.xpath('//span[@class="prodColorPrice"]/span[@id="cphMainContent_productPricingControl_ColorPriceLabel"]/text()').extract_first().split('-')
        # item['reg_price'] = re.sub('[^\d\.]', '', price[1]).strip()
        # item['sale_price'] = re.sub('[^\d\.]', '', price[0]).strip()
        item['description'] = ' '.join([frag.strip() for frag in sel.xpath('//dd[@class="accordion-navigation active"]/div[@id="panel1"]//text()').extract()])
        item['original_image_url'] = [sel.xpath('//meta[@property="og:image"]/@content').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
