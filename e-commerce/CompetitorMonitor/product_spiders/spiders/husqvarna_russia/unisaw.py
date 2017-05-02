# -*- coding: utf-8 -*-
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class unisawSpider(CrawlSpider):
    name = u'unisaw'
    allowed_domains = ['unisaw.ru']
    
    #download_delay = 10
    randomize_download_delay = True
    rotate_agent = True
    
    start_urls = [
        'http://www.shop.unisaw.ru/catalog/'
    ]
    
    categories = LinkExtractor(restrict_css='li.category')
    pages = LinkExtractor(restrict_css='div.pagination')
    products = LinkExtractor(restrict_css='div.product-item', deny='//$')
    
    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))
    
    def _start_requests(self):
        yield Request('http://www.shop.unisaw.ru/catalog/stroitelnaya_tekhnika/bury_ruchnye/?SHOWALL_1=1', callback=self.parse_products_list)

    def _parse(self, response):
        hxs         = HtmlXPathSelector(response)
        base_url    = get_base_url(response)
        
        for x in hxs.select('//div[@class="bx_sitemap"]/ul/li/div[@class="sect-inline"]/ul/li'):
            url     = x.select('./h2//@href').extract()

            yield Request(urljoin_rfc(base_url, url[0]), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs                           = HtmlXPathSelector(response)
        base_url                      = get_base_url(response)
        #base_url                      = '/'.join(base_url.split('/')[:4])
        for x in response.xpath('//section[@class="catalog-catalog-body-item"]'):
            product                   = {}
            product['stock']          = None
            if not x.select('.//span[@class="product-in-store"]'):
                product['stock']      = 0
            product['identifier']     = x.select('.//div[@class="catalog-catalog-body-item-pic"]//@href').extract()
            if product['identifier']:
                product['identifier'] = product['identifier'][0].split('/')[::-1]
            product['name']           = x.select('.//div[@class="catalog-catalog-body-item-name"]/a//text()').extract()
            if product['name']:
                product['name']       = product['name'][0].strip()
            product['price']          = extract_price(''.join(x.select('.//div[@class="catalog-catalog-body-item-price-new" or @class="catalog-catalog-body-item-price-normal"]//text()').extract()).strip().replace(' ', ''))
            product['url']            = urljoin_rfc(base_url, x.select('.//a/@href').extract()[0])

            #time.sleep(random.random()*2.0)
            yield Request(product['url'], callback=self.parse_product, meta={'product': product})

        #pagination
        for url in hxs.select('//div[@class="pager-body"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)


    def parse_product(self, response):
        hxs                           = HtmlXPathSelector(response)
        base_url                      = get_base_url(response)
        base_url                      = '/'.join(base_url.split('/')[:3])
        
        product                       = {}
        
        product['identifier'] = response.xpath('//input[@name="elementID"]/@value').extract_first()
        
        if not response.css('span.product-in-store'):
            product['stock'] = 0
            
        product['name'] = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        
        product['price'] = response.xpath('//meta[@itemprop="price"]/@content').extract_first()
        
        product['url'] = response.url
        
        product['brand']              = hxs.select(u'//dt[contains(., "Производитель")]/following-sibling::dd/span/text()').extract_first()
        if not product['brand']:
            product['brand'] = response.xpath('//span/text()').re_first(u'Другие товары бренда (.+)')
        
        image_url                     = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            product['image_url']      = urljoin_rfc(base_url,image_url[0].strip())
        
        product['sku']                = ''
        product['sku']                           = response.xpath(u'//span[contains(., "Артикул:")]/following-sibling::span/text()').extract_first()
        
        product['category']           = hxs.select('//div[contains(@class, "breadcrumbs")]//span/text()').extract()[-2]

        product_loader                = ProductLoaderWithoutSpaces(item=Product(), selector=hxs)
        for k,v in product.iteritems():
            product_loader.add_value(k, v)
        product                       = product_loader.load_item()
        
        #time.sleep(random.random()*2.0)
        yield product
