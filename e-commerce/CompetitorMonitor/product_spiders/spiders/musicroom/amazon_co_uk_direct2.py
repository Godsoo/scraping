import os
from scrapy.http import Request

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator


class MusicroomAmazonDirectSpiderTest(BaseAmazonSpider):
    name = 'musicroom-amazon.co.uk-direct[test]'
    domain = 'www.amazon.co.uk'

    max_pages = 1
    do_retry = True
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False
    amazon_direct = True
    try_suggested = False

    def __init__(self, *args, **kwargs):
        super(MusicroomAmazonDirectSpiderTest, self).__init__(*args, **kwargs)
        self.try_suggested = False
        self.current_searches = []

    def get_search_query_generator(self):
        """
        This spider differs a little from what base spider provides. For each item in list it needs firstly to search
        by ISBN, EAN, UPC and by name consequently, and only search using next method if previous failed. So if
        product is found by ISBN than just skip other search methods.

        To make it work this function outputs all possible searches. It also outputs `match_method` for each
        search strings. Match method can be of two values 'all' and 'best_match'. All means to just collect all
        found products, 'best_match' makes it collect only best matched by name product
        """
        fields = ['UniqueProductCode', 'isbn', 'ean', 'upc', 'ProductName', 'PriceGBP', 'ProductPageURL', 'Brand',
                  'Category', 'ImageURL', 'Stock', 'ShippingCost']
        filename = 'IntelligentEye.txt'
        with open(HERE + '/' + filename) as f:
            content = f.readlines()
            for i, line in enumerate(content):
                line = line.decode('cp865', 'ignore')
                values = line.split('\t')
                data = dict(zip(fields, values))
                search_strings = []

                ss = data['isbn'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['ean'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['upc'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['ProductName'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "string"))

                if search_strings:
                    item = {
                        'sku': data['UniqueProductCode'],
                        'name': data['ProductName'],
                        'category': data['Category'],
                        'price': data['PriceGBP'],
                    }
                    yield (search_strings, item)

    def get_next_search_request(self, callback=None):
        """
        This differs from how it works in base spider due to spider requirements. Check `get_search_query_generator`
        documentation for brief introduction

        To make it work how intended this spider uses additional attribute - `current_searches`. It stores all
        possible searches. The function takes search string (and relevant match_method) one by one and launches
        search on them. If `current_searches` is empty it takes next search item from generator
        """
        if not self.current_searches or self.processed_items:
            if not self.search_generator:
                return None
            try:
                search_strings, search_item = next(self.search_generator)
            except StopIteration:
                return None

            self.current_search_item = search_item
            self.collected_items = []
            self.processed_items = False
            self.current_searches = search_strings

        search_string, match_method = self.current_searches.pop(0)

        self.log('Searching for [%s]' % search_string)

        self.current_search = search_string

        requests = []
        url = AmazonUrlCreator.build_search_url(self.domain, search_string, self.amazon_direct)

        if callback is None:
            callback = self.parse_product_list

        requests.append(Request(
            url,
            meta={'search_string': search_string, 'match_method': match_method, 'search_item': self.current_search_item},
            dont_filter=True, callback=callback
        ))

        return requests

    def match(self, meta, search_item, new_item):
        if meta.get('match_method', '') == "code":
            return True
        else:
            # match last search item against the name (as last search variation is by Name)
            return self.match_name(meta['search_item'], new_item, match_threshold=70)

    def _collect_amazon_direct(self, product, meta):
        """
        The function incorporates use of `match_method` parameter. It also empties `current_searches` attribute
        after collecting so the spider moves on to next item (skipping searching current item with other
        search strings)
        """
        if meta.get('match_method', '') == "string":
            product['sku'] = None
            self._collect_all(product)
        else:
            search_item_name = self.current_search_item.get('name', '')
            search_string = ' '.join([meta['search_string'], search_item_name]).strip()
            self._collect_best_match(product, search_string)
        self.current_searches = []

    # def search(self, search_strings, search_item):
    #     if isinstance(search_strings, basestring):
    #         raise CloseSpider('Search string found, expecting a list of search strings!')
    #     url = 'http://%s/s/ref=nb_sb_noss?url=search-alias%%3Daps&field-keywords=%s'
    #     if self.amazon_direct:
    #         if '.com' in self.domain:
    #             url += '&emi=ATVPDKIKX0DER'
    #         elif '.co.uk' in self.domain:
    #             url += '&emi=A3P5ROKL5A1OLE'
    #         elif '.fr' in self.domain:
    #             url += '&emi=A1X6FK5RDHNB96'
    #         elif '.it' in self.domain:
    #             url += '&emi=A11IL2PNWYJU7H'
    #         else:
    #             raise CloseSpider('Domain %s not found!!' % self.domain)
    #     search_string = search_strings.pop(0)
    #     self.log('Searching for [%s]' % search_string)
    #     return Request(url % (self.domain, urllib.quote_plus(search_string)),
    #                    meta={'search_string': search_string,
    #                          'search_strings': search_strings,
    #                          'search_item': search_item,
    #                          'collected_items': [],
    #                          'requests': [],
    #                          'current_page': 1,
    #                          'requests_done': set(),
    #                          }, dont_filter=True, callback=self.parse_product_list)
    #
    # def _continue_requests(self, response):
    #     while response.meta['requests']:
    #         req = response.meta['requests'].pop(0)
    #         if req.url not in response.meta['requests_done']:
    #             response.meta['requests_done'].add(req.url)
    #             if '_product' in req.meta:
    #                 if not self._may_collect(response.meta['collected_items'], req.meta['_product']):
    #                     self.log('Skip product unlikely to be collected %s' % (req.meta['_product']))
    #                     continue
    #             yield req
    #             return
    #
    #     if not response.meta['collected_items'] and self.items_not_found_callback:
    #         yield self.items_not_found_callback(response.meta['search_strings'], response.meta['search_item'])
    #
    #     for item in response.meta['collected_items']:
    #         item['name'] = item['name'][:1024]
    #         yield item
    #
    # def search_next(self, search_strings, search_item):
    #     if len(search_strings):
    #         return self.search(search_strings, search_item)
    #     else:
    #         self.log("No search results for this item were found: {}".format(search_item))
    #         return []
    #
    # def parse_product(self, response):
    #     """ "Parse" product just to get seller name """
    #
    #     if self.antibot_protection_raised(response.body):
    #         if self.do_retry:
    #             yield self.retry_download(failure=None,
    #                                       url=response.url,
    #                                       metadata=response.meta,
    #                                       callback=self.parse_product)
    #         else:
    #             self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
    #                 response.url))
    #
    #     hxs = HtmlXPathSelector(response)
    #
    #     product = response.meta['_product']
    #
    #     vendor = hxs.select(u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()').extract()
    #     if not vendor:
    #         vendor = hxs.select('//div[@id="soldByThirdParty"]/b/text()').extract()
    #     else:
    #         # check if it is taken from used products buy box, ignore it if so
    #         used_vendor = hxs.select(u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()/../../../@id').extract()
    #         if used_vendor:
    #             vendor = None
    #     if not vendor:
    #         amazon_price = hxs.select('//span[@id="actualPriceValue"]/b/text()').extract()
    #         if not amazon_price:
    #             amazon_price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
    #         # Checks if it is an amazon product
    #         if amazon_price:
    #             vendor = 'Amazon'
    #         else:
    #             offer_listing = hxs.select('//div[@id="olpDivId"]/span[@class="olpCondLink"]/a/@href').extract()
    #             if not offer_listing or self.collect_products_from_list:
    #                 if not self.only_buybox:
    #                     self.errors.append('WARNING: No seller name => %s' % response.url)
    #                 vendor = None
    #             else:
    #                 offer_listing_url = urljoin_rfc(get_base_url(response), offer_listing[0])
    #                 params = parse_qs(urlparse(offer_listing_url).query)
    #                 condition = params.get('condition', ['any'])[0].strip()
    #                 if self.collect_new_products and condition == 'new' or \
    #                    self.collect_used_products and condition == 'used':
    #                     self._append_request(offer_listing_url, self.parse_mbc_list, response.meta)
    #     else:
    #         vendor = 'AM - ' + vendor[0]
    #
    #     if vendor:
    #         product['dealer'] = vendor
    #
    #         if self._seller_ok(vendor):
    #             if self.match(response.meta, product):
    #                 if len(response.meta['search_strings']) < 1:
    #                     product['sku'] = None
    #                     self._collect_all(response.meta['collected_items'], product)
    #                 else:
    #                     self._collect(response.meta['collected_items'], product)
    #
    #     for x in self._continue_requests(response):
    #         yield x
    #
    # def parse_product_list(self, response):
    #
    #     if self.antibot_protection_raised(response.body):
    #         if self.do_retry:
    #             yield self.retry_download(failure=None,
    #                                       url=response.url,
    #                                       metadata=response.meta,
    #                                       callback=self.parse_product_list)
    #         else:
    #             self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
    #                 response.url))
    #
    #     hxs = HtmlXPathSelector(response)
    #
    #     found_something = False
    #     matched_any = False
    #     suggested_product_list = response.meta.get('suggested_search_peek', False)
    #
    #     for result in hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//div[starts-with(@id, "result_")]'):
    #         found_something = True
    #
    #         try:
    #             product_name = result.select(u'.//h3/a/span/text()').extract()[0].strip()
    #             product_name = product_name[0:1020] + '...' if len(product_name) > 1024 else product_name
    #         except:
    #             continue
    #
    #         try:
    #             identifier = result.select('./@name').extract()[0]
    #         except:
    #             if not result.select('./@id').extract()[0].endswith('_empty'):
    #                 raise
    #             continue
    #
    #         price = result.select('.//span[@class="bld lrg red"]//text()').extract()
    #         if not price:
    #             price = result.select('.//span[contains(@class, "price")]//text()').extract()
    #         if not price:
    #             self.log('No price on %s' % response.url)
    #             continue
    #
    #         price = self.extract_price(price[0])
    #         product = Product(response.meta['search_item'])
    #         product['name'] = product_name
    #         brand = result.select(u'.//h3/span[contains(text(),"by")]/text()').extract()
    #         if brand:
    #             product['brand'] = brand[0].replace('by ', '').replace('de ', '').replace('(', '').strip()
    #         product['price'] = price
    #
    #         if self._use_amazon_identifier:
    #             product['identifier'] = product.get('identifier', '') + ':' + identifier
    #         url = result.select(u'.//h3/a/@href').extract()[0]
    #         product['url'] = urljoin_rfc(get_base_url(response), url)
    #         image_url = result.select(u'.//img[contains(@class, "productImage")]/@src').extract()
    #         if image_url:
    #             product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])
    #
    #         if self.basic_match(response.meta, product):
    #             if not self.collect_products_from_list:
    #                 more_buying_choices = \
    #                     result.select('.//li[@class="sect mbc"]/../li[contains(@class,"mkp2")]/a/@href').extract()
    #                 if not more_buying_choices:
    #                     more_buying_choices = result.select('.//li[contains(@class,"mkp2")]/a/@href').extract()
    #                 if more_buying_choices:
    #                     url = urljoin_rfc(get_base_url(response), more_buying_choices[0])
    #                     params = parse_qs(urlparse(url).query)
    #                     condition = params.get('condition', ['any'])[0].strip()
    #                     if not self.collect_new_products and condition == 'new':
    #                         continue
    #                     if not self.collect_used_products and condition == 'used':
    #                         continue
    #                     self._append_request(url, self.parse_mbc_list, response.meta)
    #                     continue
    #
    #             if self.match(response.meta, product):
    #                 matched_any = True
    #                 meta = dict(response.meta)
    #                 meta['_product'] = product
    #                 if self.collect_products_from_list and not self.only_buybox:
    #                     if self.amazon_direct:
    #                         # Dealer to Amazon and collect best match
    #                         product['dealer'] = 'Amazon'
    #                         search_item_name = response.meta['search_item'].get('name', '')
    #                         search_string = ' '.join([response.meta['search_string'], search_item_name]).strip()
    #                         if len(response.meta['search_strings']) < 1:
    #                             product['sku'] = None
    #                             yield self._collect_all(response.meta['collected_items'],
    #                                                     product)
    #                         else:
    #                             yield self._collect_best_match(response.meta['collected_items'],
    #                                                            product,
    #                                                            search_string)
    #                     else:
    #                         yield product
    #                 else:
    #                 # Go and extract vendor
    #                     self._append_request(product['url'], self.parse_product, meta)
    #
    #     # Follow suggested links only on original search page
    #     if not suggested_product_list and not found_something and self.try_suggested:
    #         urls = hxs.select(u'//div[contains(@class,"fkmrResults")]//h3[@class="fkmrHead"]//a/@href').extract()
    #         if urls:
    #             self.log('No results found for [%s], trying suggested searches' % (response.meta['search_string']))
    #         else:
    #             self.log('No results found for [%s], no suggested searches' % (response.meta['search_string']))
    #
    #         for url in urls:
    #             url = urljoin_rfc(get_base_url(response), url)
    #             self._append_request_suggested(url, self.parse_product_list, response.meta)
    #
    #     next_url = hxs.select(u'//a[@id="pagnNextLink"]/@href').extract()
    #     # Follow to next pages only for original search
    #     # and suggested search if at least one product matched from first page
    #     # otherwise it tries to crawl the whole Amazon or something like that
    #     if next_url and (not suggested_product_list or matched_any):
    #         page = response.meta.get('current_page', 1)
    #         if self.max_pages is None or page <= self.max_pages:
    #             response.meta['suggested_search_peek'] = False
    #             response.meta['current_page'] = page + 1
    #             url = urljoin_rfc(get_base_url(response), next_url[0])
    #             self._append_request(url, self.parse_product_list, response.meta)
    #         else:
    #             self.log('Max page limit %d reached' % self.max_pages)
    #
    #     for x in self._continue_requests(response):
    #         yield x
    #
    # def parse_mbc_list(self, response):
    #     """ Parses list of more buying choices
    #         All products have the same id, so create a unique id from product id + seller id
    #     """
    #
    #     if self.antibot_protection_raised(response.body):
    #         if self.do_retry:
    #             yield self.retry_download(failure=None,
    #                                       url=response.url,
    #                                       metadata=response.meta,
    #                                       callback=self.parse_mbc_list)
    #         else:
    #             self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
    #                 response.url))
    #
    #
    #     hxs = HtmlXPathSelector(response)
    #
    #     try:
    #         url = hxs.select('//a[@id="olpDetailPageLink"]/@href').extract()[0]
    #         url = urljoin_rfc(get_base_url(response), url)
    #         url_parts = url.split('/')
    #         product_id = url_parts[url_parts.index('product') + 1]
    #     except:
    #         if self.do_retry:
    #             yield self.retry_download(failure=None,
    #                                       url=response.url,
    #                                       metadata=response.meta,
    #                                       callback=self.parse_mbc_list)
    #
    #     for result in hxs.select('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]'):
    #         seller_id = None
    #         seller_urls = result.select(u'.//*[contains(@class, "olpSellerName")]//a/@href').extract()
    #         if seller_urls:
    #             seller_url_ = seller_urls[0]
    #             if 'seller=' in seller_url_:
    #                 seller_id = url_query_parameter(seller_url_, 'seller')
    #             else:
    #                 seller_parts = seller_url_.split('/')
    #                 try:
    #                     seller_id = seller_parts[seller_parts.index('shops') + 1]
    #                 except:
    #                     # External website (link "Shop this website"?)
    #                     seller_id = url_query_parameter(seller_url_, 'merchantID')
    #             # else:
    #         #    seller_urls = result.select(u'.//ul[@class="sellerInformation"]//a/@href').extract()
    #         #    for s in seller_urls:
    #         #        if 'seller=' in s:
    #         #            seller_id = s.split('seller=')[1].split('&')[0]
    #         #            break
    #
    #         price = self.extract_price(
    #             result.select('.//span[contains(@class, "olpOfferPrice")]/text()').extract()[0].strip())
    #         product = Product(response.meta['search_item'])
    #         product['name'] = ' '.join(hxs.select(u'//div[@id="olpProductDetails"]/h1//text()').extract()).strip()
    #         brand = hxs.select(u'//div[@id="olpProductByline"]/text()').extract()
    #         if brand:
    #             product['brand'] = brand[0].replace('by ', '').replace('de ', '').strip()
    #         product['price'] = price
    #
    #         if seller_id:
    #             if self._use_amazon_identifier:
    #                 product['identifier'] = product.get('identifier', '') + ':' + product_id + ':' + seller_id
    #             product['url'] = 'http://%s/gp/product/%s/?smid=%s' % (self.domain, product_id, seller_id)
    #             self.log('SELLER FOUND => %s - %s' % (product['identifier'], product['url']))
    #         else:
    #             if self._use_amazon_identifier:
    #                 product['identifier'] = product.get('identifier', '') + ':' + product_id
    #             product['url'] = 'http://%s/gp/product/%s/' % (self.domain, product_id)
    #
    #         shipping = result.select('.//span[@class="olpShippingPrice"]/text()').extract()
    #         if shipping:
    #             product['shipping_cost'] = self.extract_price(shipping[0])
    #
    #         image_url = hxs.select(u'//div[@id="olpProductImage"]//img/@src').extract()
    #         if image_url:
    #             product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])
    #
    #         vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@title').extract()
    #         if not vendor:
    #             vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//a/b/text()').extract()
    #         if not vendor:
    #             vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//span/a/text()').extract()
    #         if vendor:
    #             vendor = vendor[0]
    #             if vendor.lower().startswith('amazon.'):
    #                 vendor = 'Amazon'
    #             else:
    #                 vendor = 'AM - ' + vendor
    #             product['dealer'] = vendor
    #             if self._seller_ok(vendor):
    #                 self.log('SELLER OK => %s' % vendor)
    #                 if self.match(response.meta, product):
    #                     self.log('>>> COLLECTED ITEM => %s' % product['name'])
    #                     if len(response.meta['search_strings']) < 1:
    #                         product['sku'] = None
    #                         self._collect_all(response.meta['collected_items'], product)
    #                     else:
    #                         self._collect(response.meta['collected_items'], product)
    #                 else:
    #                     self.log('NO MATCH!!')
    #         else:
    #             meta = dict(response.meta)
    #             meta['_product'] = product
    #             # Go and extract vendor
    #             self._append_request(product['url'], self.parse_product, meta)
    #
    #     next_url = hxs.select('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract()
    #     # Collecting all items
    #     if self.all_sellers and next_url:
    #         url = urljoin_rfc(get_base_url(response), next_url[0])
    #         self._append_request(url, self.parse_mbc_list, response.meta)
    #
    #     for x in self._continue_requests(response):
    #         yield x
