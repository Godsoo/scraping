# -*- coding: utf-8 -*-
from get_amazon_traffic_usage import get_amazon_traffic_usage
from send_domain_weekly_traffic_usage_report import send_report

EMAILS = [
    'yuri.abzyanov@competitormonitor.com',
    # 'james.mishreki@competitormonitor.com',
    # 'toni.fleck@competitormonitor.com',
    # 'emiliano.rudenick@competitormonitor.com',
    # 'steven.seaward@competitormonitor.com',
    # 'adrian.teasdale@competitormonitor.com',
]

SPIDER_TRAFFIC_DISPLAY_THRESHOLD = 8 * 1024 * 1024 * 1024  # 5 GB


if __name__ == '__main__':
    res = get_amazon_traffic_usage('1m')
    send_report(res, 'amazon', 'last month', SPIDER_TRAFFIC_DISPLAY_THRESHOLD, EMAILS)
