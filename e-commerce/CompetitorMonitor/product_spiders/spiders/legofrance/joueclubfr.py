import urllib, lxml.html, weakref
from lxml import etree

import re
from urlparse import urljoin
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.utils.python import unicode_to_str

from product_spiders.utils import extract_price_eu as extract_price

from decimal import Decimal

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.trackref import object_ref
#             --------------                     #
def _factory(response, parser_cls):
    url = response.url
    body = response.body_as_unicode().strip().encode('utf8') or '<html/>'
    parser = parser_cls(recover=True, encoding='utf8')
    return etree.fromstring(body, parser=parser, base_url=url)


class LxmlDocument(object_ref):

    cache = weakref.WeakKeyDictionary()
    __slots__ = ['__weakref__']

    def __new__(cls, response, parser=etree.HTMLParser):
        cache = cls.cache.setdefault(response, {})
        if parser not in cache:
            obj = object_ref.__new__(cls)
            cache[parser] = _factory(response, parser)
        return cache[parser]

    def __str__(self):
        return "<LxmlDocument %s>" % self.root.tag

#             --------------                     #
class FormRequest(Request):

    def __init__(self, *args, **kwargs):
        formdata = kwargs.pop('formdata', None)
        if formdata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        super(FormRequest, self).__init__(*args, **kwargs)

        if formdata:
            items = formdata.iteritems() if isinstance(formdata, dict) else formdata
            querystr = _urlencode(items, self.encoding)
            if self.method == 'POST':
                self.headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                self._set_body(querystr)
            else:
                self._set_url(self.url + ('&' if '?' in self.url else '?') + querystr)

    @classmethod
    def from_response(cls, response, formname=None, formnumber=0, formdata=None,
                      clickdata=None, dont_click=False, formxpath=None, **kwargs):
        kwargs.setdefault('encoding', response.encoding)
        form = _get_form(response, formname, formnumber, formxpath)
        formdata = _get_inputs(form, formdata, dont_click, clickdata, response)
        url = form.action or form.base_url
        method = kwargs.pop('method', form.method)
        return cls(url, method=method, formdata=formdata, **kwargs)

def _urlencode(seq, enc):
    values = [(unicode_to_str(k, enc), unicode_to_str(v, enc))
              for k, vs in seq
              for v in (vs if hasattr(vs, '__iter__') else [vs])]
    return urllib.urlencode(values, doseq=1)

def _get_form(response, formname, formnumber, formxpath):
    """Find the form element """
    #from scrapy.selector.lxmldocument import LxmlDocument
    root = LxmlDocument(response, lxml.html.HTMLParser)
    forms = root.xpath('//form')
    if not forms:
        raise ValueError("No <form> element found in %s" % response)

    if formname is not None:
        f = root.xpath('//form[@name="%s"]' % formname)
        if f:
            return f[0]

    # Get form element from xpath, if not found, go up
    if formxpath is not None:
        nodes = root.xpath(formxpath)
        if nodes:
            el = nodes[0]
            while True:
                if el.tag == 'form':
                    return el
                el = el.getparent()
                if el is None:
                    break
        raise ValueError('No <form> element found with %s' % formxpath)

    # If we get here, it means that either formname was None
    # or invalid
    if formnumber is not None:
        try:
            form = forms[formnumber]
        except IndexError:
            raise IndexError("Form number %d not found in %s" %
                                (formnumber, response))
        else:
            return form

def _get_inputs(form, formdata, dont_click, clickdata, response):
    try:
        formdata = dict(formdata or ())
    except (ValueError, TypeError):
        raise ValueError('formdata should be a dict or iterable of tuples')

    inputs = form.xpath('descendant::textarea'
                        '|descendant::select'
                        '|descendant::input[@type!="submit" and @type!="image" '
                        'and ((@type!="checkbox" and @type!="radio") or @checked)]')
    values = [(k, u'' if v is None else v) \
              for k, v in (_value(e) for e in inputs) \
              if k and k not in formdata]

    if not dont_click:
        clickable = _get_clickable(clickdata, form)
        if clickable and clickable[0] not in formdata and not clickable[0] is None:
            values.append(clickable)

    values.extend(formdata.iteritems())
    return values

def _value(ele):
    n = ele.name
    v = ele.value
    if ele.tag == 'select':
        return _select_value(ele, n, v)
    return n, v

def _select_value(ele, n, v):
    multiple = ele.multiple
    if v is None and not multiple:
        # Match browser behaviour on simple select tag without options selected
        # And for select tags wihout options
        o = ele.value_options
        return (n, o[0]) if o else (None, None)
    elif v is not None and multiple:
        # This is a workround to bug in lxml fixed 2.3.1
        # fix https://github.com/lxml/lxml/commit/57f49eed82068a20da3db8f1b18ae00c1bab8b12#L1L1139
        selected_options = ele.xpath('.//option[@selected]')
        v = [(o.get('value') or o.text or u'').strip() for o in selected_options]
    return n, v

