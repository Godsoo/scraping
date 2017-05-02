# -*- coding: utf-8 -*-
from swisscom import SwisscomSpider


class SwisscomMBudgetSpider(SwisscomSpider):
    name = 'orange_swisscom.ch_mbudget'
    # account specific fields
    operator = 'M-Budget Mobile'
    channel = 'Direct'

    def _check_plan_is_correct(self, plan_name, response):
        if 'M-Budget'.lower() in plan_name.lower():
            self.log("Found M-Budget plan for device: %s" % response.meta['product']['device_name'])
            return True
        else:
            return False