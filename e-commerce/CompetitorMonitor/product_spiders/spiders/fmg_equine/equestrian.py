# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.url import canonicalize_url
from scrapy.http import Request, FormRequest
from urlparse import urljoin
from scrapy import log
import re, json, logging

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.spiders.BeautifulSoup import BeautifulSoup


class EquestrianSpider(BaseSpider):

    name              = "equestrian"
    allowed_domains   = ["equestrian.com"]
    start_urls        = ["http://www.equestrian.com/page/brands-all/"]
    base_url          = "http://www.equestrian.com"
    download_delay    = 2

    seen              = []


    def __init__(self, *args, **kwargs):
        super(EquestrianSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)


    def spider_idle(self):

        categories = ['http://www.equestrian.com/c/Womens/Womens-Riding-Wear/',
                      'http://www.equestrian.com/c/Womens/Womens-Leisure-Wear/',
                      'http://www.equestrian.com/c/Mens/Mens-Riding-Wear/',
                      'http://www.equestrian.com/c/Mens/Mens-Leisure-Wear/',
                      'http://www.equestrian.com/c/Childrens/Childs-Riding-Wear/',
                      'http://www.equestrian.com/c/Childrens/Childs-Leisure-Wear/',
                      'http://www.equestrian.com/c/Horse/Rugs/',
                      'http://www.equestrian.com/c/Horse/Boots-Wraps/',
                      'http://www.equestrian.com/c/Horse/Grooming/',
                      'http://www.equestrian.com/c/Horse/Tack/',
                      'http://www.equestrian.com/c/Horse/Horsewear/',
                      'http://www.equestrian.com/c/Stable-Field/Stable/',
                      'http://www.equestrian.com/c/Stable-Field/Tack-Feed-Room/',
                      'http://www.equestrian.com/c/Stable-Field/Field/',
                      'http://www.equestrian.com/c/Stable-Field/Arena/',
                      'http://www.equestrian.com/c/Stable-Field/Trailer',
                      'http://www.equestrian.com/c/Stable-Field/Horse-Toys/',
                      'http://www.equestrian.com/c/Stable-Field/Veterinary/',
                      'http://www.equestrian.com/c/Pets/Dogs/',
                      'http://www.equestrian.com/c/Pets/Cats/',
                      'http://www.equestrian.com/c/Gifts/For-Her/',
                      'http://www.equestrian.com/c/Gifts/For-Him/',
                      'http://www.equestrian.com/c/Gifts/For-Kids/']

        for category in categories:
            yield Request(url=category, meta={'brand': ''}, callback=self.parse_brand)


    def parse(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        brands = hxs.select("//section[@id='All']//ul[@class='BrandCol1']//a")
        soup = BeautifulSoup(response.body)

        for brand in brands:

            link  = urljoin_rfc(base_url, brand.select("./@href").extract()[0].replace('//', '/'))
            log.msg(link)
            brand = brand.select("./text()").extract()[0]
            yield Request(url=link, meta={'brand': brand}, callback=self.parse_brand, priority=10)

        if soup.find('section', id='All'):
            brands = [(brand.text, brand['href']) for brand in soup.find('section', id='All').findAll('a')]
            for brand, link in brands:
                yield Request(urljoin_rfc(base_url, link.replace('//', '/')), meta={'brand': brand}, callback=self.parse_brand, priority=10)

    def parse_brand(self, response):

        hxs      = HtmlXPathSelector(response)
        products = hxs.select("//h2[@class='product-name fn']")
        brand    = response.meta['brand']
        base_url = get_base_url(response)

        if not products:
	    for url in hxs.select('//a[text()="SHOP ALL" or text()="SHOP NOW"]/@href').extract():
		yield Request(urljoin(base_url, url), meta=response.meta, callback=self.parse_brand)
            try:
                hxs = HtmlXPathSelector(text=json.loads(response.body)['productList'])
                products = hxs.select("//h2[@class='product-name fn']")
            except Exception as e:
                print e

        for product in products:

            name = product.select("./a/text()").extract()[0]
            url  = product.select("./a/@href").extract()[0]

            if not url in self.seen:
                self.seen.append(url)
                yield Request(url=url, meta={'name': name, 'brand': brand}, callback=self.parse_item)

        if 'pageSize' in response.url:
            next_page = hxs.select('//li[@class="next  last-child"]/a[@class="ir"]/@href').extract()
            if next_page:
                yield Request(urljoin_rfc(base_url, next_page[0]))

        # shop now link
        shop_now_link = hxs.select('//div[@class="whole-banner-brands-e"]/div[contains(@class,"circle-link")]/a/@href').extract()
        if shop_now_link:
            log.msg(shop_now_link)
            yield Request(urljoin_rfc(base_url, shop_now_link[0]))

        if not products and not shop_now_link:
            retries = response.meta.get('retries', 0)
            if retries < 3:
                meta = response.meta
                meta['retries'] = retries + 1
                log.msg('[{}] Retry attempt {}'.format(response.url, retries))
                yield Request(response.url, callback=self.parse_brand, meta=meta, dont_filter=True)

        view_all = hxs.select('//a[text()="View All"]/@href')
        if view_all:
            url = urljoin_rfc(self.base_url, view_all[0].extract())
            meta = response.meta
            meta['brand'] = brand
            yield Request(url, callback=self.parse_brand, meta=response.meta)
        #== Paging works awful on this website, we need to parse JSON response instead ==#
        # try:
        #     hxs = HtmlXPathSelector(text=json.loads(response.body)['pagination'])
        # except:
        #     pass
        # try:
        #     next_page_value = hxs.select("//div[@class='view-up-to']/@data-ajax-url").extract()[0]
        #     next_page_value = next_page_value.replace('beginIndex=1', 'beginIndex=0').replace('searchType=0', 'searchType=IncludeImplicitSKU')
        #     next_page = hxs.select("//ul[@class='controls']//a[text()='next']/@href").extract()[0]
        #     next_page = next_page_value + '&' + re.findall(re.compile("\?(.+?$)"), next_page)[0]
        #     yield Request(next_page, meta={'brand': brand}, callback=self.parse_brand)
        # except Exception as e:
        #     logging.error(e)
        #     pass



    def parse_item(self, response):

        hxs   = HtmlXPathSelector(response)
        name  = response.meta.get('name', "")
        url   = response.url
        
        try:
            sku = hxs.select("//div[@id='productIdentifier']/@data-product-id").extract()[0]
        except:
            return

        stock = 0 if 'out of stock' in response.body.lower() else 1

        categories = hxs.select("//div[@class='breadcrumb']/ol/li")[1:-1]
        categories = [category.select("./text()").extract()[0] for category in categories]
        try:
            image_url  = hxs.select("//div[@id='Product_Image']//img[1]/@src").extract()[0]
            image_url  = image_url[2:] if image_url[:2] == '//' else image_url
            image_url  = 'http://' + image_url
        except:
            image_url  = ''
        brand      = response.meta.get('brand', "")

        try:
            options    = hxs.select("//div[contains(@id,'jsonPrices_{}')]/text()".format(sku)).extract()[0]
            options    = json.loads(options)['productPrices']
        except:
            return

        try:
            attributes = hxs.select("//div[contains(@id,'jsonAttributes_{}')]/@data-json-object".format(sku)).extract()[0]
            attributes = json.loads(attributes)['skus']
        except:
            return

        if options:
            for option in options:

                l = ProductLoader(item=Product(), response=response)

                option_id     = option['itemCatentryId']
                option_price  = option['pricing']['nowPrice']

                option_name   = ''

                try:
                    for attribute in attributes:
                        if attribute['catentry_id'] == option_id:
                            for k,v in attribute['Attributes'].iteritems():
                                if not k.split('_')[0] == 'Style':
                                    option_name += ' {}'.format(k.split('_')[1])
                except:
                    pass

                sku_tmp = sku + '-' + str(option_id)

                l.add_value('image_url',     image_url)
                l.add_value('url',           url)
                l.add_value('price',         option_price)
                l.add_value('stock',         stock)
                l.add_value('brand',         brand)
                l.add_value('identifier',    sku_tmp)
                l.add_value('sku',           sku_tmp)
                l.add_value('name',          name + option_name)

                for category in categories:
                    l.add_value('category', category)

                yield l.load_item()

        else:

            l = ProductLoader(item=Product(), response=response)

            price = hxs.select("//li[contains(@class,'price-now')]//span[@class='integer']/text()").extract()[0].strip().replace('[', '').replace(']', '')
            
            l.add_value('image_url',     image_url)
            l.add_value('url',           url)
            l.add_value('price',         price)
            l.add_value('stock',         stock)
            l.add_value('brand',         brand)
            l.add_value('identifier',    sku)
            l.add_value('sku',           sku)
            l.add_value('name',          name)

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()