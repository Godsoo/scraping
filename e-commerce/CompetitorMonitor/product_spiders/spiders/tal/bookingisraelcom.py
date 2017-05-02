# -*- coding: utf-8 -*-
import time
import datetime
import os
import urllib2
import re
import json

from scrapy.spider import BaseSpider

from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy.http import Request
from product_spiders.items import Product, ProductLoader

import logging


import urllib
import lxml.html
import weakref
from lxml import etree

from scrapy.utils.python import unicode_to_str
from scrapy.utils.trackref import object_ref

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

def date_plus_1_month(date_obj):
    month = date_obj.month
    year = date_obj.year
    if month == 12:
        new_year = year + 1
        new_month = 1
    else:
        new_year = year
        new_month = month + 1

    day = date_obj.day

    future = None
    while not future:
        try:
            future = datetime.date(new_year, new_month, day)
        except ValueError:
            day -= 1

    return future

allowed_cities = [
    "JRS",
    "TLV",
    "DEAD",
    "ETH",
    "HFA",
    "TIBE",
    "GAL16",
    "ARAD",
    "ASHQ",
    "BEV",
    "NAHA",
    "BETL",
    "NAZE",
    "HERZ",
    "ACRE",
    "BATY",
    "NETA",
    "SAFE",
    "CAES",
    "UPPE",
    "MIZP",
    ]

nights = 3

url = 'http://www.bookingisrael.com'
search_url = 'http://www.bookingisrael.com/Search/'
ajax_url = "http://www.bookingisrael.com/JsonHotels.ashx?q=gethotels_async&searchtoken=%%searchtoken%%&offset=%%offset%%&sequence=%%sequence%%&&timestamp=%%timestamp%%"
hotel_url = "http://www.bookingisrael.com/Default.aspx?pg=HotelPreBooking&hotelID=%%hotel_id%%&hotel=%%hotel_name%%&hotelCode=%%hotel_code%%"
user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0'
request_body_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "request_body")

day_format = "%d"
year_month_format = "%Y-%m"

currency = 'USD'