def _get_clickable(clickdata, form):
    """
    Returns the clickable element specified in clickdata,
    if the latter is given. If not, it returns the first
    clickable element found
    """
    clickables = [el for el in form.xpath('.//input[@type="submit"]')]
    if not clickables:
        return

    # If we don't have clickdata, we just use the first clickable element
    if clickdata is None:
        el = clickables[0]
        return (el.name, el.value)

    # If clickdata is given, we compare it to the clickable elements to find a
    # match. We first look to see if the number is specified in clickdata,
    # because that uniquely identifies the element
    nr = clickdata.get('nr', None)
    if nr is not None:
        try:
            el = list(form.inputs)[nr]
        except IndexError:
            pass
        else:
            return (el.name, el.value)

    # We didn't find it, so now we build an XPath expression out of the other
    # arguments, because they can be used as such
    xpath = u'.//*' + \
            u''.join(u'[@%s="%s"]' % c for c in clickdata.iteritems())
    el = form.xpath(xpath)
    if len(el) == 1:
        return (el[0].name, el[0].value)
    elif len(el) > 1:
        raise ValueError("Multiple elements found (%r) matching the criteria "
                         "in clickdata: %r" % (el, clickdata))
    else:
        raise ValueError('No clickable element matching clickdata: %r' % (clickdata,))

#             --------------                     #

def extract_id(name,identifier):
    chunks = name.split()
    sku = ''
    for i in chunks:
        if len(i)>3 and len(i)<6:
            try:
                sku = int(i)
                break
            except: continue
        else: continue
    if sku == '':
        chunks = name.split('-')
        for i in chunks:
            if len(i)>3 and len(i)<6:
                try:
                    sku = int(i)
                    break
                except: continue
            else: continue
    if sku<0: sku = int(str(sku).strip('-'))
    if sku != '':
        identifier = sku
    return identifier,sku

def price_processor(k):
    return str(k.split()[0]).replace(',','.')

def stock_flag(n):
    if n == 'EN STOCK': return 1
    else: return 0

def process(hxs, response):
    base_url = get_base_url(response)
    re_sku = re.compile('(\d\d\d\d\d?)')

    for product in hxs.select('//div[@class="liste-page-produit"]'):
        loader = ProductLoader(item=Product(), response=response)
        identifier = product.select('a/div[@class="liste-page-reference-produit"]/text()').re(' produit : (.*)')[0]
        loader.add_value("identifier", identifier)

        name = product.select('a/h2/text()').extract()[0]
        loader.add_value("name", name)

        sku = re_sku.findall(name)
        loader.add_value("sku", sku)

        url = product.select('a/@href').extract()[0]
        loader.add_value("url", urljoin_rfc(base_url, url))

        price = extract_price(product.select('a/div[@class="liste-page-price"]/text()').extract()[0])
        loader.add_value("price", price)
        image_url = product.select('a/img/@src').extract()

        loader.add_value("image_url", urljoin_rfc(base_url, image_url[0]))
        stock = product.select('a/div[@class="liste-page-stock-produit" and text()="En stock"]').extract()
        if not stock:
            loader.add_value("stock", 0)

        yield loader.load_item()
    return

class JoueclubSpider(BaseSpider):
    name = 'legofrance-joueclub.fr'
    start_urls = ['http://www.joueclub.fr/marque/lego.aspx']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div//div[@class="liste-page-produit"]/a/@href').extract()
        for category in categories:
            url = urljoin(base_url, category)
            yield Request(url=url, callback=self.extract_first_page_data)

    def parse_sub(self, response):
        base_url = get_base_url(response)
        log.msg("This is a warning from subdir processing", level=log.DEBUG)
        hxs = HtmlXPathSelector(response)
        # extracting sub_category links:
        categories = hxs.select('//div[@class="galerie_images"]/a/@href').extract()
        # lets iterate every sub_category:
        for i in categories:
            abs_url = urljoin_rfc(base_url, i)
            req = Request(url=abs_url, callback=self.extract_first_page_data)
            yield req

    def extract_first_page_data(self, response):
        hxs = HtmlXPathSelector(response)
        # firstly ensure in product existence on the page:
        sub_categories = hxs.select('//div[@class="galerie_images"]/a/@href').extract()
        if len(sub_categories) != 0: # there are subcategories at this page
            log.msg("This is a warning about subcategories", level=log.DEBUG)
            message = "URL = %s" % response.url
            log.msg(message, level=log.DEBUG)
            req = FormRequest.from_response(response, callback=self.parse_sub)
            return req
        else:
            # secondary check up the pagination:
            if hxs.select('//div[@class="liste-pagination"]//a[contains(text(), ">")]/@href').extract():
                # pagination exists and set up 100 products per page request:
                form_keys = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
                formdata = dict()
                for k in form_keys:
                    formdata[k] = hxs.select('//input[@name="{}"]/@value'.format(k))[0].extract()
                formdata.update({'__EVENTTARGET': 'ctl00$MainContent$ddlNbpages','ctl00$MainContent$ddlNbpages':'108'})
                req = FormRequest(response.url, formdata=formdata, callback=self.extract_all_page_data)
                log.msg("This is a warning 1", level=log.DEBUG)
                return req
            else:
                log.msg("This is a warning 2", level=log.DEBUG)
                # it is one page product list
                return process(hxs, response)

    def extract_all_page_data(self, response):
        hxs = HtmlXPathSelector(response)
        return process(hxs, response)

