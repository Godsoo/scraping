import scrapy
from scrapy import FormRequest
from captcha import get_captcha_from_url
import sys
import csv
import re
import os
from scrapy import signals
from collections import defaultdict
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper, AmazonFilter, AmazonUrlCreator, AmazonScraperException
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(scrapy.Spider):
    name = 'sonae-test_amazon.es'
    allowed_domains = ['amazon.es']                  
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/52.0.2743.116 Chrome/52.0.2743.116 Safari/537.36'
    
    search_url = 'https://www.amazon.es/s/ref=nb_sb_noss?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=me%3D{dealer}&field-keywords={search}'
    dealers_url = 'https://www.amazon.es/gp/search/other/ref=sr_sa_p_6?rh=%2Ci%3A{category}&keywords={search}&pickerToList=enc-merchantbin&ie=UTF8'
    main_search_url = 'https://www.amazon.es/s/ref=nb_sb_noss?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&field-keywords={search}'
    
    total_dealers = 0
    asin_sku = {}
    dealer_asins = defaultdict(list)
    amazon_scraper = AmazonScraper()

    def spider_idle(self, spider):
        self.log('Idle called')
        if spider.name == self.name:
            for query in self.get_next_query():
                url = self.search_url.format(dealer=query['dealer'], search='|'.join(query['asins']))
                request = scrapy.Request(url, callback=self.parse_dealer_search, meta=query)
                self._crawler.engine.crawl(request, self)

    def parse_dealer_search(self, response):
        if self.antibot_protection_raised(response, response.body.decode('utf8')):
            yield self.get_antibot_request(response, self.parse_dealer_search)
        else:
            products = self.amazon_scraper.scrape_search_results_page(response)
            self.log('{} products found'.format(len(products['products'])))
            asins_found = []
            for product in products['products']:
                asins_found.append(product['asin'])
                links = product['result'].xpath('.//div[@class="a-row a-spacing-none"]/a[@class="a-size-small a-link-normal a-text-normal"]/@href')
                if len(links) == 1 and 'condition=used' in links[0].extract():
                    self.log('Skipping used item')
                    continue
                loader = ProductLoader(item=Product(), response=response)
                identifier = ':{}:{}'.format(product['asin'], response.meta['dealer'])
                loader.add_value('identifier', identifier)
                loader.add_value('name', product['name'])
                loader.add_value('url', product['url'])
                loader.add_value('image_url', product['image_url'])
                loader.add_value('price', product['price'])
                loader.add_value('sku', self.asin_sku[product['asin']])
                yield loader.load_item()
            
            if len(response.meta['asins']) > 1:
                for asin in response.meta['asins']:
                    if asin not in asins_found:
                        self.log('Asin not found {} {} {}'.format(response.meta['dealer'], asin, response.url))
                        query = {'dealer': response.meta['dealer'], 'asins': [asin]}
                        url = self.search_url.format(dealer=response.meta['dealer'], search=asin)
                        request = scrapy.Request(url, callback=self.parse_dealer_search, meta=query)
                        yield request

    def get_next_query(self):
        query_size = 24

        for dealer in self.dealer_asins:
            i = query_size
            while i < len(self.dealer_asins[dealer]):
                q = {'asins': self.dealer_asins[dealer][i - query_size : i], 'dealer': dealer}
                yield q
                i += query_size

            q = {'asins': self.dealer_asins[dealer][i - query_size : i], 'dealer': dealer}
            yield q

    def get_antibot_request(self, response, callback):
        self.log('ANTIBOT raised {}'.format(response.url))    
        captcha_url = response.xpath('//img[contains(@src, "captcha")]/@src').extract()[0]
        self.log('Getting captcha')
        captcha = get_captcha_from_url(captcha_url)
        self.log('Captcha: {}'.format(captcha))
        r = FormRequest.from_response(response, formdata={'field-keywords': captcha}, dont_filter=True,
                callback=callback, meta=response.meta)
        return r


    def start_requests(self):
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        f = open(os.path.join(HERE, 'worten_products.csv'))
        reader = csv.DictReader(f)
        for row in reader:
            search_url = self.main_search_url.format(search=row['sku'])
            yield scrapy.Request(search_url, meta={'sku': row['sku']}, callback=self.check_sku)

    def check_sku(self, response):
        if self.antibot_protection_raised(response, response.body.decode('utf8')):
            yield self.get_antibot_request(response, self.check_sku)
        else:
            results = response.xpath('//li[@data-asin]/@data-asin')
            products = self.amazon_scraper.scrape_search_results_page(response)
            self.log(str(products))

            if not results:
                self.log('No results found for {}'.format(response.meta['sku']))
            else:
                asins = []
                for result in results.extract():
                    self.asin_sku[result] = response.meta['sku']
                    asins.append(result)
                
                url = response.xpath('//a[contains(text(), "Ver todos los productos")]/@href')
                if not url:
                    url = response.xpath('//a[contains(text(), "Ver los") and contains(text(), "resultados")]/@href')
                if url:
                    self.log('Category found')
                    url = url.extract()[0]
                    category = re.search('rh=k%3A.*3A(.*)&k', url).groups(0)
                    self.log('Category: {}'.format(category))
                    meta = response.meta.copy()
                    meta['asins'] = asins
                    yield scrapy.Request(self.dealers_url.format(category=category[0], search=response.meta['sku']),
                                         callback=self.parse_dealers, meta=meta)
                else:
                    self.log('Category not found!')

    def parse_dealers(self, response):
        if self.antibot_protection_raised(response, response.body.decode('utf8')):
            yield self.get_antibot_request(response, self.parse_dealers)
        else:
            dealers = response.xpath('//span[@class="a-list-item"]/a[not(@title="Amazon.es")]')
            dealers = [re.search('6%3A([A-Z0-9]+)', d.xpath('./@href').extract()[0]).groups()[0] for d in dealers]
            dealers = [d for d in dealers if d != 'A6T89FGPU3U0Q'] # Remove amazon used dealer
            if len(dealers) >= 47:
                self.log('Too many dealers')
                dealer_pages = response.xpath('//span[@class="pagnLink"]/a/@href').extract()
                for d in dealer_pages:
                    yield scrapy.Request(response.urljoin(d), meta={'current_dealers': dealers[:],
                                                                    'sku': response.meta['sku'],
                                                                    'asins': response.meta['asins']},
                                                                    callback=self.parse_dealers)
            else:
                self.total_dealers += len(dealers)
                self.log('{} dealers found'.format(len(dealers)))
                self.log('{} total dealers'.format(self.total_dealers))
                for d in dealers:
                    self.dealer_asins[d] += response.meta['asins']

    def antibot_protection_raised(self, response, text):
        if u'Sorry, we just need to make sure' in text:
            if u're not a robot' in text:
                return True
                
        # general solution
        #hxs = HtmlXPathSelector(text=text)
        if response.xpath("//input[@id='captchacharacters']").extract():
            return True

        return False