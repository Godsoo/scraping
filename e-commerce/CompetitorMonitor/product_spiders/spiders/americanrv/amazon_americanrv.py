import os
import re
import urllib2

import logging

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders import SearchSpiderBase

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(SearchSpiderBase):
    name = 'amazon_americanrv.com'
    allowed_domains = ['amazon.com']

    skip_first_row = True

    debug = False
    limit = 0

    def _get_csv_filename(self):
        return os.path.join(HERE, 'americanrv_products.csv')

    def _create_search_urls(self, row):
        product_ids = set()
        product_ids.add(row['id'])
        for prod_id in product_ids:
            query = urllib2.quote(prod_id)
            url = 'http://www.amazon.com/s/ref=nb_sb_noss?' + \
                  'url=search-alias%%3Daps&field-keywords=%s&x=0&y=0' % query
            yield url

    def _create_meta(self, row):
        sku = row['id']
        name = row['name']
        mfrgid = row['mfgid']
        ids = row['part #']
        meta = {'sku': sku, 'mfrgid': mfrgid, 'name': name, 'ids': ids}
        return meta

    # def start_requests(self):
    #     with open(os.path.join(HERE, 'americanrv_products.csv')) as f:
    #         reader = csv.reader(f)
    #         reader.next()
    #         for row in reader:
    #             product_ids = set()
    #             product_ids.add(row[0])
    #             sku = row[0]
    #             mfrgid = row[2]
    #             name = row[1]
    #             ids = row[3]
    #             for prod_id in product_ids:
    #                 query = prod_id.replace(' ', '+')
    #                 url = 'http://www.amazon.com/s/ref=nb_sb_noss?' + \
    #                       'url=search-alias%%3Daps&field-keywords=%s&x=0&y=0'
    #
    #                 yield Request(url % query, meta={'sku': sku, 'mfrgid': mfrgid, 'name': name, 'ids': ids})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@id="atfResults"]//div[starts-with(@id, "result_")]')
        pr = None
        search_results = []
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', './/h3/a/span/text()')
            if not loader.get_output_value('name'):
                loader.add_xpath('name', './/h3/a/text()')
            loader.add_xpath('url', './/h3/a/@href')
            loader.add_xpath('price', './/ul/li/a/span/text()', re='\$(.*)')
            if not loader.get_output_value('price'):
                loader.add_xpath('price', './/div[@class="newPrice"]//span[contains(@class,"price")]/text()')
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('identifier', response.meta['sku'].lower())
            if loader.get_output_value('price') and \
                    (pr is None or pr.get_output_value('price') > loader.get_output_value('price')):
                pr = loader
                search_results.append(pr)

        if search_results:
            cur_prod = search_results[0]
            next_prods = search_results[1:]
            yield Request(cur_prod.get_output_value('url'), callback=self.parse_mfrgids,
                          meta={'mfrgid': response.meta['mfrgid'], 'name': response.meta['name'], 'ids': response.meta['ids'], 'cur_prod': cur_prod, 'next_prods': next_prods}, dont_filter=True)

    def parse_mfrgids(self, response):
        hxs = HtmlXPathSelector(response)

        cur_prod = response.meta['cur_prod']

        ids = response.meta['ids'].split(' ')

        mfrgid = response.meta['mfrgid']
        mfrgid = re.sub('[-\. ]', '', mfrgid)

        keywords = response.meta['name'].split(' ')
        keywords = map(lambda x: re.sub('[-\. ]', '', x), keywords)
        keywords.append(mfrgid)

        site_mfrgids = []

        results = [
            hxs.select('//div[@class="tsRow" and child::span[contains(text(),"Manufacturer")]]/span[not(@class)]/text()').extract(),
            hxs.select('//td[@class="techSpecTD2" and preceding-sibling::td[contains(text(),"Manufacturer")]]/text()').extract(),
            hxs.select('//td[@class="bucket"]//li[b[contains(text(), "ASIN")]]/text()').extract(),
            hxs.select('//td[@class="bucket"]//li[b[contains(text(), "Item model number")]]/text()').extract(),
            hxs.select('//div[@class="productDescriptionWrapper"]/text()').re("Part Number\(s\):\s+(.*)"),
            hxs.select('//div[@class="tsRow" and child::span[contains(text(),"Manufacturer")]]/span[not(@class)]/text()').extract(),

            hxs.select('//tr[@class="item-model-number"]/td[@class="value"]/text()').extract(),
            hxs.select('//tr[td[@class="label"][contains(text(),"Manufacturer")]]/td[@class="value"]/text()').extract(),
            hxs.select('//tr[td[@class="label"][contains(text(),"ASIN")]]/td[@class="value"]/text()').extract(),
        ]
        for res in results:
            if res:
                site_mfrgids.append(_reformat_mfrgid(res[0]))
        #
        # site_mfrgid = hxs.select('//div[@class="tsRow" and child::span[contains(text(),"Manufacturer")]]/span[not(@class)]/text()').extract()
        # if not site_mfrgid:
        #     site_mfrgid = hxs.select('//td[@class="techSpecTD2" and preceding-sibling::td[contains(text(),"Manufacturer")]]/text()').extract()
        # if not site_mfrgid:
        #     site_mfrgid = hxs.select('//td[@class="bucket"]//li[b[contains(text(), "ASIN")]]/text()').extract()
        # if site_mfrgid:
        #     site_mfrgid = site_mfrgid[0]
        # else:
        #     site_mfrgid = None

        # site_part_number = hxs.select('//td[@class="bucket"]//li[b[contains(text(), "Item model number")]]/text()').extract()
        # if not site_part_number:
        #     site_part_number = hxs.select('//div[@class="productDescriptionWrapper"]/text()').re("Part Number\(s\):\s+(.*)")
        # if not site_part_number:
        #     site_part_number = hxs.select('//div[@class="tsRow" and child::span[contains(text(),"Manufacturer")]]/span[not(@class)]/text()').extract()
        # if not site_part_number:
        #     site_part_number = None
        # else:
        #     site_part_number = site_part_number[0]

        logging.error("Parsing SKU: %s" % cur_prod.get_output_value('sku'))
        if len(cur_prod.get_output_value('sku').split(" ")) > 2:
            brand = " ".join(cur_prod.get_output_value('sku').split(" ")[0:-1])
            part_number = cur_prod.get_output_value('sku').split(" ")[-1]
        elif len(cur_prod.get_output_value('sku').split(" ")) < 2:
            logging.error("Can't parse SKU: %s" % cur_prod.get_output_value('sku'))
            return
        else:
            brand, part_number = cur_prod.get_output_value('sku').split(" ")

        site_brand = hxs.select('//div[@class="tsRow" and child::span[contains(text(),"Brand")]]/span[not(@class)]/text()').extract()
        if not site_brand:
            site_brand = hxs.select('//tr[td[@class="label"][contains(text(),"Brand")]]/td[@class="value"]/text()').extract()
        if not site_brand:
            site_brand = None
        else:
            site_brand = site_brand[0]

        brand = brand.lower()
        site_brand = site_brand.lower() if site_brand else None

        # site_mfrgid = _reformat_mfrgid(site_mfrgid) if site_mfrgid else None
        part_number = _reformat_mfrgid(part_number)
        # site_part_number = _reformat_mfrgid(site_part_number) if site_part_number else None

        logging.error("Got brand: %s, part number: %s" % (brand, part_number))
        logging.error("Found on page brand: %s" % site_brand)
        logging.error("Found on page part numbers: %s" % str(site_mfrgids))

        if not site_brand and not site_mfrgids:
            logging.error("WTF?!")

        # site_mfrgid = site_mfrgid if site_mfrgid else site_part_number
        # site_part_number = site_part_number if site_part_number else site_mfrgid

        # matching part number
        matched = False
        # match with ids
        for prod_id in ids:
            ref_prod_id = _reformat_mfrgid(prod_id)
            for site_mfrgid in site_mfrgids:
                if site_mfrgid == ref_prod_id:
                    matched = True
            # if site_mfrgid == _reformat_mfrgid(prod_id):
            #     matched = True
            #     break
            # if site_part_number == _reformat_mfrgid(prod_id):
            #     matched = True
            #     break
        # match with part number from sku
        for site_mfrgid in site_mfrgids:
            if site_mfrgid == part_number or part_number in site_mfrgid:
                matched = True
        # match with mfrgid
        for site_mfrgid in site_mfrgids:
            if site_mfrgid == response.meta['mfrgid']:
                matched = True

        # if part_number == site_part_number or part_number in site_part_number:
        #     matched = True
        # if site_part_number == _reformat_mfrgid(response.meta['mfrgid']):
        #     matched = True
        # if site_mfrgid == _reformat_mfrgid(response.meta['mfrgid']):
        #     matched = True

        brand_matches = False
        if site_brand is not None and (brand in site_brand or site_brand in brand):
            brand_matches = True
        elif site_brand != brand:
            if brand in cur_prod.get_output_value('name').lower():
                brand_matches = True

        if matched and (brand_matches or site_brand is None):
            yield cur_prod.load_item()
        else:
            if response.meta['next_prods']:
                cur_prod = response.meta['next_prods'][0]
                yield Request(
                    cur_prod.get_output_value('url'),
                    callback=self.parse_mfrgids,
                    meta={
                        'mfrgid': response.meta['mfrgid'],
                        'name': response.meta['name'],
                        'ids': response.meta['ids'],
                        'cur_prod': cur_prod,
                        'next_prods': response.meta['next_prods'][1:]
                    },
                    dont_filter=True
                )

def _reformat_mfrgid(mfrgid):
    import string
    chars_to_remove = string.whitespace + "-_."
    return _remove_chars(mfrgid, chars_to_remove).lower()

def _remove_chars(x, chars=None):
    if not chars:
        import string
        chars = string.whitespace
    res = x
    for c in chars:
        res = res.replace(c, "")
    return res