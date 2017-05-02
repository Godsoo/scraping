import os
import xlrd

from scrapy.http import Request

from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator


class RoysAmazonBuyboxSpider(BaseAmazonSpider):
    name = 'roys-amazon.co.uk-buybox'
    domain = 'www.amazon.co.uk'
    max_pages = 1
    do_retry = True
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False
    only_buybox = True
    try_suggested = False
    collect_products_with_no_dealer = False

    second_code_list = {}

    def __init__(self, *args, **kwargs):
        super(RoysAmazonBuyboxSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False
        self.current_searches = []

    def get_search_query_generator(self):

        filename = os.path.join(HERE, 'RoysData.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row_values(rownum)
            self.second_code_list[row[12]] = row

            yield (row[12],
                  {'sku': row[6],
                   'name': '',
                   'category': [row[1], row[3], row[5]],
                   'price': extract_price(row[11]),
                  })

    def match(self, meta, search_item, found_item):
        return True

    def _collect_buybox(self, product, meta):
        self._collect_all(product)

    def parse_product_list(self, response):
        """
        This function is callback for Scrapy. It processes search results page

        TODO: incorporate cache
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product_list)
                return
            else:
                self.antibot_blocked_fully_urls.add(response.url)
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)
                return

        self.parsed_count['parse_product_list'] += 1

        follow_suggestions = response.meta.get("follow_suggestions", True)
        is_main_search = response.meta.get("is_main_search", True)

        data = self.scraper.scrape_search_results_page(response, amazon_direct=self.amazon_direct)

        # This sometimes does not work because Amazon does not show total number of products properly on the first page
        # Then when the request is split, if the total number of requests is 1 then it is just going to ignore it
        max_pages = data['max_pages'] if data.get('max_pages') else self._max_pages

        # calculate page number
        page = data.get('current_page', None)
        if not page:
            page = response.meta.get('current_page', None)
        page = int(page) if page is not None else 1

        if page == 1 and not self.check_number_of_results_fits(data, max_pages, response=response):
            requests = self.get_subrequests_for_search_results(response, data, max_pages)
            # If not splitted then it is ignored
            if len(requests) > 1:
                self.log("[AMAZON] WARNING: Number of results is too big (%d). Splitting to %d requests. URL: %s" %
                         (data['results_count'], len(requests), response.url))
                for req in requests:
                    yield req
                return

        if data['products']:
            items = data['products']
            found_for = None
            if self.type == 'search':
                found_for = self.current_search
            elif self.type == 'category':
                found_for = self.current_category
            self.log('[AMAZON] Found products for [%s]' % found_for)

        elif data['suggested_products'] and self.try_suggested:
            items = data['suggested_products']
            self.log('[AMAZON] No products found for [%s]. Using suggested products. URL: %s' %
                     (self.current_search, response.url))
        else:
            items = []

        if not items and not response.meta.get('second_code_search', False):
            row = self.second_code_list[self.current_search.replace('"', '')]
            if row[0] >=103 and row[14]:
                search_string = row[14]
                url = AmazonUrlCreator.build_search_url(self.domain, search_string, self.amazon_direct)

                s_item = {'sku': row[6],
                          'name': '',
                          'category': [row[1], row[3], row[5]],
                          'price': extract_price(row[11]),
                         }

                yield Request(url, meta={'search_string': row[14], 'search_item': s_item, 'second_code_search':True},
                            dont_filter=True, callback=self.parse_product_list)


        if not data['products'] and follow_suggestions and self.try_suggested:
            self.log('[AMAZON] No products or suggested products found for [%s], trying suggested searches' %
                     self.current_search)
            for url in data['suggested_search_urls']:
                # yield request
                # should mark that it's referred as suggested search and as so do not check other suggestions
                new_meta = response.meta.copy()
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': self.current_search_item,
                    'follow_suggestions': False,
                    'is_main_search': False,
                })
                yield Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )

        matched_any = False

        if self.collect_products_from_list:
            # Amazon Direct
            if self.amazon_direct and not self.only_buybox and not self.all_sellers and not self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_amazon_direct(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
            # Buy-Box
            elif self.only_buybox and not self.amazon_direct and not self.all_sellers and not self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_buybox(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
            # All sellers / lowest price dealer
            elif self.all_sellers or self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_all_sellers(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
        else:
            for item in items:
                new_meta = response.meta.copy()
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                new_meta.update({
                    'check_match': True,
                })
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta
                )

        next_url = data['next_url']

        follow_next = False
        if self.type == 'category':
            follow_next = True
        elif self.type == 'search':
            # Follow to next pages only for original search
            # and suggested search if at least one product matched from first page
            # otherwise it tries to crawl the whole Amazon or something like that
            follow_next = (is_main_search or matched_any)
        if next_url and follow_next:
            if self.max_pages is None or page <= self.max_pages:
                new_meta = response.meta.copy()
                new_meta.update({
                    'follow_suggestions': False,
                    'is_main_search': is_main_search,
                    'current_page': page + 1
                })
                yield Request(
                    next_url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )
            else:
                self.log('[AMAZON] Max page limit %d reached. URL: %s' % (self.max_pages, response.url))
        elif next_url:
            self.log('[AMAZON] Not following next page from %s: %s' % (response.url, next_url))
        else:
            self.log('[AMAZON] No next url from %s' % response.url)
