from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from urlparse import urljoin
import copy
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc


class WexJohnlewisSpider(BaseSpider):

    name               = 'wexphotographic_new-johnlewis'
    allowed_domains    = ['johnlewis.com']
    start_urls         = ['http://www.johnlewis.com/electricals/televisions/c6000084?rdr=1',
                          'http://www.johnlewis.com/electricals/dvd-blu-ray-home-cinema-sound-bars/c600007?rdr=1',
                          'http://www.johnlewis.com/browse/electricals/freeview-freesat-streaming/_/N-al6',
                          'http://www.johnlewis.com/electricals/tv-stands-accessories/c600009?rdr=1',
                          'http://www.johnlewis.com/electricals/cameras-camcorders/c600006?rdr=1',
                          'http://www.johnlewis.com/electricals/ipods-mp3-players/c60000160?rdr=1',
                          'http://www.johnlewis.com/electricals/headphones/c600002279?rdr=1',
                          'http://www.johnlewis.com/browse/electricals/audio/view-all-radios/_/N-5ajx?intcmp=EHT_sound_vision_nav_allradio_link_x031014',
                          'http://www.johnlewis.com/electricals/audio/c600005?rdr=1',
                          'http://www.johnlewis.com/electricals/sat-nav-gps-navigation-systems/c700001444?rdr=1']
    id_seen            = []


    def start_requests(self):
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/electricals/televisions/c6000084?rdr=1',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.parse_country)

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs   = HtmlXPathSelector(response)

        #== Crawl subcategories ==#
        cat_path = response.url.split('/')[-2]
        for url in hxs.select('//div[@class="col-3 first lt-nav"]//a/@href').extract():
            if ('/' + cat_path + '/') in url:
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse)

        #== Crawl product list ==#
        links = hxs.select('//div[@class="products"]/div/article/a/@href').extract()
        for link in links:
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #== Crawl next page ==#
        tmp = hxs.select('//div[@class="pagination"]//a[@rel="next"]/@href').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="pagination"]//li[@class="next"]/a/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        sub_items = hxs.select('//div[@class="item-details"]//h3/a/@href').extract()
        if sub_items:
            for sub_item in sub_items:
                url = urljoin(response.url, sub_item)
                yield Request(url, callback=self.parse_product)
            return

        option_links = hxs.select('//form[@id="save-product-to-cart"]//div/ul[contains(@class, "selection-grid")]/li/a/@href').extract()
        if not response.meta.get('option', False) and option_links:
            for link in option_links:
                url = urljoin(response.url, link)
                yield Request(url, meta={'option':True}, dont_filter=True, callback=self.parse_product)
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)


        #== Extracting Identifier and SKU ==#
        tmp = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@id="bundle-product-code"]/p/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])


        #== Extracting Product Name ==#
        try:
            name = hxs.select('//h1[@id="prod-title"]/span/text()').extract()[0].strip()
        except:
            try:
                name = hxs.select("//div[@class='mod mod-product-info']/h2/text()").extract()[0].strip()
            except:
                name = hxs.select('//h1[@id="prod-title"]/text()').extract()
                if name:
                    name = name[0].strip()
                else:
                    name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()
                    if name:
                        name = name[0].strip()
                    else:
                        log.msg('### No name at '+ response.url, level=log.INFO)

        tmp = hxs.select('//div[@class="detail-pair"]/p/text()').extract()
        if tmp:
            name += ', ' + tmp[0]
        loader.add_value('name', name)


        #== Extracting Price, Stock & Shipping cost ==#
        price = 0
        tmp   = hxs.select('//div[@class="basket-fields"]/meta[@itemprop="price"]/@content').extract()
        if not tmp:
            tmp = hxs.select('//section[div[@id="prod-product-code"]]//div[@id="prod-price"]/p//strong//text()').extract()
            if not tmp:
                tmp = hxs.select('//div[@id="prod-price"]//span[@itemprop="price"]/text()').extract()
                if not tmp:
                    tmp = hxs.select('//strong[@class="price"]/text()').extract()
        if tmp:
            price = extract_price(''.join(tmp).strip().replace(',',''))
        loader.add_value('price', price)

        try:
            loader.add_xpath('stock', '//div[@data-jl-stock]/@data-jl-stock')
        except ValueError:
            loader.add_value('stock', '0')

        #== Extracting Image URL ==#
        tmp = hxs.select('//li[contains(@class,"image")]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)


        #== Extracting Brand ==#
        tmp = hxs.select('//div[@itemprop="brand"]/span/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())


        #== Extracting Category ==#
        tmp = hxs.select('//div[@id="breadcrumbs"]/ol/li/a/text()').extract()
        if len(tmp)>1:
            loader.add_value('category', ' > '.join(tmp[-3:]))

        product = loader.load_item()

        #== Extracting Options ==#
        options = hxs.select('//div[@id="prod-multi-product-types"]//div[@itemprop="offers"]')
        if not options:
            if not product.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return

        #== Process options ==#
        for sel in options:
            item = copy.deepcopy(product)
            tmp  = sel.select('.//div[contains(@class,"mod-product-code")]/p/text()').extract()
            if tmp:
                item['identifier'] = tmp[0]
                item['sku'] = tmp[0]
            tmp = sel.select('.//h3/text()').extract()
            if tmp:
                item['name'] = name + ' - ' + tmp[0]

            price = 0
            tmp = sel.select('.//p[@class="price"]/strong/text()').re('[0-9,.]+')
            if not tmp:
                tmp = sel.select('.//strong[@class="price"]/text()').re('[0-9,.]+')
            if tmp:
                price = extract_price(tmp[0].strip().replace(',',''))
            item['price'] = price

            tmp = sel.select('.//link[@itemprop="availability"]/@content').extract()
            if tmp and 'in' in tmp[0].lower():
                item['stock'] = 1
            else:
                item['stock'] = 0

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
