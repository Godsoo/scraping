from scrapy import Spider, Request, FormRequest
from product_spiders.items import Product, ProductLoader
from itertools import product as iter_product
from hashlib import md5
from decimal import Decimal
import json


QTY_VALUES = [
    1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150,
    200, 250, 300, 400, 500, 600, 700, 750, 800,
    900, 1000, 1250, 1500, 1750, 2000, 2250, 2500,
    2750, 3000, 3500, 4000, 4500, 5000, 10000, 15000,
    20000, 25000, 30000, 40000, 50000]

NAME_REPLACEMENTS = {
    'A3-Square': 'Square 29.7 cm',
    'A4-Square': 'Square 21 cm',
    'A5-Square': 'Square 14.8 cm',
    'A6-Square': 'Square 10.5 cm'
}


class OnlinePrintersSpider(Spider):
    name = 'instantprint-onlineprinters.co.uk'
    allowed_domains = ['onlineprinters.co.uk']
    start_urls = [
        'https://www.onlineprinters.co.uk/Flyers-%26-Leaflets.htm?websale8=diedruckerei.08-aa&ci=006953',
    ]
    max_depth = 2
    explored_options = set()
    paper_types = ['170', '250', '350']
    PAGE_SAVED = False

    def start_requests_(self):
        yield Request('https://www.onlineprinters.co.uk/Multi-pack,-Flyers-DIN-A6.htm?websale8=diedruckerei.08-aa&pi=MFLA644&ci=006961',
                      callback=self.parse_product,
                      meta=dict(main_url='https://www.onlineprinters.co.uk/Multi-pack,-Flyers-DIN-A6.htm?websale8=diedruckerei.08-aa&pi=MFLA644&ci=006961'))
    def parse(self, response):
        subcats = response.xpath('//div[@class="cat_box_wrapper_link"]/a/@href').extract()
        for subcat_url in subcats:
            yield Request(response.urljoin(subcat_url),
                          callback=self.parse)

        products = response.xpath('//a[@class="cat_table_links"]/@href').extract()
        for product_url in products:
            yield Request(response.urljoin(product_url),
                          meta={'main_url': response.urljoin(product_url)},
                          callback=self.parse_product)

    def parse_product(self, response):
        paper_types_extracted = response.meta.get('paper_types_extracted', False)
        paper_types_sel = response.xpath('//select[option[contains(text(),"g/m")]]')
        if not paper_types_extracted and paper_types_sel:
            meta = response.meta
            meta['paper_types_extracted'] = True
            paper_types_sel_name = paper_types_sel.xpath('@name')[0].extract()
            for paper_type in paper_types_sel.xpath('option/@value').extract():
                if any([v in paper_type for v in self.paper_types]):
                    formdata = {paper_types_sel_name: paper_type}
                    meta.update(formdata)
                    yield FormRequest.from_response(response,
                                                    formdata=formdata.copy(),
                                                    formxpath='//form[@id="productform"]',
                                                    callback=self.parse_product,
                                                    meta=meta)
            return

        product_sku = response.xpath('//form[@id="productform"]//input[@name="prod_index_1"]/@value').extract()[0]
        product_name = response.xpath('//*[@id="opadDescriptionTitle"]/text()').extract()[0]
        for old, new in NAME_REPLACEMENTS.items():
            if old in product_name:
                product_name = product_name.replace(old, new)
                break
        product_url = response.meta['main_url']
        categories = response.xpath('//div[@class="breadcrumbs"]//*[@itemprop="title"]/text()').extract()[:-1]
        main_selects = response.xpath('//h3[contains(text(), "Additional options")]')[-1]\
                               .xpath('.//preceding-sibling::div[@class="box_content_mitte"]//select')
        print_run_select = None
        last_option_desc = main_selects[-1].xpath('parent::p/preceding-sibling::div/text()').extract()[0]
        if last_option_desc == 'Print run':
            print_run_select = main_selects[-1]
            main_selects = main_selects[0:-1]
        lamination = response.xpath('//select[contains(@name, "input_var_") and '
                                    '(.//option[contains(text(), "matt film")] or '
                                    './/option[contains(text(), "glossy film")])]')
        if lamination:
            main_selects += lamination
        coat = response.xpath('//select[contains(@name, "input_var_") and '
                              '(.//option[contains(text(), "matt coat")] or '
                              './/option[contains(text(), "glossy coat")])]')
        if coat:
            main_selects += coat

        options = []
        selected_options = []
        options_keys = [] # To use in form data
        for sel_xs in main_selects:
            s_name = sel_xs.xpath('@name').extract()[0]
            if s_name not in options_keys:
                options_keys.append(s_name)
                if s_name in response.meta.keys():
                    options.append([response.meta.get(s_name)])
                else:
                    options.append(sel_xs.xpath('option/@value').extract())
                selected_options.append(sel_xs.xpath('option[@selected]/@value').extract()[0])
        options = filter(lambda ops: bool(ops), options)  # discard empty groups

        options_processed = response.meta.get('options_processed', False)
        if not options_processed:
            meta = response.meta.copy()
            meta['options_processed'] = True
            for amount in print_run_select.xpath('./option/@value').extract():
                if int(amount) not in QTY_VALUES: continue
                amount_sel_name = print_run_select.xpath('./@name')[0].extract()
                for options_comb in iter_product(*options):
                    formdata = {}
                    for i, opt_value in enumerate(options_comb):
                        formdata[options_keys[i]] = opt_value
                    formdata[amount_sel_name] = amount
                    opt_key = u'{}-{}'.format(product_sku, json.dumps(sorted(formdata.items())))
                    if opt_key in self.explored_options:
                        continue
                    self.explored_options.add(opt_key)
                    meta['opt_key'] = opt_key
                    yield FormRequest.from_response(response,
                                                    formdata=formdata.copy(),
                                                    formxpath='//form[@id="productform"]',
                                                    callback=self.parse_product,
                                                    meta=meta)

        if selected_options:
            product_name += ' - ' + ' - '.join(selected_options)

        # Unencrypted
        product_identifier_base = product_sku + ''.join(selected_options)

        if print_run_select is not None:
            selected_amount = print_run_select.xpath('./option[@selected]/@value')[0].extract()
            for pr_xs_opt in print_run_select.xpath('option[@value="{}"]/text()'.format(selected_amount)):
                pr_total, pr_price = pr_xs_opt.re(r'[\d\.,]+')
                add_prices = response.xpath('//p[@class="product_depvariation_aufpreis"]/b/text()').re(r'([-\d\.,]+)')
                qty = int(pr_total.replace('.', '').replace(',', ''))
                if qty not in QTY_VALUES:
                    continue
                product_identifier = md5((product_identifier_base + pr_total).encode('utf-8')).hexdigest()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', product_identifier)
                loader.add_value('name', product_name + ' - ' + pr_total)
                loader.add_value('sku', product_sku)
                loader.add_value('price', pr_price)
                loader.add_value('url', product_url)
                loader.add_value('category', categories)
                item = loader.load_item()
                if item['price']:
                    for add_price in add_prices:
                        item['price'] += Decimal(add_price.replace(',', ''))
                        self.log('{}=>{}'.format(item['identifier'], add_price))
                    if 'matt film' not in item['name'].lower() and 'glossy film' not in item['name'].lower():
                        item['price'] = (item['price'] / Decimal('1.2')).quantize(Decimal('0.01'))
                item['metadata'] = {'ProdQty': qty}
                self.log('OPT_KEY={}'.format(response.meta.get('opt_key', '')))
                yield item
        else:
            product_price = response.xpath('//*[@id="pr_basispreis"]/text()').re(r'[\d\.,]+')
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', md5(product_identifier_base.encode('utf-8')).hexdigest())
            loader.add_value('name', product_name)
            loader.add_value('sku', product_sku)
            loader.add_value('price', product_price)
            loader.add_value('url', product_url)
            loader.add_value('category', categories)
            item = loader.load_item()
            if item['price']:
                item['price'] = (item['price'] * Decimal('1.2')).quantize(Decimal('0.01'))
            yield item
