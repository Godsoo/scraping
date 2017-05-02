import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse,Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product,ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.join(os.path.abspath(os.path.dirname(__file__)))

class FourxFourTyresUK(BaseSpider):
    name = '4x4tyres.co.uk'
    allowed_domains = ['4x4tyres.co.uk']
    start_urls = ['https://www.4x4tyres.co.uk/advanced_search_result.php?finder=1&4=any&5=any&6=any&sort=2a&page=1']
    index = 1

    def __init__(self, *args, **kwargs):
        super(FourxFourTyresUK, self).__init__(*args, **kwargs)
        self.skus = {}
        with open(os.path.join(HERE, '4x4tyres_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.skus[row['product_name'].strip()] = row['product_sku'].strip()



    def parse(self,response):
        # self. = SSL.SSLv23_METHOD
        self.index+=1
        if self.index > 1:
            self.log('Currently Process URL:-'+response.url+'\n')
            #self.log('Iteration Number:'+str(self.index))
            self.log('\n\n')
            base_url = get_base_url(response)
            hxs = HtmlXPathSelector(response)
            product_urls = hxs.select('//*[contains(@class, "contentText")]/table/tr/td/div/div/div/h2/a/@href').extract()
            html = response.body
            #self.log(html+'\n\n')
            #self.log('BASE URL ->'+base_url+'\n')
            for product_url in product_urls:
                yield Request(product_url, callback=self.parse_product)

            next_page = hxs.select('//*[contains(text(),"[Next")]/text()').extract()
            #if next_page and self.index < 2:
            if 'Next&nbsp;&gt;&gt' in html:
                url = base_url+'advanced_search_result.php?finder=1&4=any&5=any&6=any&sort=2a&page='+str(self.index)
                # self.log('NEXT Process URL:-'+url+'\n')
                yield Request(url, callback=self.parse)
                # self.log('Yea We Found it')
            else:
                self.log('NOTHING EXIST!!!!')
                #self.index = -1

    def parse_product(self,response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs,item=Product())

        category = ''
        brand = ''
        name = ''
        stockk = 0
        price = 0
        identifier = ''
        image_url = ''

        name = hxs.select('//*[@id="bodyContentfullWidth"]/form/div[1]/h1/text()').extract()[0].strip().encode('ascii','ignore')
        brand = hxs.select('//*[@id="infotab1"]/div[2]/ul/li[4]/span[2]/a/text()').extract()
        if brand:
            brand = brand[0].strip()

        price = hxs.select('//*[@id="bodyContentfullWidth"]/form/div[2]/div/div[2]/div[2]/div[1]/div/div/text()').extract()[0].encode('ascii','ignore')
        price = price.replace('\xa3','').strip().encode('ascii','ignore')
        stock = hxs.select('//*[@id="infotab1"]/div[2]/ul/li[5]/span[2]/text()').extract()
        if stock:
            stock = stock[0]
            if 'Yes' in stock:
                stock = 1
            else:
                stock = 0

        identifier = hxs.select('//input[@type="hidden"][@name="products_id"]/@value').extract()[0].strip()
        category = hxs.select('//*[@id="infotab1"]/div[2]/ul/li[2]/span[2]/text()').extract()[0].strip()
        image_url = base_url+hxs.select('//*[@id="piGal"]/a/img/@src').extract()[0]

        loader.add_value('name',name)
        loader.add_value('image_url',image_url)
        loader.add_value('sku', self.skus.get(name.strip(), ''))
        loader.add_value('url',response.url)
        loader.add_value('price',price)
        loader.add_value('stock',stock)
        loader.add_value('category',category.strip())
        loader.add_value('brand',brand)
        # Add 'new_id' string to avoid duplciates with old products
        loader.add_value('identifier', 'new_id_' + str(identifier))
        yield loader.load_item()
