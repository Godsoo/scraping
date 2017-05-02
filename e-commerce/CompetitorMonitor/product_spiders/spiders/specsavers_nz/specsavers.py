# -*- coding: utf-8 -*-
import os
from product_spiders.spiders.specsavers_au.specsavers import SpecSavers


HERE = os.path.abspath(os.path.dirname(__file__))

class SpecSaversNZ(SpecSavers):
    name = 'specsavers_nz-specsavers.co.nz'
    allowed_domains = ['specsavers.co.nz']

    filename = os.path.join(HERE, 'specsavers.csv')
    start_urls = ('file://' + filename,)

    url_field = 'NZ'
