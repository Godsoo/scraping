import re
import os
import time
import json
from urlparse import urljoin

from scrapy import log
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class HibikeDeSpider(BigSiteMethodSpider):
    name = 'hibike.de'
    allowed_domains = ['hibike.de']
    website_id = 491599
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'
    # download_delay = 0.15

    start_urls = ['http://www.hibike.de/']

    new_system = True
    old_system = False

    identifiers = []

    def parse_full(self, response):
        # set language
        yield Request(self.start_urls[0], callback=self.parse_cats, dont_filter=True)

    def parse_cats(self, response):
        hxs = HtmlXPathSelector(response)
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> PARSE CATS >>>")

        ajax_url = 'http://www.hibike.de/API/ajax.php?method=xref&format=agent&languageID=2'

        mfgs = hxs.select('//select[@id="sel_mfgID"]//option/@value').extract()[1:]
        # mfgs = hxs.select('//select[@id="sel_mfgID"]//option[@value="70175"]/@value').extract()
        groups = hxs.select('//select[@id="sel_groupID"]//option/@value').extract()[1:]

        for mfg_id in mfgs:
            url = add_or_replace_parameter(ajax_url, 'trigger', 'mfg')
            url = add_or_replace_parameter(url, 'groupID', '-1')
            url = add_or_replace_parameter(url, 'mfgID', str(mfg_id))

            yield Request(url, callback=self.parse_ajax)
        '''
        for group_id in groups:
            url = add_or_replace_parameter(ajax_url, 'trigger', 'group')
            url = add_or_replace_parameter(url, 'groupID', str(group_id))
            url = add_or_replace_parameter(url, 'mfgID', '-1')

            yield Request(url, callback=self.parse_ajax)
        '''

    def parse_ajax(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = 'http://www.hibike.de/'

        viewall_url = hxs.select('//a[contains(text(), "click here")]/@href').extract()[0]

        if viewall_url:
            yield Request(urljoin(base_url, viewall_url), callback=self.parse_product_list)

        categories = hxs.select('//tr/td/center/a/@href').extract()
        if categories:
            for category in categories:
                yield Request(urljoin(base_url, category), callback=self.parse_product_list)
        else:
            for elem in self.parse_product_list(response):
                yield elem

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> PARSE PRODUCT LIST >>>")

        for url in hxs.select(u'//div[@class="toc2"]//a/@href').extract():
            yield Request(
                    url=urljoin(base_url, url),
                    callback=self.parse_product_list,
                    meta=response.meta)

        # for url in hxs.select(u'//div[@class="cat_prod_image"]/a/@href').extract():
        for url in hxs.select('//div[@class="mainarea"]/a/@href').extract():
            yield Request(
                    url=urljoin(base_url, url),
                    callback=self.parse_product,
                    meta=response.meta)

        for url in hxs.select('//a[img[contains(@class, "arrow_fwd")]]/@href').extract():
            log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> PARSE NEXT PAGE LIST >>>")
            yield Request(
                    url=urljoin(base_url, url),
                    callback=self.parse_product_list,
                    meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> PARSE PRODUCT >>>")
        product_hash = re.search(r'/product/(\w+)/', response.url).groups()[0]

        products = hxs.select("//table[@width='100%']/tr")

        if not products:
            retry = response.meta.get('retry', 0) + 1
            if retry < 25:
                time.sleep(60)
                self.log('Retrying %s => %s' % (retry, response.url))
                meta = response.meta.copy()
                meta['retry'] = retry
                yield Request(response.url, meta=meta, callback=self.parse_product, dont_filter=True)
                return
            else:
                self.log('Max retry number exceeded')

        for item in products:
            product_loader = ProductLoader(item=Product(), selector=item)

            product_loader.add_value('url', response.url)

            name = item.select("..//td[@class='shaded']/text()").extract()[1].strip()
            try:
                opt = item.select("..//td[@class='shaded']/div/text()").extract()[0].strip()
            except:
                opt = ''
            # log.msg(">>>>>>>>>>>>>>>>>>>>>> name [1] >>> %s" % name)
            if not name:
                try:
                    name = item.select("..//td[@class='shaded'][1]/b/text()[1]").extract()[0].strip()
                except:
                    name = ''
            # log.msg(">>>>>>>>>>>>>>>>>>>>>> name [2] >>> %s" % name)
            if opt:
                name = name + " " + opt
            product_loader.add_value('name', name)

            price = item.select("..//td[@class='shaded']/span/nobr/b/span/text()").extract()
            # log.msg(">>>>>>>>>>>>>>>>>>>>>> price [1] >>> %s" % price)
            if not price:
                price = item.select("..//td[@class='shaded'][2]/nobr/b/text()").extract()
            if not price:
                price = item.select('.//*[@itemprop="price"]/text()').extract()
            # log.msg(">>>>>>>>>>>>>>>>>>>>>> price [2] >>> %s" % price)
            product_loader.add_value('price', price[0].replace(",", ".").split(" ")[0])

            product_loader.add_value('category', response.meta.get('category'))

            img = hxs.select('//a[@class="lightbox"]/img/@src').extract()  # hxs.select(u'//span[@class="link"]//img/@src').extract()
            if img:
                product_loader.add_value('image_url', urljoin(get_base_url(response), img[-1]))
            else:
                try:
                    img = hxs.select(u'//div/a[@class="lightbox"]/img/@src').extract()[0]
                    product_loader.add_value('image_url', img)
                except:
                    pass

            product_loader.add_value('identifier',
                                     item.select('.//span[contains(@id, "askPAM_")]/@id').re(r'askPAM_(.*)')[0].strip())
            product_loader.add_value('sku', product_loader.get_output_value('identifier'))

            brands = hxs.select(u'//select[@id="sel_mfgID"]//option/text()').extract()
            name = product_loader.get_output_value('name').lower()
            for brand in brands:
                brand = brand.split('(')[0].strip()
                if brand.lower() in name:
                    product_loader.add_value('brand', brand)
                    break

            product_ = product_loader.load_item()
            if product_['identifier'] not in self.identifiers:
                self.identifiers.append(product_['identifier'])
                yield product_
            else:
                self.log('%s is duplicated => %s' % (product_['identifier'], product_['url']))

    def closing_parse_simple(self, response):
        for item in super(HibikeDeSpider, self).closing_parse_simple(response):
            if item['identifier'] not in self.identifiers:
                self.identifiers.append(item['identifier'])
                yield item
