import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *

class AnthropologieSpider(scrapy.Spider):
    name = "anthropologie"
    start_urls = ["https://www.anthropologie.com/sale-clothing"]

    def parse(self, response):
        sel = Selector(response)
        
        # f=open("page_source.html",'w+b')
        # f.write(response.body)
        
        all_divs = sel.xpath('//div[@class="dom-category-browse"]/div[2]/div')
        print len(all_divs)

        for a in all_divs:
            Name = a.xpath('span[@itemprop="product"]/div[@class="c-product-tile-details c-product-tile-details--regular"]/a/h3/span/text()').extract()
            description = ""
            reg_price = a.xpath('span[@itemprop="product"]/div[@class="c-product-tile-details c-product-tile-details--regular"]/p[@class="c-product-tile__price c-product-tile__price--regular"]/span/span[@class="c-product-meta__original-price"]/text()').extract()
            sale_price = a.xpath('span[@itemprop="product"]/div[@class="c-product-tile-details c-product-tile-details--regular"]/p[@class="c-product-tile__price c-product-tile__price--regular"]/span/span[@class="c-product-meta__current-price c-product-meta__current-price--sale"]/text()').extract()
            website_id = 5
            brand = "Anthropologie"
            original_url = a.xpath('span[@itemprop="product"]/div[@class="c-product-tile-details c-product-tile-details--regular"]/a/@href').extract()
            original_url = "https://www.anthropologie.com" + "".join(original_url).strip()
            original_image_url = ""
            category_id = 2
            original_image_url = "".join(a.xpath('span[@itemprop="product"]/div[@class="c-product-tile-controls__link-wrap js-product-tile-controls__link-wrap"]/a/img/@src').extract()).strip()
            if 'https:' not in original_image_url:
                original_image_url = 'https:' + original_image_url
            
            item = Product()
            item['Name'] = "".join(Name).strip()
            item['reg_price'] = "".join(reg_price).strip().replace('$', '').strip()
            item['sale_price'] = "".join(sale_price).strip().replace('$', '').strip()
            item['brand'] = "".join(brand).strip()
            item['original_url'] = original_url
            item['website_id'] = website_id
            item['category_id'] = category_id
            item['original_image_url'] = [original_image_url]

            yield Request(original_url, meta={'item': item}, callback=self.each_detail)

            # break

        next_page = sel.xpath('//a[@aria-label="next page"]/@href').extract()
        if len(next_page) > 0:
            yield Request("https://www.anthropologie.com" + next_page[0], callback=self.parse)

    def each_detail(self,response):
        sel = Selector(response)

        # f=open("page_source.html",'w+b')
        # f.write(response.body)
    
        temp_Desc = sel.xpath('//div[@id="product_description__panel"]')

        description_list = []
        for t in temp_Desc:
            description_list.append("".join(t.xpath('string()').extract()).strip().replace(u'\xa0',' ').strip())

        description = []
        try:
            description_list = "".join(description_list).strip().split('\n')
        except:
            pass
            
        for d in description_list:
            if len("".join(d).strip()) > 0:
                description.append("".join(d).strip())
        
        item = response.meta['item']

        item['description'] = "\n".join(description).strip()
        yield item