class BookingComSpider(BaseSpider):
    name = "bookingisrael.com"
    allowed_domains = ["bookingisrael.com"]
    start_urls = (
        'http://www.bookingisrael.com/',
        )

    headers = {
        'User-agent': user_agent
    }
    form_headers = {
        'User-agent': user_agent,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-MicrosoftAjax': 'Delta=true',
        'X-Requested-With': 'XMLHttpRequest'
    }
    formdata = {}

    max_repeat = 50

    def get_view_state(self, hxs):
        view_state = hxs.select("//input[@id='__VIEWSTATE']/@value").extract()
        if view_state:
            return view_state[0]
        else:
            return None

    def parse(self, response):
        headers = {'User-agent': user_agent}

        self.searchtoken_reg = re.compile(r"JsonHotels.ashx\',\'(\w+)\',")
        self.hotels_reg = re.compile(r"Hotels:(\[.*\])\}\)$", re.DOTALL)

        # opening main page for cookies
        yield Request(url, dont_filter=True, headers=headers, callback=self.collect_cookies, meta={'dont_merge_cookies': True})

    def collect_cookies(self, response):
        self.main_page_response = response

        # calculate calendar values
        check_in_date = date_plus_1_month(datetime.date.today())
        check_out_date = check_in_date + datetime.timedelta(days=nights)

        formdata = {}
        formdata['ctl05$ctl07$Calendar1$dateCheckIn'] = check_in_date.strftime("%d.%m.%Y")
        formdata['ctl05$ctl07$Calendar1$dateCheckOut'] = check_out_date.strftime("%d.%m.%Y")
        formdata['ctl05$ctl07$Calendar1$hiddenfieldCheckIn'] = check_in_date.strftime("%d.%m.%Y")
        formdata['ctl05$ctl07$Calendar1$hiddenfieldCheckOut'] = check_out_date.strftime("%d.%m.%Y")
        formdata['ctl05$ctl07$Calendar1$hiddenfieldNights'] = str(nights)
        formdata['ctl05$ctl07$Calendar1$nightsDDL'] = str(nights)
        formdata['__ASYNCPOST'] = 'true'
        formdata['__EVENTTARGET'] = 'ctl05$ctl07$btnSearch'
        formdata['scriptMgr'] = 'ctl05$ctl05|ctl05$ctl07$btnSearch'

        self.formdata = formdata

        self.cities = allowed_cities[:]

        yield self.get_city_request()

    def get_city_request(self):
        try:
            city = self.cities.pop()
        except IndexError:
            return None

        cur_formdata = self.formdata.copy()
        cur_formdata['ctl05$ctl07$m_city1'] = city
        # sending search request. results will be downloaded after next request
        logging.error("Searching city: %s" % city)
        request = FormRequest.from_response(
            response=self.main_page_response,
            formname="frm",
            formdata=cur_formdata,
            dont_filter=True,
            headers=self.form_headers,
            callback=self.redirect_search
        )
        return request

    def redirect_search(self, response):
        """
        Parses body of page with results
        """
        search_url = response.body.split("|")[7]
        search_url = urllib2.unquote(search_url)

        search_url = urljoin_rfc(get_base_url(response), search_url)

        request = Request(
            url=search_url,
            dont_filter=True,
            headers=self.headers,
            callback=self.parse_search
        )
        yield request

    def parse_search(self, response):
        time.sleep(0.5)
        m = re.search(self.searchtoken_reg, response.body)
        if m:
            searchtoken = m.group(1)
            timestamp = str(int(time.time() * 1000))
            offset = 0
            sequence = 1
            url = ajax_url.replace("%%searchtoken%%", searchtoken).replace("%%timestamp%%", timestamp)\
                .replace("%%offset%%", str(offset)).replace("%%sequence%%", str(sequence))
            request = Request(
                url=url,
                callback=self.parse_hotels_list,
                dont_filter=True,
                meta={'offset': offset, 'sequence': sequence, 'searchtoken': searchtoken}
            )
            self.last_request = request
            self.counter = 0
            yield request

    def parse_hotels_list(self, response):
        m = re.search(self.hotels_reg, response.body)
        if not m:
            logging.error(response.body)
            logging.error("ERROR!!! No hotels")
            logging.error(self.last_request)
            logging.error(self.counter)
            if self.counter < self.max_repeat:
                self.counter += 1
                yield self.last_request
            else:
                yield self.get_city_request()
            return

        hotels = json.loads(m.group(1))
        if not hotels:
            logging.error(response.body)
            logging.error("ERROR!!! No hotels 2")
            logging.error(self.last_request)
            logging.error(self.counter)
            if self.counter < self.max_repeat:
                self.counter += 1
                yield self.last_request
            else:
                yield self.get_city_request()
            return

        hotel_count = len(hotels)
        for hotel in hotels:
            name = hotel['Item']['Name']
            url = hotel_url.\
                replace("%%hotel_id%%", urllib2.quote(hotel['Item']['SuppInCode'])).\
                replace("%%hotel_name%%", urllib2.quote(hotel['Item']['Name'])).\
                replace("%%hotel_code%%", urllib2.quote(hotel['Item']['Code']))

            price = None
            for room in hotel['RoomClasses']:
                local_price = room['Price']['USD']
                if price is None or local_price < price:
                    price = local_price

            l = ProductLoader(item=Product(), response=response)
            l.add_value('name', name.encode('ascii', 'replace'))
            l.add_value('identifier', name.encode('ascii', 'replace'))
            l.add_value('url', url)
            l.add_value('price', price)
            yield l.load_item()

        offset = response.meta['offset']
        sequence = response.meta['sequence']

        if sequence < 3:
            sequence += 1
            offset += hotel_count
            timestamp = str(int(time.time() * 1000))
            searchtoken = response.meta['searchtoken']
            url = ajax_url.replace("%%searchtoken%%", searchtoken).replace("%%timestamp%%", timestamp)\
                .replace("%%offset%%", str(offset)).replace("%%sequence%%", str(sequence))
            request = Request(
                url=url,
                callback=self.parse_hotels_list,
                dont_filter=True,
                meta={'offset': offset, 'sequence': sequence, 'searchtoken': searchtoken}
            )
            self.last_request = request
            self.counter = 0
            yield request
        else:
            yield self.get_city_request()
