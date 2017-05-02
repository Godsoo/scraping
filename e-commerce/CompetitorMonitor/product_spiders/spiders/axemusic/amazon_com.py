import os
import os.path
import json

from decimal import Decimal

from scrapy import log
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url

from urlparse import urljoin as urljoin_rfc

from product_spiders.spiders.BeautifulSoup import BeautifulSoup


from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders import BaseAmazonSpider
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

def append_request(url, callback, meta):
    meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))

def append_request_suggested(url, callback, meta):
    meta = dict(meta)
    meta['suggested_search_peek'] = False
    meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))


class AmazonSpider(BaseAmazonSpider):
    name = 'axemusic-amazon.com-music'
    allowed_domains = ['amazon.com']
    all_sellers = True
    _use_amazon_identifier = True
    collect_products_from_list = True
    collected_identifiers = set()

    start_urls = ['http://www.amazon.com/']
    
    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    handle_httpstatus_list = [400, 501]

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__('www.amazon.com', *args, **kwargs)
        self.try_suggested = False
        self.do_retry = True

    def start_requests(self):
        urls = [{'url':'http://www.amazon.com/s/ref=lp_11091801_nr_n_1?rh=n%3A11091801%2Cn%3A!11965861%2Cn%3A11971311&bbn=11965861&ie=UTF8&qid=1385563252&rnid=11965861', 'category':'Bass Guitars'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D11971241&field-keywords=', 'category':'Guitars'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D11970241&field-keywords=', 'category':'Drums & Percussion'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D11969981&field-keywords=', 'category':'Keyboards'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D11973881&field-keywords=', 'category':'DJ, Electronic Music & Karaoke'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D405757011&field-keywords=', 'category':'Live Sound & Stage'},
                {'url':'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D11973111&field-keywords=', 'category':'Recording Equipment'}]

        for url in urls:
            yield Request(url['url'], meta={
                'search_string': '',
                'search_item': {'sku': '', 'name': '', 'category': url['category'], 'price': ''},
                'collected_items': [],
                'requests': [],
                'current_page': 1,
                'requests_done': set(),
                }, dont_filter=True, callback=self.parse_product_by_price)

    def parse_product_by_price(self, response):
        if response.meta.get('crawl_list', False):
            yield Request(response.url, meta=response.meta, dont_filter=True, callback=self.parse_product_list)
        else:
            for i in xrange(801):
                max_price = '' if i == 800 else i + 1
                price_filter = '&low-price=%s&high-price=%s&x=0&y=0' % (i, max_price)
                url = response.url + price_filter
                response.meta['crawl_list'] = True
                yield Request(url, meta=response.meta, callback=self.parse_product_by_price)

    def match(self, search_item, new_item):
        return True

    def parse_product_list(self, response):

        if self.antibot_protection_raised(response.body):
            if self.do_retry:
                yield self.retry_download(failure=None,
                                          url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product_list)
            else:
                self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        hxs = HtmlXPathSelector(response)

        found_something = False
        matched_any = False
        suggested_product_list = response.meta.get('suggested_search_peek', False)

        preloaded_images = hxs.select('//div[@id="results-atf-images-preload"]/img/@src').extract()
        preloaded_images.reverse()

        for result in hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//li[starts-with(@id, "result_")]'):
            found_something = True

            try:
                product_name = result.select(u'.//h2//text()').extract()[0].strip()
                product_name = product_name[0:1020] + '...' if len(product_name) > 1024 else product_name
            except:
                continue

            # checks item condition, collect only new items
            amazon_prime = result.select('.//i[contains(@class, "a-icon-prime")]').extract()
            condition = ''.join(result.select('div/div[3]//text()').extract())
            if not condition:
                condition = ''.join(result.select('ul/li/a[span[contains(@class, "price")]]/text()').extract()).strip()
            if condition and 'new' not in condition.lower() and not amazon_prime:
                self.log('Reject used product %s' % product_name)
                continue

            try:
                identifier = result.select('@data-asin').extract()[0]
            except:
                if not result.select('./@id').extract()[0].endswith('_empty'):
                    raise
                continue

            price = result.select('.//span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = result.select('.//span[contains(@class, "price")]//text()').extract()
            if not price:
                self.log('No price on %s' % response.url)
                continue

            price = self.extract_price(price[0])
            product = Product(response.meta['search_item'])
            product['name'] = product_name
            brand = result.select('.//a/text()').re('Show only (.+) items')
            if brand:
                product['brand'] = brand[0]

            product['price'] = price

            if preloaded_images:
                pre_image_url = preloaded_images.pop()
            else:
                pre_image_url = ''

            if self._use_amazon_identifier:
                product['identifier'] = product.get('identifier', '') + ':' + identifier
            url = result.select(u'.//h2/../@href').extract()[0]
            product['url'] = urljoin_rfc(get_base_url(response), url)
            image_url = result.select(u'.//img[contains(@alt, "Product Details")]/@src').extract()
            if image_url:
                product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])
                if len(product['image_url']) > 1024 and ('data:image/jpg;base64' in product['image_url']):
                    product['image_url'] = pre_image_url


            if self.basic_match(response.meta['search_item'], product):

                if self.match(response.meta['search_item'], product):
                    matched_any = True
                    meta = dict(response.meta)
                    meta['_product'] = product
                    if self.collect_products_from_list and not self.only_buybox and product['price'] > 0:
                        if self.amazon_direct:
                            # Dealer to Amazon and collect best match
                            product['dealer'] = 'Amazon'
                            search_item_name = response.meta['search_item'].get('name', '')
                            search_string = ' '.join([response.meta['search_string'], search_item_name]).strip()
                            yield self._collect_best_match(response.meta['collected_items'],
                                                           product,
                                                           search_string)
                        else:
                            yield product

        # Follow suggested links only on original search page
        if not suggested_product_list and not found_something and self.try_suggested:
            urls = hxs.select(u'//div[contains(@class,"fkmrResults")]//h3[@class="fkmrHead"]//a/@href').extract()
            if urls:
                self.log('No results found for [%s], trying suggested searches' % (response.meta['search_string']))
            else:
                self.log('No results found for [%s], no suggested searches' % (response.meta['search_string']))

            for url in urls:
                url = urljoin_rfc(get_base_url(response), url)
                self._append_request_suggested(url, self.parse_product_list, response.meta)

        next_url = hxs.select(u'//a[@id="pagnNextLink"]/@href').extract()
        # Follow to next pages only for original search
        # and suggested search if at least one product matched from first page
        # otherwise it tries to crawl the whole Amazon or something like that
        if next_url and (not suggested_product_list or matched_any):
            page = response.meta.get('current_page', 1)
            if self.max_pages is None or page <= self.max_pages:
                response.meta['suggested_search_peek'] = False
                response.meta['current_page'] = page + 1
                url = urljoin_rfc(get_base_url(response), next_url[0])
                self._append_request(url, self.parse_product_list, response.meta)
            else:
                self.log('Max page limit %d reached' % self.max_pages)

        for x in self._continue_requests(response):
            yield x

    def _collect_lowest_price(self, collected_items, new_item):
        """ Keeps only product with the lowest price """
        if collected_items:
            i = collected_items[0]
            if Decimal(i['price']) > Decimal(new_item['price']) and i['identifier'] == new_item['identifier']:
                collected_items[0] = new_item
                self.collected_identifiers.add(new_item['identifier'])
            else:
                if new_item['identifier'] in self.collected_identifiers:
                    return
                collected_items.append(new_item)
                self.collected_identifiers.add(new_item['identifier'])
        else:
            collected_items.append(new_item)
            self.collected_identifiers.add(new_item['identifier'])

    def collect_price(self, hxs, response):
        soup = BeautifulSoup(response.body)
        try:
            soup_form = soup.find(id='handleBuy')
            price = soup_form.find('b', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'price')
            if not price:
                price = soup_form.find('span', 'pa_price')
            if price:
                price = self.extract_price(price.text)
            else:
                price = None
        except:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
            if not price:
                price = hxs.select('//span[@id="priceblock_saleprice"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="actualPriceValue"]/*[@class="priceLarge"]/text()').extract()

            if price:
                price = self.extract_price(price[0])
            else:
                price = None

        return price
