import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

def multiply(lst):
    if not lst:
        return [('', 0, '')]

    while len(lst) > 1:
        result = []
        for name0, price0, id0 in lst[0]:
            for name1, price1, id1 in lst[1]:
                result.append((name0 + ' ' + name1, float(price0) + float(price1), id0+'-'+id1))
        lst = [result] + lst[2:]
    return lst[0]


class PkSafetyComSpider(BaseSpider):
    name = 'pksafety.com'
    allowed_domains = ['pksafety.com']
    start_urls = ('http://www.pksafety.com',)
    user_agent = 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:26.0) Gecko/20100101 Firefox/26.0'

    def fix_options(self, option_name, optionval_split):
        if len(optionval_split) == 0:
            return option_name, '0', ''
        else:
            option_price = '0'
            last_value = ''
            opt_id = ''
            if len(optionval_split) > 1:
                #last = optionval_split[len(optionval_split) - 1]
                last = optionval_split[-2]
                optionval_split.remove(last)
                option_price = last.replace(',', '')
                last_value = last
                opt_id = optionval_split[-1]
                optionval_split.remove(opt_id)

            option_value = " ".join(optionval_split)
            option_price = option_price.replace('+','').replace('.0.0','.00').replace('$', '').strip()
            try:
                price = Decimal(option_price)
            except:
                option_price = '0'
                if last_value:
                    option_value = option_value + " " + last_value
            return option_name + ':' + option_value, option_price, opt_id

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="nav-container"]/ul/li/a/@href').extract():
            #url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)


    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        #cats = hxs.select(u'//div[@id="RightColumn"]/table/tr/td/center/div[@class="contentsName"]/a/@href').extract()
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        if products:
            for url in products:
                #if url.split('.')[-1].lower() not in ('htm', 'html'):
                    # Contains links to PDFs as well
                #    continue
                #url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product_list)
        else:
            opt_groups = []
            # def fix_options(what, o):
            #     try:
            #         return (what + ':' + o[0], o[1].replace(',', ''))
            #     except:
            #         return (what + ':' + o[0], '0')
 
            option_names = hxs.select('//fieldset[@class="product-options"]/dl/dt/label/text()').extract()
            for i, option in enumerate(hxs.select('//select[contains(@class, "product-custom-option") or contains(@class, "required-entry")]')):
                what = option_names[i].strip().replace(':','')
                opt_list = option.select(u'./option[@value!="PleaseSelect" and @value!="Please Select" and text()!=""]/text()').extract()[1:]
                option_ids = option.select(u'./option[@value!="PleaseSelect" and @value!="Please Select" and @value!=""]/@value').extract()
                opt_list =  map(lambda x, y: x+[y], [o.split('+') if len(o.split('+'))>1 else o.split('+')+['0'] for o in opt_list], option_ids)
                if opt_list:
                    opt_groups.append([self.fix_options(what, o) for o in opt_list])

            # Extract option from JavaScript code
            try:
                js_options = ''
                for line in response.body.split('\n'):
                    if "spConfig = new Product.Config(" in line:
                        js_options = line.split('spConfig = new Product.Config(')[1].split(');')[0]
                json_options = json.loads(js_options)

                for item in json_options['attributes'].iteritems():
                    options = item[-1]['options']
                    option_ids = []
                    opt_list = []
                    for option in options:
                        option_ids.append(option['id'])
                        opt_list.append(option['label']+'+'+option['price'])
  
                    what = option_names[i].strip().replace(':','')
                    opt_list =  map(lambda x, y: x+[y], [o.split('+') if len(o.split('+'))>1 else o.split('+')+['0'] for o in opt_list], option_ids)
                    opt_groups.append([self.fix_options(what, o) for o in opt_list])
            except:
                log.msg('No JSON options: '+ response.url)

            if len(opt_groups)>4:
                self.log("WARNING: Too many options, using base price only")
                opt_groups = []

            for opt_name, opt_price, opt_id in multiply(opt_groups):
                product_loader = ProductLoader(item=Product(), selector=hxs)
                '''
                if not hxs.select(u'//div[@class="buybox"]'):
                    self.log("WARNING: NOT A PRODUCT")
                    return
                '''

                product_loader.add_value('url', response.url)
                product_loader.add_xpath('name', u'//h1/text()')

                if hxs.select('//tr[td/text()="Sale Price"]/td[text()!="Sale Price"]/text()'):#FIXME: fix the other prices
                    product_loader.add_xpath('price', u'//tr[td/text()="Sale Price"]/td[text()!="Sale Price"]/text()')
                elif hxs.select('//td/span[@class="price"]/text()'):
                    product_loader.add_xpath('price', u'//td/span[@class="price"]/text()')
                else:
                    product_loader.add_xpath('price', u'//div[@class="itemRegPrice"]/span/font/text()')

                sku = hxs.select('//tr[th/text()="MPN"]/td/text()').extract()
                sku = sku[0] if sku else ''
                product_loader.add_value('sku', sku)
                product_loader.add_xpath('category', u'//div[@class="breadcrumbs"]/ul/li[contains(@class, "category")]/a/text()')
                product_loader.add_xpath('image_url', u'//div[@class="product-img-box"]//div[@class="prolabel-wrapper"]/a/img/@src')
#            product_loader.add_xpath('brand', u'substring-after(//div[@class="product-meta"]/span[contains(text(),"Manufacturer:")]/text(),":")')
                product_loader.add_value('shipping_cost', '')
                identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
                if opt_id:
                    product_loader.add_value('identifier', identifier+'-'+opt_id)
                else:
                    product_loader.add_value('identifier', identifier)

                product = product_loader.load_item()
                product['name'] = (product['name'] + ' ' + opt_name).strip()

                if not 'price' in product:
                    product['price'] = Decimal(0)
                    self.log('ERROR price is not set, setting to default 0')
                else:
                    product['price'] = product['price'] + Decimal(opt_price)

                yield product

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_product_list)
        
