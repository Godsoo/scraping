import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *

class MacysSpider(scrapy.Spider):
    name = "macys"
    start_urls = ["https://www.macys.com/shop/womens-clothing/womens-clearance/Pageindex,Productsperpage/1,120?id=24118"]

    def parse(self, response):
        sel = Selector(response)
        
        # f=open("page_source.html",'w+b')
        # f.write(response.body)
        
        all_divs = sel.xpath('//ul[@id="thumbnails"]/li')
        
        for a in all_divs:
            Name = a.xpath('div[@class="innerWrapper"]/div[@class="textWrapper"]/div[@class="shortDescription"]/a/text()').extract()
            description = ""
            reg_price = a.xpath('div[@class="innerWrapper"]/div[@class="textWrapper"]/div[@class="prices"]/span[@class="colorway-price"][1]/span[@class="first-range "]/text()').extract()
            sale_price = a.xpath('div[@class="innerWrapper"]/div[@class="textWrapper"]/div[@class="prices"]/span[@class="colorway-price"]/span[@class="first-range priceSale"]/text()').extract()
            website_id = 4
            brand = ""
            original_url = a.xpath('div[@class="innerWrapper"]/div[@class="textWrapper"]/div[@class="shortDescription"]/a/@href').extract()
            original_url = "https://www.macys.com"+"".join(original_url).strip()
            original_image_url = ""
            category_id = 2
            
            item = Product()
            item['Name'] = "".join(Name).strip()
            
            try:
                reg_price = "".join(reg_price).strip().replace('$','').strip().split(' ')[1].strip()
            except:
                pass

            try:
                sale_price = "".join(sale_price).strip().replace('$','').strip().split(' ')[1].strip()
            except:
                pass

            item['reg_price'] = reg_price
            item['sale_price'] = sale_price
            item['original_url'] = original_url
            item['website_id'] = website_id
            item['category_id'] = category_id

            yield Request(original_url, meta={'item':item}, callback=self.each_detail)

            #break

        try:
            current_page_no = response.url.split('Productsperpage/')[1].strip().split(',')[0].strip()
            max_page_no = response.body.split('totalPageCount:')[1].strip().split(',')[0].strip()

            if int("".join(current_page_no).strip()) < int("".join(max_page_no).strip()):
                current_page_no = int("".join(current_page_no).strip()) + 1
                temp_link = response.url.split('Productsperpage/')[0].strip() + "Productsperpage/" + str(current_page_no) + "," + response.url.split('Productsperpage/')[1].strip().split(',')[1].strip()
                yield Request(temp_link, callback=self.parse)
        except:
            #raise
            pass
    
    def each_detail(self, response):
        sel = Selector(response)

        # f=open("page_source.html",'w+b')
        # f.write(response.body)
    
        temp_Desc = sel.xpath('//div[@id="prdDesc"]')
        if len(temp_Desc) <= 0:
            temp_Desc = sel.xpath('//div[@id="productDetails"]')
            
        description = []
        for t in temp_Desc:
            description.append("\n".join(t.xpath('string()').extract()).strip().replace(u'\xa0',' ').strip())

        original_image_url = sel.xpath('//img[@id="mainView_1"][1]/@src').extract()

        item = response.meta['item']

        item['description'] = "".join(description).strip()
        item['original_image_url'] = ["".join(original_image_url).strip()]
        yield item