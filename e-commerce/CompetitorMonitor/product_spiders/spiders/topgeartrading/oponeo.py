from scrapy import Spider, Request, FormRequest
from product_spiders.items import Product, ProductLoader


class OponeoSpider(Spider):
    name = 'topegeartrading-oponeo.co.uk'
    allowed_domains = ['oponeo.co.uk']
    start_urls = ('http://www.oponeo.co.uk',)

    download_delay = 1
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'
    
    exclude_word = 'DOT'
    
    def __init__(self, *args, **kwargs):
        super(OponeoSpider, self).__init__(*args, **kwargs)

        self.current_cookie = 0

    def start_requests(self):
        search_url = 'http://www.oponeo.co.uk/tyre-finder/s=3/summer,winter,all-season/t=1/car,van,4x4/r=1/145-80-r10'
        self.current_cookie += 1
        yield Request(search_url,
                      meta={'cookiejar': self.current_cookie,
                            'category': 'Car tyres'},
                      callback=self.parse_cartyres)

        cats_urls = [
            ('Alloy Wheels', 'http://www.oponeo.co.uk/alloy-wheels-finder'),
            ('Steel Wheels', 'http://www.oponeo.co.uk/steel-wheels-finder'),
        ]
        for cat_name, cat_url in cats_urls:
            self.current_cookie += 1
            yield Request(cat_url,
                          meta={'cookiejar': self.current_cookie,
                                'category': cat_name})

    def parse(self, response):
        products = response.xpath('//*[@id="productList"]//div[contains(@class, "item")]//div[@class="productName"]//a/@href').extract()
        if not products:
            products = response.xpath('//div[@class="productName"]//h4/a/@href').extract()

        for product_url in products:
            yield Request(response.urljoin(product_url), callback=self.parse_product, meta=response.meta)

        is_next_page = response.meta.get('is_next_page', False)
        next_page = response.xpath('//li[contains(@class, "next") and contains(@class, "nextItem")]/a/@id').extract()
        if next_page:
            meta = response.meta.copy()
            if not is_next_page:
                meta['is_next_page'] = True
                meta['main_response'] = response
            next_page_id = next_page[0]
            req = FormRequest.from_response(meta['main_response'], formname='form1',
                formdata={'__ASYNCPOST': 'true', '__EVENTTARGET': next_page_id, '__EVENTARGUMENT': ''},
                headers={'X-MicrosoftAjax': 'Delta=true', 'X-Requested-With': 'XMLHttpRequest',
                         'User-Agent': response.request.headers['User-Agent']},
                meta=meta,
                dont_filter=True)
            yield req

    def parse_cartyres(self, response):
        search_url = 'http://www.oponeo.co.uk/tyre-finder/s=3/summer,winter,all-season/t=1/van,car,4x4/r=1/%s'
        for opt in response.xpath('//li[input and contains(@id, "flTr_olSize")]/label/@title').extract():
            self.current_cookie += 1
            search_opt = opt.lower().replace('/', ' ').replace('.', '-').replace(' ', '-').replace('--', '-').replace('x', '-')
            yield Request(search_url % search_opt,
                          meta={'cookiejar': self.current_cookie,
                                'category': response.meta['category']})

        for p in self.parse(response):
            yield p

    def retry_request(self, response):
        try_no = response.meta.get('try', 1)
        if try_no < self.max_retry_count:
            meta = {
                'try': try_no + 1
            }
            meta['recache'] = True
            self.log("[WARNING] Retrying. Failed to scrape product page: %s" % response.url)
            return Request(response.url,
                           meta=meta,
                           callback=self.parse_product,
                           dont_filter=True)
        else:
            self.log("[WARNING] Gave up. Failed to scrape product page: %s" % response.url)
            self.errors.append("Failed to scrape product page: %s" % response.url)

        return None

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), selector=response)
        loader.add_value('url', response.url)

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))

        identifier = response.xpath('//form[@name="form1"]/@action').extract()
        if not identifier:
            yield self.retry_request(response)
            return
        identifier = identifier[0]
        loader.add_value('identifier', identifier)
        price = response.xpath('//*[@class="price"]/*[@class="mainPrice"]/text()')[0].extract()
        loader.add_value('price', price)

        stock = response.xpath('//div[@class="stockLevel"]//text()').re(r'(\d+)')
        if stock:
            loader.add_value('stock', stock[0])

        brand = response.xpath('//*[@itemprop="brand"]/@content').extract()
        if not brand:
            brand = response.xpath('//div[@class="hidden"]/input[@class="producerName"]/@value').extract()
        if brand:
            brand = brand[0].strip()
            loader.add_value('brand', brand)
        if 'category' in response.meta:
            if response.meta['category'] != 'Car tyres':
                loader.add_value('category', response.meta['category'])
            else:
                category = response.xpath('//dt[contains(text(), "Type:")]/following-sibling::dd/text()').extract()
                if category:
                    loader.add_value('category', category[0].strip())
        else:
            loader.add_value('category', loader.get_output_value('brand'))

        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('sku', '//*[@itemprop="sku"]/@content')
        
        if self.exclude_word not in loader.get_output_value('name'):
            yield loader.load_item()
