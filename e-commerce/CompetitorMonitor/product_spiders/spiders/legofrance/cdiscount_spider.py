import os
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.exceptions import CloseSpider

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log

# from phantomjs import PhantomJS

# from scrapy.xlib.pydispatch import dispatcher
# from scrapy import signals


class CDiscountSpider(BaseSpider):
    name = 'legofrance-cdiscount.com'
    allowed_domains = ['cdiscount.com']
    start_urls = (u'http://www.cdiscount.com/juniors/lego/v-12028-12028.html',)

    handle_httpstatus_list = [502]
    user_agent = 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0'

    download_delay = 0.1

    RETRY_TIMES = 200

    '''
    def __init__(self, *args, **kwargs):
        super(CDiscountSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self._browser.quit()
    
    '''

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="mvNavSub"]/ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(base_url, category)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//span[@class="ListImage100GlobalDiv"]//a[contains(@href, "juniors/lego")]/@href').extract()
        categories += hxs.select('//div[@class="act"]//following-sibling::ul/li/a[contains(text(), "LEGO")]/@href').extract()
        for category in categories:
            url = urljoin_rfc(base_url, category)
            yield Request(url, callback=self.parse_products)

        sitemap_nodeid = hxs.select('//input[@name="TechnicalForm.SiteMapNodeId"]/@value').extract()

        products = response.xpath('//div[@id="lpContent"]/ul/li[div/a]')
        if products:
            for product in products:
                link = product.select('div/a/@href').extract()
                if link:
                    meta = {}
                    sku = product.select('./@data-sku').extract()[0]
                    meta['url'] = urljoin_rfc(base_url, link[0])
                    meta['name'] = product.select('div//div[@class="prdtBTit"]/text()').extract()[0]
                    meta['category'] = product.select('//div[@id="bc"]//span[@itemprop="title"]/text()').extract()[0]
                    meta['image_url'] = product.css('img.prdtBImg::attr(data-src)').extract_first() or product.css('img.prdtBImg::attr(src)').extract_first()
                    identifier = product.select('./@data-sku').extract()
                    meta['identifier'] = identifier[0] if identifier else None
                    meta['sku'] = sku.replace('LEGO', '').replace('leg', '').strip()
                    meta['brand'] = 'LEGO'
                    meta['price'] = '.'.join(product.select(u'.//div[@class="lpPrice"]//text()').re(r'\d+')).strip()

                    sellers_url = product.select('.//div[@class="facilityP"]/div[@class="facMkt"]/a/@href').extract()
                    if sellers_url:
                        sellers_url = sellers_url[0]
                        if sellers_url.startswith('#/') or sellers_url.startswith('#'):
                            sellers_url = sellers_url[1:]
                        sellers_url = urljoin_rfc(base_url, sellers_url)
                        if sitemap_nodeid and identifier:
                            alternative_url = 'http://www.cdiscount.com/mp-%(sitemap_nodeid)s-%(product_id)s.html' % \
                                {'sitemap_nodeid': sitemap_nodeid[0], 'product_id': identifier[0]}
                            meta['alternative_url'] = alternative_url
                        yield Request(sellers_url, callback=self.parse_sellers, meta=meta)
                    elif sitemap_nodeid and identifier:
                        sellers_url = ('http://www.cdiscount.com/mp-%(sitemap_nodeid)s-%(product_id)s.html?Filter=New' % \
                            {'sitemap_nodeid': sitemap_nodeid[0], 'product_id': identifier[0]})
                        yield Request(sellers_url, callback=self.parse_sellers, meta=meta)
                    else:
                        yield Request(meta['url'], dont_filter=True, callback=self.parse_sellers, meta=meta)
        else:
            # this site is buggy (it returns no products when we traverse thru the pages at random rate)
            # so this is a kind of retry code
            if 'next_page_retry' in response.meta:
                self.log('ERROR - NO PRODUCTS FOUND, retrying...')
                count = response.meta['next_page_retry']
                if count < self.RETRY_TIMES:
                    self.log('ERROR - NO PRODUCTS FOUND, retry #{} url: {}'.format(count, response.url))
                    yield Request(response.url,
                                  callback=self.parse_full,
                                  meta={'next_page_retry': count + 1,
                                        'dont_redirect': True},
                                  dont_filter=True
                                  )
                else:
                    self.log('ERROR - NO PRODUCTS FOUND, retry limit reached, giving up, url: {}'.format(response.url))
        # pagination
        next_page = hxs.select('//form[@name="PaginationForm"]//a[contains(@class, "pgNext")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            '''
            self.log('>>> BROWSER: GET => %s' % next_page)
            self._browser.get(next_page)
            self.log('>>> BROWSER: OK')
            time.sleep(5)
            cat_response = response.replace(url=next_page,
                                            body=self._browser.page_source)
            for p in self.parse_products(cat_response):
                yield p
            '''
            yield Request(next_page, callback=self.parse_products)

    def parse_sellers(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()
        if not name:
            name = ' '.join(hxs.select('//div[@id="fpBlocProduct"]/h1/text()').extract())
        if not name:
            name = ' '.join(hxs.select('//h1[@class="MpProductTitle productTitleBig"]/text()').extract())

        sellers = hxs.select('//div[@id="OfferList"]/div')
        if not meta['identifier']:
            meta['identifier'] = hxs.select('//div[@class="WantButton"]/@data-productid').extract()[0].upper()
        if sellers:
            for seller in sellers:
                seller_name = seller.select('div//div[@class="ConsoBoxMpStd002"]/a/@title').extract()
                euros = seller.select('div//div[@class="priceContainer"]/div/text()').extract()
                euros = euros[0] if euros else ''
                cents = seller.select('div//div[@class="priceContainer"]/div/div/text()').re(u'(\d+)')
                cents = cents[0] if cents else ''
                seller_price = euros + '.' + cents
                shipping_cost = seller.select('div//div[@class="DeliveryMode"]/span[@class="ColPlContent"]/text()').extract()[0].replace(',', '.')

                if seller_name:
                    seller_name = seller_name[0]
                else:
                    seller_name = ''

                l = ProductLoader(item=Product(), response=response)
                l.add_value('name', meta['name'])
                l.add_value('identifier', meta['identifier'] + seller_name)
                l.add_value('sku', meta['sku'])
                l.add_value('url', meta['url'])
                l.add_value('image_url', meta['image_url'])
                l.add_value('brand', meta['brand'])
                l.add_value('category', meta['category'])
                l.add_value('price', seller_price)
                l.add_value('shipping_cost', shipping_cost)
                l.add_value('dealer', 'CD - ' + seller_name if seller_name else 'Cdiscount')
                yield l.load_item()
            # Next page?
            next_page = hxs.select(u'//ul[@class="PaginationButtons"]//a[contains(text(),"Suivant")]')
            if next_page:
                next_page_onclick_id = next_page.select('@id').extract()[-1] + '.OnClick'
                yield FormRequest.from_response(response, formname='PageForm', formdata={next_page_onclick_id: u'1'},
                    callback=self.parse_sellers, meta=meta, dont_filter=True)
        else:
            # The website has changed but in some offer pages keep the old structure.
            sellers = hxs.select('//div[@id="fpmContent"]/div[contains(@class, "fpTab")]')
            if not meta['identifier']:
                meta['identifier'] = hxs.select('//div[@class="WantButton"]/@data-productid').extract()[0].upper()
            if sellers:
                for seller in sellers:
                    seller_name = seller.select('div[@class="fpSlrName"]/a[@class="slrName"]/text()').extract()
                    seller_price = '.'.join(seller.select('.//p[@class="price"]//text()').re(r'(\d+)'))
                    shipping = seller.select('./div[@class="fpSlrCom"]/table/tbody/tr/td[2]/span[@class="price"]/text()').re(r'([\d.,]+)')
                    shipping_cost = shipping[0].replace('.', ',').replace(',', '.') if shipping else '0.00'

                    if seller_name:
                        seller_name = seller_name[0]
                    else:
                        seller_name = ''

                    l = ProductLoader(item=Product(), response=response)
                    l.add_value('name', meta['name'])
                    l.add_value('identifier', meta['identifier'] + seller_name)
                    l.add_value('sku', meta['sku'])
                    l.add_value('url', meta['url'])
                    l.add_value('image_url', meta['image_url'])
                    l.add_value('brand', meta['brand'])
                    l.add_value('category', meta['category'])
                    l.add_value('price', seller_price)
                    l.add_value('shipping_cost', shipping_cost)
                    l.add_value('dealer', 'CD - ' + seller_name if seller_name else 'Cdiscount')
                    yield l.load_item()

                # Next page
                params = {
                    'FiltersAndSorts.ChkFilterToNew': 'true',
                    'FiltersAndSorts.ChkSortByPriceAndShipping': 'true',
                }
                pagination_params = dict(
                    zip(hxs.select('//input[contains(@name, "Pagination.")]/@name').extract(),
                        hxs.select('//input[contains(@name, "Pagination.")]/@value').extract()))
                if pagination_params.get('Pagination.CurrentPage', 1) != pagination_params.get('Pagination.TotalPageCount', 1):
                        next_page = int(pagination_params.get('Pagination.CurrentPage', 1)) + 1
                        pagination_params['Pagination.CurrentPage'] = str(next_page)
                        params.update(pagination_params)
                        yield FormRequest(response.url,
                                          callback=self.parse_sellers,
                                          formdata=params,
                                          dont_filter=True,
                                          meta=response.meta)
            elif response.meta.get('alternative_url'):
                # This site have bugs and sometimes does not list the offers.
                meta = response.meta.copy()
                meta['alternative_url'] = None
                yield Request(response.meta['alternative_url'],
                              callback=self.parse_sellers,
                              meta=meta)
            else:
                seller = hxs.select('//a[@href="#seller"]/text()').extract()
                seller_name = 'Cdiscount' if not seller else 'CD' + ' - ' + seller[0].strip()
                l = ProductLoader(item=Product(), response=response)
                l.add_value('name', meta['name'])
                l.add_value('identifier', meta['identifier'] + (seller[0] if seller else 'Cdiscount'))
                l.add_value('sku', meta['sku'])
                l.add_value('url', meta['url'])
                l.add_value('image_url', meta['image_url'])
                l.add_value('brand', meta['brand'])
                l.add_value('category', meta['category'])
                l.add_value('price', meta['price'])
                l.add_value('shipping_cost', 0)
                l.add_value('dealer', seller_name)
                yield l.load_item()
