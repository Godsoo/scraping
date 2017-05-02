import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *

class BarneyswarehouseSpider(scrapy.Spider):
    name = "barneyswarehouse"
    start_urls = ["http://www.barneyswarehouse.com/category/clearance/women/clothing/N-jkxhqd?recordsPerPage=96&page=1"]

    def parse(self, response):
        print response.url
        sel = Selector(response)
        
        # f=open("page_source.html",'w+b')
        # f.write(response.body)
        
        all_divs = sel.xpath('//div[@id="atg_store_prodList"]/ul/li')
   
        for a in all_divs:
            Name = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="product-name"]/a/text()').extract()
            description = ""
            reg_price = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="product-pricing"]/div[@class="product-standard-price"]/span[@class="product-discounted-price"]/text()').extract()
            sale_price = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="product-pricing"]/div[@class="product-standard-price"]/span[@class="product-sales-price"]/text()').extract()
            website_id = 3
            brand = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="brand"]/a/text()').extract()
            original_url = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="product-name"]/a/@href').extract()
            original_url = "http://www.barneyswarehouse.com" + "".join(original_url).strip()
            original_image_url = ""
            category_id = 2
            discount = a.xpath('div[@class="product-tile "]/div[@class="wrap-desc"]/div[@class="product-pricing"]/div[@class="product-standard-price"]/text()').extract()
            discount = "".join(discount).strip().replace('Off','').replace('%','').strip()

            item = Product()
            item['Name'] = "".join(Name).strip()
            item['reg_price'] = "".join(reg_price).strip().replace('$','').strip()
            item['sale_price'] = "".join(sale_price).strip().replace('$','').strip()
            item['brand'] = "".join(brand).strip()
            item['original_url'] = original_url
            item['discount'] = discount
            item['website_id'] = website_id
            item['category_id'] = category_id

            print 'yield Request(original_url, meta={\'item\': item}, callback=self.each_detail)'
            yield Request(original_url, meta={'item': item}, callback=self.each_detail)

            # break

        current_page_no = sel.xpath('//input[@id="currentPageNumber"][1]/@value').extract()
        max_page_no = sel.xpath('//input[@id="currentPageNumber"][1]/@max').extract()
        try:
            if int("".join(current_page_no).strip()) < int("".join(max_page_no).strip()):
                current_page_no = int("".join(current_page_no).strip()) + 1
                temp_link = response.url.split('&page=')[0].strip() + "&page=" + str(current_page_no)
                yield Request(temp_link, callback=self.parse)
        except:
            pass
    
    def each_detail(self, response):
        sel = Selector(response)
        print response.url

        # f=open("page_source.html",'w+b')
        # f.write(response.body)
    
        temp_Desc = sel.xpath('//div[@class="pdpReadMore"]/div[1]')

        description = []
        for t in temp_Desc:
            description.append("\n".join(t.xpath('string()').extract()).strip().replace(u'\xa0',' ').strip())

        original_image_url = sel.xpath('//li[@class="row"]/img[@class="primary-image"][1]/@src').extract()

        item = response.meta['item']
        item['description'] = "".join(description).strip()
        item['original_image_url'] = ["".join(original_image_url).strip()]
        yield item