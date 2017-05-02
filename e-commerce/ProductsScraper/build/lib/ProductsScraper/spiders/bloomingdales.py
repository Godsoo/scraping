import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *

class BloomingdalesSpider(scrapy.Spider):
    name = "bloomingdales"
    
    start_urls = ["http://www1.bloomingdales.com/shop/sale/women?id=3985&cm_sp=NAVIGATION-_-TOP_NAV-_-3977-SALE-%26-CLEARANCE-Women"]

    def parse(self, response):
        sel = Selector(response)
        
        # f=open("page_source.html",'w+b')
        # f.write(response.body)
        
        all_divs = sel.xpath('//ul[@id="thumbnails"]/li')
        
        for a in all_divs:
            Name = a.xpath('div/div[@class="shortDescription newProdDesc"]/div[@id="prodName"]/a/text()').extract()
            description = ""
            reg_price = a.xpath('div/div[@class="prices"]/div[@class="priceSale colorwayBrowse"]/div/text()').extract()
            sale_price = a.xpath('div/div[@class="prices"]/div[@class="priceSale colorwayBrowse"]/div/span[@class="priceSale"]/text()').extract()
            website_id = 6
            brand = a.xpath('div/div[@class="shortDescription newProdDesc"]/div[@id="brandName"]/a/text()').extract()
            original_url = a.xpath('div/div[@class="shortDescription newProdDesc"]/div[@id="prodName"]/a/@href').extract()
            original_url = "".join(original_url).strip()
            original_image_url = ""
            category_id = 2
            
            try:
                reg_price = "".join(reg_price).strip().replace('$','').strip().split(' ')[1].strip()
            except:
                pass

            try:
                sale_price = "".join(sale_price).strip().replace('$','').strip().split(' ')[1].strip()
            except:
                pass

            item = Product()
            item['Name'] = "".join(Name).strip()
            item['reg_price'] = reg_price
            item['sale_price'] = sale_price
            item['brand'] = "".join(brand).strip()
            item['original_url'] = original_url
            item['website_id'] = website_id
            item['category_id'] = category_id

            yield Request(original_url, meta={'item':item}, callback=self.each_detail)

            # break

        try:
            next_page = sel.xpath('//link[@rel="canonical"]/@href').extract()
            current_page_no = sel.xpath('//li[@class="currentPage displayNone"][1]/text()').extract()

            temp_page = sel.xpath('//select[@id="paginationDdl"]/option/@value').extract()
            max_page_no = temp_page[len(temp_page) - 1]

            if int("".join(current_page_no).strip()) < int("".join(max_page_no).strip()):
                current_page_no = int("".join(current_page_no).strip()) + 1
                temp_link = "".join(next_page).strip().split('?id')[0].strip() + "/Pageindex/" + str(current_page_no) + "?id=" + "".join(next_page).strip().split('?id=')[1].strip()
                yield Request(temp_link, callback=self.parse)
        except:
            pass

    def each_detail(self, response):
        sel = Selector(response)

        # f=open("page_source.html",'w+b')
        # f.write(response.body)
    
        temp_Desc = sel.xpath('//div[@id="pdp_tabs_body_details"]')

        description = []
        for t in temp_Desc:
            description.append("\n".join(t.xpath('string()').extract()).strip().replace(u'\xa0',' ').strip())

        original_image_url = sel.xpath('//div[@id="zoomerDiv"]/img[@id="productImage"][1]/@src').extract()

        item = response.meta['item']

        item['description'] = "".join(description).strip()
        item['original_image_url'] = ["".join(original_image_url).strip()]
        item['image_urls'] = item['original_image_url']

        yield item