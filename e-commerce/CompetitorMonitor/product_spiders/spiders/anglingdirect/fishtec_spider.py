import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from scrapy.http import FormRequest

class fishtec_spider(BaseSpider):
    name = 'fishtec.co.uk'
    allowed_domains = ['fishtec.co.uk', 'www.fishtec.co.uk']
    start_urls = ('http://www.fishtec.co.uk',)
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        
        #categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//ul[@id="menu"]/li/div/div/ul/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url))
            
        #additional categories
        
        acategory_urls = hxs.select('//div[@class="sidemenu"]/div/div/h3/a/@href').extract()
        for aurl in acategory_urls:
            yield Request(urljoin_rfc(base_url, aurl))
        
        #products
        products = hxs.select('//div[@class="prodbox"]/p[@class="prodTitle"]/a/@href').extract()
        for url in products:
            url_product = urljoin_rfc(base_url, url)
            yield Request(url_product, callback=self.parse_product)

        pages = hxs.select('//input[@id="pageButton" and not(@style)]/@value').extract()
        crawled_pages = response.meta.get('crawled_pages', [])
        for page in pages:
            if page not in crawled_pages:
                formdata = {'page':page, 'sortBy': 'popular'}
                crawled_pages.append(page)
                yield FormRequest(response.url, formdata=formdata, dont_filter=True, meta={'crawled_pages':crawled_pages})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        image_url = hxs.select(u'//img[@id="zoomImage"]/@src').extract() 
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        '''
        if not image_url:
            image_url = hxs.select(u'//div[@class="mainimgborderdiv"]/img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        '''
        category = hxs.select(u'//p[contains(@class,"crumbs")]/span/a/span/text()').extract()
        category = category[-1] if category else ''

        name = hxs.select('//input[@name="name"]/@value').extract()
        if not name:
            retry_count = int(response.meta.get('retry_count', '0'))
            retry_count += 1
            if retry_count < 10:
                yield Request(response.url, callback=self.parse_product, meta={'retry_count': retry_count})
            else:
                self.log('Warning! Maximum retry count reached: {}'.format(response.url))
            return

        options = hxs.select("//select[@name='box1']/option")[1:]
        if options:
            i = 0
            product_codes = hxs.select(u'//td[font[*[contains(text(),"Code")]]]/../../tr/td[last()]/text()').extract()
            #options
            '''
            if not name:
                name = hxs.select("//h1[@class='productNameDN']/text()").extract()
            '''
            url = response.url
            for option in options:
                loader = ProductLoader(item=Product(), selector=hxs)
                identifier = option.select('./@value')[0].extract()
                option = option.select('./text()')[0].extract()
                name2 = re.match(r'(.*) -.*',option.strip())
                stock = re.search('\( ?(\d+).? in stock', option.replace('\n', '').replace('\t', ' '))
                stock = stock.group(1) if stock else 0
                if name2:
                    name2 = name2.group(1)
                else:
                    continue
                price = re.match(r'.*\xa3(.*)',option.replace("\r","").replace("\n","").strip())
                price = price.group(1) if price else None
                if not price:
                    price = "".join(hxs.select("//p[@class='ProductDetailPrice']/a/font[@class='BodyMain']/text()").re(r'\xa3([0-9\,\. ]+)')).strip()
                    if not price:
                        price = "".join(hxs.select('//p[@class="ProductDetailPrice"]/font[1]/b/text()').re(r'\xa3([0-9\,\. ]+)')).strip()
                        if not price:
                            price = "".join(hxs.select('//div[@class="priceBox"]/p/b/text()').re(r'\xa3([0-9\,\. ]+)')).strip()
                loader.add_value('url', urljoin_rfc(base_url,url))
                loader.add_value('name', name[0].strip() + u' ' + name2)
                loader.add_value('price', price)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('stock', int(stock))
                try:
                    sku = product_codes[i] if product_codes else ''
                except IndexError:
                    sku = ''
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                if image_url:
                    loader.add_value('image_url', image_url)
                if loader.get_output_value('identifier'):
                    yield loader.load_item()
                i += 1
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            '''
            name = hxs.select("//div[@class='buybox']/table/tr/td/h1/text()").extract()
            if not name:
                name = hxs.select("//h1[@class='productNameDN']/text()").extract()
                if not name:
                    name = hxs.select("//div[@class='buybox']/table/tr/td/table/tr/td/h1/text()").extract()
            '''
            url = response.url
            price = hxs.select('//div[@class="priceBox"]/p/b/text()').extract()
            price = price[0] if price else ''
            '''
            if not price:
                price = "".join(hxs.select("//p[@class='ProductDetailPrice']/a/font[@class='BodyMain']/text()").re(r'\xa3([0-9\,\. ]+)')).strip()
                if not price:
                    price = "".join(hxs.select('//p[@class="ProductDetailPrice"]/strong/font/b/text()').re(r'\xa3([0-9\,\. ]+)')).strip()
                    if not price:
                        price = "".join(hxs.select('//p[@class="ProductDetailPrice"]/font[@color="Black"]/b/text()').re(r'\xa3([0-9\,\. ]+)')).strip()
            '''
            loader.add_value('url', urljoin_rfc(base_url,url))
            loader.add_value('name', name[0].strip())
            loader.add_value('price', price)
            loader.add_xpath('identifier', u'//input[@type="hidden" and @name="theprodcode"]/@value')
            loader.add_xpath('sku', u'//input[@type="hidden" and @name="theprodcode"]/@value')
            in_stock = hxs.select('//div[@id="buyBox"]/p/b[contains(text(), "IN STOCK")]')
            if not in_stock:
                stock = hxs.select(u'//div[@id="buyBox"]/p/b/text()').re('\d+')
                stock = int(stock[0]) if stock else 0
                loader.add_value('stock', stock)
            loader.add_xpath('sku', u'//input[@type="hidden" and @name="SkuRecNum"]/@value')
            loader.add_value('category', category)
            if image_url:
                loader.add_value('image_url', image_url)
            if loader.get_output_value('identifier'):
                yield loader.load_item()
