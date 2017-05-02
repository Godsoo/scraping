import re
from scrapy import Spider, Request, FormRequest
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoader
from hashlib import md5
from decimal import Decimal


def process_next_request(func):
    def new_func(self, response):
        if response.meta.get('callback_list'):
            next_callback = response.meta['callback_list'].pop(0)
            product_id = response.meta['product_id']
            for meta in func(self, response):
                meta['callback_list'] = list(response.meta['callback_list'])
                next_request = self.create_request_by_callback(product_id, meta, meta['values'],
                        next_callback[0], *next_callback[1:])
                yield next_request
        elif response.meta.get('request_list'):
            next_request = response.meta['request_list'].pop(0)
            for meta in func(self, response):
                meta['request_list'] = list(response.meta['request_list'])
                req = next_request.replace(meta=meta)
                req.dont_filter = True
                yield req
        else:
            for meta in func(self, response):
                self._forms_to_process.append((self.get_formdata(meta), meta))
    return new_func


class PrintedSpider(Spider):
    name = 'instantprint-printed.com'
    allowed_domains = ['printed.com']
    start_urls = ['https://www.printed.com/site-map']

    def __init__(self, *args, **kwargs):
        self._forms_to_process = []
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        self.log('>> SPIDER IDLE')
        if self._forms_to_process:
            args = self._forms_to_process.pop(0)
            request = self.save_options(*args)
            self.crawler.engine.crawl(request, self)
        else:
            request = self.get_next_request()
            if request:
                self.crawler.engine.crawl(request, self)

    def get_next_request(self):
        self.log('>> GET NEXT REQUEST')
        if self._products:
            prod_name, prod_url, rules, filters, metafields = self._products.pop(0)
            return Request(prod_url,
                           meta={'product_name': prod_name,
                                 'product_url': prod_url,
                                 'rules': rules,
                                 'filters': filters,
                                 'metafields': metafields,
                                 'metadata': {},
                                 'formdata': {},
                                 'values': {},
                                 'callback_list': [],
                                 'request_list': []},
                           callback=self.parse_options)
        return None

    def create_request_by_callback(self, product_id, meta, values, callback, *args):
        params_values = []
        for a in args:
            if '{constant}' in a:
                params_values.append(a.split('{constant}')[-1])
            elif a == '{meta}':
                # pass over meta as parameter
                params_values.append(meta)
            else:
                try:
                    params_values.append(values[a])
                except:
                    self.log('ERROR!!! => %r, %r' % (callback, values))
                    return None
        req = callback(product_id, *params_values)
        if req is not None:
            req = req.replace(meta=meta)
            req.dont_filter = True
        return req

    def parse(self, response):
        self._products = [
            ('Leaflets & Flyers', 'https://www.printed.com/order-wizard/product-options/leaflets--flyers',
             {'coreNumberOfTypes': '1',
              'coreQuantity': '{copy}pdc-core-quantity',
              'fileUploadFlow': 'upload',
              'productSubCategory': '',
              'formdata': [
                  ('pdc-core-number-of-types', [('default', '1')]),
                  ('multiple', [('default', 'No')]),
                  ('paper-type-list-count-alt', [('default', 'twelve')]),
                  ('paper-size',
                   ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
                  ('paper-type',
                   ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
                  ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
                  ('lamination-options',
                   ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
                  ('lamination-finish', ['//section[@id="wizard-section-lamination-finish"]//input[@name="lamination-finish"]']),
                  ('orientation', [['portrait']]),
                  ('perforation', [(self.get_valid_perforation_options, 'paper-size')]),
                  ('pdc-core-quantity', [[1, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000,
                                          15000, 20000, 25000, 30000, 40000, 50000]]),
                  ('pdc-core-quantity-dropdown', [('copy', 'pdc-core-quantity')]),
                  ('print-type', [(self.force_save_options, '{meta}'), (self.get_printing_type,)]),
                  ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type', 'print-type')]),
                  ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
              ]},
             {'paper-size': ['460', '462', '464', '463', '461', '458', '457', '459'],
              'paper-type': ['520'],
              'paper-weight': ['539', '546', '550', '897']},
             {'paper-size': 'PaperSize',
              'paper-type': 'PaperType',
              'sides': 'PrintType',
              'lamination-finish': 'LaminationType',
              'paper-weight': 'PaperType',
              'pdc-core-quantity': 'ProdQty'}),  #### END Leaflets & Flyers ####
            # ('Folded Leaflets', 'https://www.printed.com/order-wizard/product-options/folded-leaflets',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('pdc-core-number-of-types', [('default', '1')]),
            #       ('multiple', [('default', 'No')]),
            #       ('paper-type-list-count-alt', [('default', 'twelve')]),
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options',
            #        ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
            #       ('fold-type', [(self.get_fold_type_general, 'paper-size')]),
            #       ('pdc-core-quantity', [[1, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000,
            #                               15000, 20000, 25000, 30000, 40000, 50000]]),
            #       ('pdc-core-quantity-dropdown', [('copy', 'pdc-core-quantity')]),
            #       ('print-type', [(self.force_save_options, '{meta}'), (self.get_printing_type,)]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type', 'print-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-size': ['471', '468', '465'],
            #   'paper-type': ['520'],
            #   'paper-weight': ['539', '546', '550'],
            #   'sides': ['double']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'lamination-options': 'LaminationType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty',
            #   'fold-type': 'FoldingType'}),  #### END OF Folded Leaflets ####
            # ('Indoor Posters', 'https://www.printed.com/order-wizard/product-options/indoor-posters',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('custom-width', [('default', '')]),
            #       ('custom-height', [('default', '')]),
            #       ('lamination-list', [('default', 'none')]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150, 200, 250, 500,
            #                               1000, 2000, 5000]]),
            #       ('orientation', [['portrait']]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['881', '882', '857', '855', '856', '464'],
            #   'paper-type': ['1120'],
            #   'paper-weight': ['536'],
            #   'sides': ['single']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Indoor Posters ####
            # ('Outdoor Posters', 'https://www.printed.com/order-wizard/product-options/outdoor-posters',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('custom-width', [('default', '')]),
            #       ('custom-height', [('default', '')]),
            #       ('lamination-list', [('default', 'none')]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150, 200, 250, 500,
            #                               1000, 2000, 5000]]),
            #       ('orientation', [['portrait']]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['881', '882', '857', '855', '856', '464'],
            #   'sides': ['single']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Outdoor Posters ####
            # ('Standard Posters', 'https://www.printed.com/order-wizard/product-options/standard-posters-a2-only',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options', [('default', 'none')]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150, 200, 250, 500,
            #                               1000, 2000, 5000]]),
            #       ('orientation', [['portrait']]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['915'],
            #   'paper-type': ['522'],
            #   'paper-weight': ['542'],
            #   'sides': ['single']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Standard Posters ####
            # ('Stationery', 'https://www.printed.com/order-wizard/product-options/stationery/gallery',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'gallery',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('pdc-core-quantity', [[25, 50, 100, 250, 500, 1000, 2000, 5000, 10000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['463'],
            #   'paper-type': ['522'],
            #   'paper-weight': ['536']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Standard Posters ####
            # ('Business Cards', 'https://www.printed.com/order-wizard/product-options/business-cards/gallery',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'gallery',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options',
            #        ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
            #       ('lamination-finish', ['//section[@id="wizard-section-lamination-finish"]//input[@name="lamination-finish"]']),
            #       ('orientation', [['landscape']]),
            #       ('pdc-core-quantity', [[50, 100, 250, 500, 1000, 2000, 5000, 10000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-type': ['520', '522', '1092', '1093']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'lamination-finish': 'LaminationType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Business Cards ####
            # ('Banners', 'https://www.printed.com/order-wizard/product-options/banners',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('custom-width', [('default', '')]),
            #       ('custom-height', [('default', '')]),
            #       ('orientation', [['landscape']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10, 25, 50, 100, 250, 500, 1000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('eyelets', ['//section[@id="wizard-section-eyelets"]//input[@name="eyelets"]']),
            #   ]},
            #  {'paper-size': ['873']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Banners ####
            # ('Standard Roller Banner', 'https://www.printed.com/order-wizard/product-options/standard-roller-banner',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['993']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Standard Roller Banner ####
            # ('Deluxe Roller Banner', 'https://www.printed.com/order-wizard/product-options/deluxe-roller-banner',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['995']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Deluxe Roller Banner ####
            # ('Genie Banner Stand', 'https://www.printed.com/order-wizard/product-options/genie-banner-stand',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['996']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Genie Banner Stand ####
            # ('Twin Banner Stand', 'https://www.printed.com/order-wizard/product-options/twin-banner-stand',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['994']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Twin Banner Stand ####
            # ('Sidewinder 800mm Banner Stand', 'https://www.printed.com/order-wizard/product-options/sidewinder800mm-banner-stand',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['1000']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Sidewinder 800mm Banner Stand ####
            # ('Sidewinder 1000mm Banner Stand', 'https://www.printed.com/order-wizard/product-options/sidewinder1000mm-banner-stand',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['997']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Sidewinder 1000mm Banner Stand ####
            # ('Photography Standard Banner Stand', 'https://www.printed.com/order-wizard/product-options/photography-standard-banner-stand',
            #  {'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['portrait']]),
            #       ('banner-type', [['993']]),
            #       ('pdc-core-quantity', [[1, 2, 3, 4, 5, 10]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Photography Standard Banner Stand ####
            # ('Flat Invitations', 'https://www.printed.com/order-wizard/product-options/flat-invitations',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['landscape']]),
            #       ('paper-type-list-count-alt', [('default', 'seven')]),
            #       ('personalisation', [('default', 'N')]),
            #       ('envelopes', ['//section[@id="wizard-section-envelopes"]//input[@name="envelopes"]']),
            #       ('pdc-core-quantity', [[1, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000,
            #                               15000, 20000, 25000, 30000, 40000, 50000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-size': ['458', '459'],
            #   'paper-type': ['524', '527', '530', '531', '532'],
            #   'paper-weight': ['548', '550'],
            #   'envelopes': ['852']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Flat Invitations ####
            # ('Wedding Invitations', 'https://www.printed.com/order-wizard/product-options/wedding-invitations',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options',
            #        ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
            #       ('orientation', [['landscape']]),
            #       ('paper-type-list-count-alt', [('default', 'eleven')]),
            #       ('personalisation', [('default', 'N')]),
            #       ('envelopes', ['//section[@id="wizard-section-envelopes"]//input[@name="envelopes"]']),
            #       ('pdc-core-quantity', [[1, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000,
            #                               15000, 20000, 25000, 30000, 40000, 50000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-size': ['458', '459'],
            #   'paper-type': ['520'],
            #   'paper-weight': ['548', '550'],
            #   'envelopes': ['852']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'lamination-options': 'LaminationType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Wedding Invitations ####
            # ('Greeting Cards', 'https://www.printed.com/order-wizard/product-options/greeting-cards',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-type-list-count-alt', [('default', 'ten')]),
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options',
            #        ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
            #       ('personalisation', [('default', 'N')]),
            #       ('envelopes', ['//section[@id="wizard-section-envelopes"]//input[@name="envelopes"]']),
            #       ('fold-type', [(self.get_fold_type_general, 'paper-size')]),
            #       ('pdc-core-quantity', [[25, 50, 100, 250, 500, 1000, 2000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-size': ['491', '493'],
            #   'paper-type': ['520'],
            #   'paper-weight': ['550'],
            #   'lamination-options': ['none'],
            #   'envelopes': ['852'],
            #   'fold-type': ['515'],
            #   'corners': ['799']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'lamination-options': 'LaminationType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty',
            #   'fold-type': 'FoldingType'}),  #### END OF Greeting Cards ####
            # ('Postcards', 'https://www.printed.com/order-wizard/product-options/postcards',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('lamination-options',
            #        ['//*[@id="wizard-section-lamination-options"]//input[@name="lamination-options"]']),
            #       ('lamination-finish', ['//section[@id="wizard-section-lamination-finish"]//input[@name="lamination-finish"]']),
            #       ('orientation', [['landscape']]),
            #       ('paper-type-list-count-alt', [('default', 'twelve')]),
            #       ('envelopes', ['//section[@id="wizard-section-envelopes"]//input[@name="envelopes"]']),
            #       ('pdc-core-quantity', [[100, 250, 500, 1000, 2000, 5000, 10000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #       ('corners', ['//*[@id="wizard-section-corner-options"]//input[@name="corners"]']),
            #   ]},
            #  {'paper-size': ['458'],
            #   'paper-type': ['520'],
            #   'paper-weight': ['550'],
            #   'envelopes': ['852'],
            #   'lamination-options': ['one', 'both'],
            #   'lamination-finish': ['gloss'],
            #   'corners': ['799']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'lamination-finish': 'LaminationType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Postcards ####
            # ('Round Stickers', 'https://www.printed.com/order-wizard/product-options/round-stickers',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('pdc-core-quantity', [[100, 250, 500, 750, 1000, 1500, 2000, 5000, 10000, 15000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['479', '482', '483']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Round Stickers ####
            # ('Square Stickers', 'https://www.printed.com/order-wizard/product-options/square-stickers',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('pdc-core-quantity', [[100, 250, 500, 750, 1000, 1500, 2000, 5000, 10000, 15000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['474']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Square Stickers ####
            # ('Rectangle Stickers', 'https://www.printed.com/order-wizard/product-options/rectangle-stickers',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('pdc-core-quantity', [[100, 250, 500, 750, 1000, 1500, 2000, 5000, 10000, 15000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {'paper-size': ['488', '489']},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Rectangle Stickers ####
            # ('Address Labels', 'https://www.printed.com/order-wizard/product-options/address-labels',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['landscape']]),
            #       ('pdc-core-quantity', [[100, 250, 500, 750, 1000, 1500, 2000, 5000, 10000, 15000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Address Stickers ####
            # ('Return Address Labels', 'https://www.printed.com/order-wizard/product-options/return-address-labels',
            #  {'coreNumberOfTypes': '1',
            #   'coreQuantity': '{copy}pdc-core-quantity',
            #   'fileUploadFlow': 'upload',
            #   'productSubCategory': '',
            #   'formdata': [
            #       ('paper-size',
            #        ['//section[@id="wizard-section-paper-size"]//input[@name="paper-size"]']),
            #       ('paper-type',
            #        ['//div[@id="wizard-section-paper-type-list"]//input[@name="paper-type"]']),
            #       ('sides', ['//section[@id="wizard-section-sides"]//input[@name="sides"]']),
            #       ('orientation', [['landscape']]),
            #       ('pdc-core-quantity', [[100, 250, 500, 750, 1000, 1500, 2000, 5000, 10000, 15000]]),
            #       ('paper-weight', [(self.get_paper_weights_general, 'paper-size', 'paper-type')]),
            #   ]},
            #  {},
            #  {'paper-size': 'PaperSize',
            #   'paper-type': 'PaperType',
            #   'sides': 'PrintType',
            #   'paper-weight': 'PaperType',
            #   'pdc-core-quantity': 'ProdQty'}),  #### END OF Return Address Labels ####
        ]

        yield self.get_next_request()

    @process_next_request
    def parse_nothing(self, response):
        yield response.meta

    # Return request
    def get_orientation_general(self, product_id, size_id):
        url = 'https://www.printed.com/order-wizard/ajax/options/get-orientation-general'
        formdata = {
            'paperSizeId': size_id,
            'productId': product_id,
        }
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            formdata=formdata,
            callback=self.parse_orientation)

    @process_next_request
    def parse_orientation(self, response):
        orientations = response.xpath('//orientation')
        for orientation_xs in orientations:
            orientation_id = orientation_xs.xpath('id/text()').extract()[0]
            orientation_name = orientation_xs.xpath('name/text()').extract()[0]
            # Apply filters
            if self._excluded_value('orientation', orientation_id, response.meta['filters']):
                continue
            meta = response.meta.copy()
            meta['formdata'] = response.meta['formdata'].copy()
            meta['values'] = response.meta['values'].copy()
            meta['metadata'] = response.meta['metadata'].copy()
            meta['product_name'] += ' - ' + orientation_name.strip()
            if 'orientation' in meta['metafields']:
                self._add_item_metadata(meta, orientation_name, meta['metafields']['orientation'])
            ix = len(meta['formdata']) / 2
            meta['formdata']['formData[%s][name]' % ix] = 'orientation'
            meta['formdata']['formData[%s][value]' % ix] = orientation_id
            meta['values']['orientation'] = orientation_id
            yield meta

   # Return request
    def get_fold_type_general(self, product_id, size_id):
        url = 'https://www.printed.com/order-wizard/ajax/options/get-fold-type-general'
        formdata = {
            'paperSizeId': size_id,
            'productId': product_id,
        }
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            formdata=formdata,
            callback=self.parse_fold_type)

    @process_next_request
    def parse_fold_type(self, response):
        fold_types = response.xpath('//foldType')
        for fold_type_xs in fold_types:
            fold_type_id = fold_type_xs.xpath('id/text()').extract()[0]
            fold_type_name = fold_type_xs.xpath('name/text()').extract()[0]
            # Apply filters
            if self._excluded_value('fold-type', fold_type_id, response.meta['filters']):
                continue
            meta = response.meta.copy()
            meta['formdata'] = response.meta['formdata'].copy()
            meta['values'] = response.meta['values'].copy()
            meta['metadata'] = response.meta['metadata'].copy()
            meta['product_name'] += ' - ' + fold_type_name.strip()
            if 'fold-type' in meta['metafields']:
                self._add_item_metadata(meta, fold_type_name, meta['metafields']['fold-type'])
            ix = len(meta['formdata']) / 2
            meta['formdata']['formData[%s][name]' % ix] = 'fold-type'
            meta['formdata']['formData[%s][value]' % ix] = fold_type_id
            meta['values']['fold_type'] = fold_type_id
            yield meta

    # Return request
    def get_printing_type(self, product_id):
        url = 'https://www.printed.com/order-wizard/ajax/options/get-printing-type'
        formdata = {
            'productId': product_id,
        }
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            formdata=formdata,
            callback=self.parse_printing_type)

    @process_next_request
    def parse_printing_type(self, response):
        printing_type = response.xpath('//printingType/text()').extract()[0]
        meta = response.meta.copy()
        meta['values']['print-type'] = printing_type
        yield meta

    # Return request
    def get_paper_weights_general(self, product_id, size_id, type_id, printing_type='1'):
        url = 'https://www.printed.com/order-wizard/ajax/options/get-paper-weights-general'
        formdata = {
            'multipageOption': '0',
            'paperSizeId': size_id,
            'paperTypeId': type_id,
            'printingType': printing_type,
            'productId': product_id,
        }
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            formdata=formdata,
            callback=self.parse_weights)

    @process_next_request
    def parse_weights(self, response):
        lamination_restriction_found = bool(
            response.xpath('//restrictedPropertyType/name[text()="Lamination"]'))
        lamination_option = response.meta['values'].get('lamination-options', 'none')
        if lamination_restriction_found and lamination_option != 'none':
            return

        paper_weights = response.xpath('//paperWeight')
        for paper_weight_xs in paper_weights:
            paper_weight_id = paper_weight_xs.xpath('id/text()').extract()[0]
            paper_weight_name = paper_weight_xs.xpath('name/text()').extract()[0]
            # Apply filters
            if self._excluded_value('paper-weight', paper_weight_id, response.meta['filters']):
                continue
            meta = response.meta.copy()
            meta['formdata'] = response.meta['formdata'].copy()
            meta['values'] = response.meta['values'].copy()
            meta['metadata'] = response.meta['metadata'].copy()
            meta['product_name'] += ' - ' + paper_weight_name.strip()
            if 'paper-weight' in meta['metafields']:
                self._add_item_metadata(meta, paper_weight_name, meta['metafields']['paper-weight'])
            ix = len(meta['formdata']) / 2
            meta['formdata']['formData[%s][name]' % ix] = 'paper-weight'
            meta['formdata']['formData[%s][value]' % ix] = paper_weight_id
            meta['values']['paper-weight'] = paper_weight_id
            yield meta

    # Return request
    def get_valid_perforation_options(self, product_id, size_id):
        url = 'https://www.printed.com/order-wizard/ajax/options/get-valid-perforation-options'
        formdata = {
            'paperSizeId': size_id,
            'productId': product_id,
        }
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            formdata=formdata,
            callback=self.parse_perforation)

    @process_next_request
    def parse_perforation(self, response):
        perforation_id = response.xpath('//validOptionId/text()').extract()[0]
        meta = response.meta.copy()
        ix = len(response.meta['formdata']) / 2
        meta['formdata']['formData[%s][name]' % ix] = 'perforation'
        meta['formdata']['formData[%s][value]' % ix] = perforation_id
        meta['values']['perforation'] = perforation_id
        yield meta

    def get_formdata(self, meta):
        formdata = {
            'productId': meta['product_id'],
        }
        for k, v in meta['rules'].items():
            if k == 'formdata':
                continue
            if '{copy}' in v:
                f = v.split('{copy}')[-1]
                formdata[k] = meta['values'][f]
            else:
                formdata[k] = v
        formdata.update(meta['formdata'])

        return formdata

    # Force saving options before to continue with next request
    def force_save_options(self, product_id, meta):
        self._forms_to_process.append((self.get_formdata(meta), meta, False))
        return None

    # Return request
    def save_options(self, formdata, meta, getprice=True):
        # self.log('>> SAVE OPTIONS: %r' % formdata)
        url = 'https://www.printed.com/order-wizard/ajax/options/save-options'
        if getprice:
            meta['request_list'] = [self.get_price(meta)]  # Get price after saving form
        return FormRequest(
            url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            meta=meta,
            formdata=formdata,
            callback=self.parse_nothing,
            dont_filter=True)

    def get_price(self, meta):
        """
        GET request
        """
        url = 'https://www.printed.com/order-wizard/ajax/calculate/get-price'
        return Request(url,
                       meta=meta,
                       dont_filter=True,
                       callback=self.parse_price)

    def parse_price(self, response):
        """
        Parse price, load Product object and yield it
        """
        product_name = response.meta['product_name']
        product_url = response.meta['product_url']
        product_identifier = md5(product_name).hexdigest()
        product_price = response.xpath('//quotePrice/text()').extract()[0]
        product_category = product_name.split(' - ')[0]
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', product_url)
        loader.add_value('identifier', product_identifier)
        loader.add_value('price', product_price)
        loader.add_value('category', product_category)
        item = loader.load_item()
        if item['price'] and (('Matt' in item['name']) or ('Gloss' in item['name'])):
            item['price'] = (item['price'] * Decimal('1.2')).quantize(Decimal('0.01'))
        item['metadata'] = response.meta['metadata'].copy()
        yield item

    def _exclude_rule(self, k, m):
        if k == 'lamination-finish' and m['values']['lamination-options'] == 'none':
            return True
        return False

    def _select_and_parse_options(self, k, v, l, r, m):
        """
        Load formdata with selected option and call parse_options again
        to continue with the next rule/option.
        param::k formdata name (ie: paper-size)
        param::v value selected
        param::l label
        param::r response
        param::m meta
        """
        meta = m.copy()
        # Sometimes some options are hidden when other option is selected
        if not self._exclude_rule(k, m):
            meta['formdata'] = m['formdata'].copy()
            meta['values'] = m['values'].copy()
            meta['metadata'] = m['metadata'].copy()
            ix = len(m['formdata']) / 2  # 2 inputs for each field (name and value)
            meta['formdata']['formData[%s][name]' % ix] = k
            meta['formdata']['formData[%s][value]' % ix] = v
            meta['values'][k] = v
            l = l.strip()
            if l:
                meta['product_name'] += ' - ' + l.strip()
                # self.log('Product name: %s' % meta['product_name'])
            if k in meta['metafields']:
                self._add_item_metadata(meta, l, meta['metafields'][k])

        meta['current_rule_action_no'] += 1  # Get next action

        # self.log('Select %s: %s' % (k, l or v))
        # IMPORTANT: check how the memory consumption is affected
        for q in self.parse_options(r, meta):
            yield q

    def _add_item_metadata(self, m, l, k):
        """
        param::m response meta
        param::l label
        param::k key (field name)
        """
        if k in m['metadata']:
            m['metadata'][k] += ' - ' + l
        else:
            m['metadata'][k] = l

    def _excluded_value(self, k, v, filters):
        return (k in filters) and (v not in filters[k])

    def parse_options(self, response, new_meta=None):
        meta = response.meta if new_meta is None else new_meta
        meta['callback_list'] = list(meta['callback_list'])  # Forcing copy of requests list
        product_id = re.findall(r"pdcOrderWizard.productId = '(\d+)';", response.body)[0]
        if 'product_id' not in meta:
            meta['product_id'] = product_id
        rules = meta['rules']
        filters = meta['filters']
        formdata_rules = rules['formdata']
        values = meta.get('values', {})
        current_rule_no = meta.get('current_rule_no')
        if current_rule_no is None:
            current_rule_no = 0
            meta['current_rule_no'] = 0
        current_rule_action_no = meta.get('current_rule_action_no')
        if current_rule_action_no is None:
            current_rule_action_no = 0
            meta['current_rule_action_no'] = 0
        if current_rule_no < len(formdata_rules):
            current_rule = formdata_rules[current_rule_no]
            # self.log('[LOCAL DEBUG] -- Current rule => %r' % current_rule[1])
            if current_rule_action_no < len(current_rule[1]):
                action = current_rule[1][current_rule_action_no]
                if isinstance(action, (str, unicode)):
                    # XPath
                    option_inputs = response.xpath(action)
                    for input_xs in option_inputs:
                        try:
                            label = input_xs.xpath('@data-original-label').extract()[0]
                        except:
                            label = input_xs.xpath('following-sibling::label/text()').extract()[0]
                        value = input_xs.xpath('@value').extract()[0]

                        if self._excluded_value(current_rule[0], value, filters):
                           continue

                        for q in self._select_and_parse_options(current_rule[0], value, label,
                                                                response, meta):
                            yield q
                elif isinstance(action, list):
                    for v in map(str, action):
                        if self._excluded_value(current_rule[0], v, filters):
                            continue
                        for q in self._select_and_parse_options(current_rule[0], v, v,
                                                                response, meta):
                            yield q
                elif isinstance(action, tuple) and action[0] in ('copy', 'default'):
                    if action[0] == 'copy':
                        # Empty label to prevent duplicate options values in product name
                        v = values[action[1]]
                        for q in self._select_and_parse_options(current_rule[0], v, '',
                                                                response, meta):
                            yield q
                    else:
                        # Empty label because the default options are not visible nor selectables
                        v = action[1]
                        for q in self._select_and_parse_options(current_rule[0], v, '',
                                                                response, meta):
                            yield q
                else:
                    # It should be a tuple with a callable method in first place
                    # The following arguments will be formdata field names
                    meta['callback_list'].append(action)
                    meta['current_rule_action_no'] += 1  # Get next action
                    # Recursive call creating a new branch from this option/s selected
                    # IMPORTANT: check how the memory consumption is affected
                    for q in self.parse_options(response, meta):
                        yield q
            else:
                meta['current_rule_no'] += 1
                meta['current_rule_action_no'] = 0
                # Recursive call creating a new branch from this option/s selected
                # IMPORTANT: check how the memory consumption is affected
                for q in self.parse_options(response, meta):
                    yield q
        else:
            # self.log('[LOCAL DEBUG] -- Product name: %s' % meta['product_name'])
            # self.log('[LOCAL DEBUG] -- Requests list: %r' % meta['request_list'])
            # self.log('[LOCAL DEBUG] -- Values: %r' % meta['values'])
            # return

            # Start running first request in list
            # self.log('[LOCAL DEBUG] -- Requests list => %r' % meta['request_list'])
            # self.log('[LOCAL DEBUG] -- Doing first request')
            first_request = None
            first_callback = meta['callback_list'].pop(0) \
                if meta['callback_list'] else None
            if first_callback is not None:
                first_request = self.create_request_by_callback(product_id, meta, values,
                    first_callback[0], *first_callback[1:])
                first_request.meta['values'] = values.copy()
                first_request.meta['callback_list'] = meta['callback_list']
            yield first_request
