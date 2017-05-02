'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5244
'''

import json
from hashlib import md5
from itertools import product as iter_product
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class SaxoPrints(Spider):
    name = 'instantprint-saxoprints'
    allowed_domains = ['saxoprint.co.uk']
    start_urls = ['http://www.saxoprint.co.uk/']

    concurrent_requests = 1

    def __init__(self, *args, **kwargs):
        super(SaxoPrints, self).__init__(*args, **kwargs)

        self.categories = {
            'Flyers': {
                'url': 'http://www.saxoprint.co.uk/shop/flyers',
                'qty': [1, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000, 15000,
                        20000, 25000, 30000, 40000, 50000],
                # 'qty': [1000],
                'ProductGroupAssortment': ['Flyers'],
                'TrimmedSize': ['A3', 'A4', 'A5', 'A6', 'A7', 'DL', '148 x 148', '210 x 210'],
                # 'TrimmedSize': ['A4'],
                'Paper': ['170gsm silk', '250gsm silk', '300gsm silk'],
                # 'Paper': ['135gsm silk'],
                'Refinement': ['lamination', 'no finishing'],
                'RefinementPage': ['front/back'],
                'LaquerEffect': ['gloss finish', 'matt finish'],
                'set_values': [600],  # Set Refinement as lamination to extract all the options
                'restrictions': {
                    'lamination': ['gloss finish', 'matt finish', 'front/back'],
                },
                'filter_ids': ['ProductGroupAssortment', 'TrimmedSize',
                               'Page', 'Paper', 'Refinement', 'LaquerEffect', 'RefinementPage']
            },
        }

    def parse(self, response):
        cookie_no = 0
        for category, data in self.categories.iteritems():
            cookie_no += 1
            yield Request(data['url'],
                          meta={'cat_name': category, 'cat_attrs': data,
                                'cookiejar': cookie_no},
                          callback=self.parse_category)

    def parse_category(self, response):
        try:
            json_conf = json.loads(response.xpath('//script/text()').re('tcs = ({.+})')[0])
        except IndexError:
            return
        option_names = dict(json_conf['i'])

        tab_session_id = response.css('div#tabSessionId::text').extract_first()
        product_group = response.css('div#ProductGroupHf::text').extract_first()
        product_groups = response.css('div#ProductGroupsHf::text').extract_first()
        payload = {'productGroup': int(product_group),
                   'switchableProductGroups': json.loads(product_groups),
                   'tabSessionId': tab_session_id}

        new_meta = response.meta.copy()
        new_meta['option_names'] = option_names
        new_meta['tab_session_id'] = tab_session_id
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Content-Type': 'application/json; charset=utf-8',
                   'X-Requested-With': 'XMLHttpRequest'}
        req = Request('http://www.saxoprint.co.uk/print.svc/Init',
                      method='POST',
                      headers=headers,
                      body=json.dumps(payload),
                      meta=new_meta,
                      callback=self.parse_init)
        return req

    def parse_init(self, response):
        data = json.loads(response.body)
        data = json.loads(data['d'])
        data_conf = data['conf']
        cat_attrs = response.meta['cat_attrs']
        if 'set_values' in cat_attrs and cat_attrs['set_values']:
            next_val = response.meta['cat_attrs']['set_values'].pop(0)
            headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Content-Type': 'application/json; charset=utf-8',
                       'X-Requested-With': 'XMLHttpRequest'}
            params = {
                'value': next_val,
                'tabSessionId': response.meta['tab_session_id'],
            }
            req = Request('http://www.saxoprint.co.uk/print.svc/ValueChanged',
                          method='POST',
                          headers=headers,
                          body=json.dumps(params),
                          meta=response.meta,
                          callback=self.parse_init,
                          dont_filter=True)
            yield req
            return
        quantities = [int(q.replace(',', '')) for q in data_conf['tsl']]
        quantities = filter(lambda q: q in cat_attrs['qty'], quantities)

        response.meta['quantities'] = quantities

        option_names = response.meta['option_names']

        adr = data_conf['adr']
        filtered_adr = filter(lambda o: o['c'] in cat_attrs['filter_ids'], adr)

        options = []
        for bix, i in enumerate(filtered_adr):
            options.append([])
            for j in i['items']:
                valid_option = True
                if i['c'] in cat_attrs:
                    valid_option = any([v in option_names[j['v']] for v in cat_attrs[i['c']]])
                if valid_option:
                    options[bix].append((j['v'], option_names[j['v']]))

        # Remove empty options
        options = filter(lambda o: bool(o), options)
        self.log('%r' % options)
        variants = list(iter_product(*options))
        cleaned_variants = []
        for variant in variants:
            is_valid = True
            full_name = ' - '.join([v[1] for v in variant])
            for k, r in cat_attrs['restrictions'].items():
                if k in full_name:
                    is_valid = any([v in full_name for v in r])
                else:
                    is_valid = False
                    new_variant = []
                    for v in variant:
                        if not any([y in v for y in r]):
                            new_variant.append(v)
                    cleaned_variants.append(tuple(new_variant))
                if not is_valid:
                    break
            if is_valid:
                cleaned_variants.append(variant)
        variants = list(set(cleaned_variants))
        self.log('%r' % variants)
        response.meta['variants'] = variants

        for i in self.parse_variant(response):
            yield i

    def parse_quantity(self, response):
        qix = response.meta.get('qix')
        if qix is None:
            qix = 0
        else:
            qix += 1
        if qix >= len(response.meta['quantities']):
            response.meta['qix'] = -1
            for i in self.parse_variant(response):
                yield i
        else:
            next_qty = response.meta['quantities'][qix]
            new_meta = response.meta.copy()
            new_meta['qty_selected'] = next_qty
            new_meta['qix'] = qix
            headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Content-Type': 'application/json; charset=utf-8',
                       'X-Requested-With': 'XMLHttpRequest'}
            params = {
                'circulation': next_qty,
                'tabSessionId': response.meta['tab_session_id'],
            }
            req = Request('http://www.saxoprint.co.uk/print.svc/CirculationChanged',
                          method='POST',
                          headers=headers,
                          body=json.dumps(params),
                          meta=new_meta,
                          callback=self.parse_product,
                          dont_filter=True)
            yield req
        yield None

    def parse_variant(self, response):
        variants = response.meta['variants']
        bix = response.meta.get('bix_selected')
        oix = response.meta.get('oix_selected')
        if bix is None:
            bix = 0
        if oix is None:
            oix = 0
        else:
            oix += 1

        if bix < len(variants) and oix >= len(variants[bix]):
            oix = 0
            bix += 1
            response.meta['oix_selected'] = oix
            response.meta['bix_selected'] = bix
            self.log('Parse Quantities: BIX: %s, OIX: %s' % (bix, oix))
            for i in self.parse_quantity(response):
                yield i
            return

        if bix < len(variants):
            new_meta = response.meta.copy()
            next_val = variants[bix][oix][0]
            new_meta['bix_selected'] = bix
            new_meta['oix_selected'] = oix
            headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Content-Type': 'application/json; charset=utf-8',
                       'X-Requested-With': 'XMLHttpRequest'}
            params = {
                'value': next_val,
                'tabSessionId': response.meta['tab_session_id'],
            }
            self.log('Value Changed: BIX: %s, OIX: %s' % (bix, oix))
            req = Request('http://www.saxoprint.co.uk/print.svc/ValueChanged',
                          method='POST',
                          headers=headers,
                          body=json.dumps(params),
                          meta=new_meta,
                          callback=self.parse_variant,
                          errback=lambda failure, response = response: self.ignore_variant(failure, response),
                          dont_filter=True)
            yield req
        yield None

    def ignore_variant(self, f, r):
        r.meta['bix_selected'] += 1
        r.meta['oix_selected'] = 0
        for i in self.parse_variant(r):
            yield i

    def parse_product(self, response):
        data = json.loads(response.body)
        data = json.loads(data['d'])
        price_data = data['price']

        cat_attrs = response.meta['cat_attrs']

        data_conf = data['conf']
        option_names = response.meta['option_names']

        adr = data_conf['adr']
        filtered_adr = filter(lambda o: o['c'] in cat_attrs['filter_ids'], adr)

        current_selected = []
        for option in filtered_adr:
            for i in option['items']:
                if i['s']:
                    current_selected.append((i['v'], option_names[i['v']]))
                    break

        qty_selected = response.meta.get('qty_selected', data_conf['defc'])
        product_name = ' - '.join([c[1] for c in current_selected])
        product_name += ' - ' + str(qty_selected)
        if '- lamination -' in product_name:
            product_price = price_data['CustomerGrossValue']
        else:
            product_price = price_data['CustomerNetValue']

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', md5(product_name.encode('utf-8')).hexdigest())
        loader.add_value('name', product_name)
        loader.add_value('url', cat_attrs['url'])
        loader.add_value('price', product_price)
        loader.add_value('category', response.meta['cat_name'])
        item = loader.load_item()
        item['metadata'] = {'ProdQty': str(qty_selected)}
        yield item

        # Go Next option
        for i in self.parse_quantity(response):
            yield i
