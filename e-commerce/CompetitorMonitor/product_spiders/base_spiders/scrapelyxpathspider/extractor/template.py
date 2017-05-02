# -*- coding: utf-8 -*-
import json

from scrapely.htmlpage import HtmlTag, HtmlTagType
from scrapely.template import TemplateMaker, FragmentNotFound, FragmentAlreadyAnnotated


class TemplateMakerWithAttrs(TemplateMaker):
    def annotate(self, field, score_func, best_match=True, attr=None):
        if attr is None:
            return super(TemplateMakerWithAttrs, self).annotate(field, score_func, best_match)

        indexes = self.select(score_func)
        if not indexes:
            raise FragmentNotFound("Fragment not found annotating %r using: %s" %
                                   (field, score_func))
        if best_match:
            del indexes[1:]
        for i in indexes:
            self.annotate_fragment(i, field, attr)

    def annotate_fragment(self, index, field, attr=None, required=True):
        if attr is None:
            return super(TemplateMakerWithAttrs, self).annotate_fragment(index, field)

        for f in self.htmlpage.parsed_body[index::-1]:
            if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.OPEN_TAG:
                if 'data-scrapy-annotate' in f.attributes:
                    fstr = self.htmlpage.fragment_data(f)
                    raise FragmentAlreadyAnnotated("Fragment already annotated: %s" % fstr)
                if attr is None or attr == 'text' or attr == 'content':
                    d = {'annotations': {'content': field}}
                else:
                    d = {'annotations': {attr: field}}
                if required:
                    d['required'] = [field]
                a = ' data-scrapy-annotate="%s"' % json.dumps(d).replace('"', '&quot;')
                p = self.htmlpage
                p.body = p.body[:f.end-1] + a + p.body[f.end-1:]
                break


class TemplateMakerRepeated(TemplateMaker):
    def __init__(self, htmlpage):
        super(TemplateMakerRepeated, self).__init__(htmlpage)
        self.variant_counter = 1

    def annotate(self, field, score_func, best_match=True):
        return super(TemplateMakerRepeated, self).annotate(field, score_func, best_match)
