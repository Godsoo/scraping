# -*- coding: utf-8 -*-
from lxml import etree
from lxml.html import tostring

from scrapely import Scraper
from scrapely.htmlpage import HtmlTag, HtmlTagType
from scrapely.extraction import InstanceBasedLearningExtractor
from scrapely.descriptor import FieldDescriptor, ItemDescriptor
from scrapely.extractors import image_url

from template import TemplateMakerWithAttrs
from value_extractors import get_extractor_function


class MyItemDescriptor(ItemDescriptor):
    def __init__(self, fields=None):
        attributes = []
        if not fields:
            fields = ['name', 'price', 'sku', 'brand', 'category']
        for x in fields:
            attributes.append(FieldDescriptor(x, x))

        attributes.append(FieldDescriptor('image', 'image', extractor=image_url))
        super(MyItemDescriptor, self).__init__('myitem', 'testing description', attributes)


def get_visual_tool_item_descriptor(fields_spec):
    field_descriptors = []
    for field_name, spec in fields_spec.items():
        required = spec['required']
        extractor_name = spec['extractor']
        extractor_func = get_extractor_function(extractor_name)
        field_descriptors.append(FieldDescriptor(field_name, field_name, extractor_func, required))

    return ItemDescriptor("", "", field_descriptors)


def has_xpath_annotation(fragment, field):
    if isinstance(fragment, HtmlTag) and fragment.tag_type == HtmlTagType.OPEN_TAG:
        if 'xpath_annotation' in fragment.attributes:
            if fragment.attributes['xpath_annotation'] == field:
                return True
            else:
                return False
    return False


def best_match_xpath_annotation(field):
    """
    disregards value, but instead searches for 'xpath_annotation' html attr
    """
    def func(fragment, page):
        res = has_xpath_annotation(fragment, field)
        if res:
            return 1.0
        else:
            return 0.0
    return func


def prepare_html(html, data):
    """
    adds 'xpath_annotation' attribute to elements which contain data
    search for elements using xpath
    """
    htmlparser = etree.HTMLParser()
    tree = etree.fromstring(html, htmlparser)

    for field, xpathes in data.items():
        if not hasattr(xpathes, '__iter__'):
            xpathes = [xpathes]
        for xpath in xpathes:
            if xpath:
                try:
                    res = tree.xpath(xpath)
                except etree.XPathEvalError:
                    continue
                if res:
                    for r in res:
                        r.attrib['xpath_annotation'] = field

    return tostring(tree, encoding='unicode')


def filter_annotation_from_template(template, annotation='xpath_annotation'):
    """
    remove 'xpath_annotation' html attributes
    """
    for i, f in enumerate(template.parsed_body):
        if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.OPEN_TAG:
            if annotation in f.attributes:
                value = f.attributes[annotation]
                el = template.body[f.start:f.end]
                if not annotation in el:
                    continue
                start = el.index(annotation)
                end = start + len(annotation) + len('"%s"' % value) + 1
                el = el[:start] + el[end+1:]
                p = template.body
                template.body = p[:f.start] + el + p[f.end:]
    return template


class ScraperXPath(Scraper):
    """
    This extractor considers 'xpath_annotations' when training
    """

    default_data_attrs = {}

    def _train_implementation(self, htmlpage, data, data_attrs=None, repeated=False):
        assert data, "Cannot train with empty data"
        if not repeated:
            best_match = True
        else:
            best_match = False
        if data_attrs is None:
            data_attrs = self.default_data_attrs
        # assume that `data` has xpathes for each field and annotate it with
        # 'xpath_annotation' html attributes
        htmlpage.body = prepare_html(htmlpage.body, data)
        # train using xpath annotations
        tm = TemplateMakerWithAttrs(htmlpage)
        for field, values in data.items():
            if not hasattr(values, '__iter__'):
                values = [values]
            if field in data_attrs:
                attr = data_attrs[field]
            else:
                attr = None
            if len(list(values)) > 0:
                tm.annotate(field, best_match_xpath_annotation(field), attr=attr, best_match=best_match)
        template = tm.get_template()
        # remove xpath annotations from resulting html page,
        # cause they will interfere with IBL Extractor
        template = filter_annotation_from_template(template)
        self.add_template(template)

    def train_from_htmlpage(self, htmlpage, data, data_attrs=None):
        self._train_implementation(htmlpage, data, data_attrs, repeated=False)

    def train_from_htmlpage_repeated(self, htmlpage, data, data_attrs=None):
        self._train_implementation(htmlpage, data, data_attrs, repeated=True)

    def scrape_page2(self, page, fields_spec):
        if self._ex is None:
            self._ex = InstanceBasedLearningExtractor(((t, get_visual_tool_item_descriptor(fields_spec))
                                                       for t in self._templates), False, True)
        res = self._ex.extract(page)[0]
        return res
