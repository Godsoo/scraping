import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import requests

class DillardsSpider(scrapy.Spider):
    name = "dillards"
    start_urls = [   "http://www.dillards.com/c/women?facet=dil_pricereduced:1",
                   # 'http://www.dillards.com/c/women?facet=dil_pricereduced:1#pageSize=96&beginIndex=0&orderBy=1'
                ]

    def __init__(self):
        self.page_num = 0
        self.ajax_url = 'http://www.dillards.com/shop/DDS_ProductListingView?storeId=301&langId=-1&catalogId=301&requesttype=ddsAjax&resultType=products&pageView=grid&searchTerm=&pageSize=96&beginIndex=%d&orderBy=1&categoryId=410&facet=dil_pricereduced:1&super=women'

    def parse(self, response):
        while 1:
            products = requests.get(self.ajax_url % self.page_num, headers={'X-Requested-With': 'XMLHttpRequest'}).json()['products']
            if len(products) == 0:
                break
            for prod in products:
                item = Product()

                item['Name'] = prod['name']
                item['original_url'] = 'http://www.dillards.com/p/' + prod['nameForURL'] + '/' + prod['catentryId'] + '?di=' + prod['fullImage'] + '&categoryId=410&facetCache=pageSize=96&beginIndex=%d&orderBy=1' % self.page_num
                item['reg_price'] = re.sub('[^\d\.]', '', prod['listMax'])
                item['sale_price'] = re.sub('[^\d\.]', '', prod['offerMin'])
                item['website_id'] = 10
                item['category_id'] = 2

                yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            self.page_num = self.page_num + len(products)
            # break

    # def parse(self, response):
    #     sel = Selector(response)
    #     products = sel.xpath('//div[@id="result-row"]/ul/li/div[@class="product-tile"]/figure/figcaption[@class="item-info"]')
    #     print len(products)
    #     valid_products_num = len(products)
    #     # return
    #     if len(products) != 0:
    #         for prod in products:
    #             try:
    #                 item = Product()
    #                 item['Name'] = prod.xpath('a/span[@class="product-name"]/text()').extract_first().strip()
    #                 item['original_url'] = response.urljoin(prod.xpath('a/span[@class="product-name"]/../@href').extract_first()).strip()
    #                 item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('a/div[@class="price-wrapper"]/span[@class="price original-price"]/span[@class="price-number"]/@data-range1').extract_first()).strip()
    #                 item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('a/div[@class="price-wrapper"]/span[@class="price now-price"]/span[@class="price-number"]/text()').extract_first().split('-')[0]).strip()
    #                 item['website_id'] = 10
    #                 item['category_id'] = 2

    #                 print item['Name'] + ' -> ' + item['original_url']
    #                 # print prod.xpath('.//text()').extract()
    #                 yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
    #                 # break
    #             except:
    #                 valid_products_num = valid_products_num - 1
    #         # return

    #         try:
    #             self.page_num = self.page_num + valid_products_num
    #             nextpage_url = 'http://www.dillards.com/c/women?facet=dil_pricereduced:1#pageSize=96&beginIndex=%d&orderBy=1' % self.page_num
    #             print 'nextpage -> ' + nextpage_url
    #             yield Request(nextpage_url, callback=self.parse, dont_filter=True)
    #         except:
    #             pass

    def parse_detail(self, response):
        sel = Selector(response)
        item = response.meta['item']

        item['description'] = ' '.join([frag.strip() for frag in sel.xpath('//div[@id="productpage-accordion"]//div[@id="description-panel"]//text()').extract()])
        image_url = sel.xpath('//div[@id="productImageContain"]//div[@class="mainProductImage"]/img[@class="mainImage"]/@src').extract_first()
        if 'https:' not in image_url:
            image_url = 'https:' + image_url
        item['original_image_url'] = [image_url]
        item['image_urls'] = item['original_image_url']

        yield item
