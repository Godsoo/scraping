# -*- coding: utf-8 -*-
from get_amazon_traffic_usage import get_amazon_traffic_usage
from send_domain_weekly_traffic_usage_report import send_report

EMAILS = [
    'yuri.abzyanov@intelligenteye.com',
    # 'james.mishreki@intelligenteye.com',
    # 'toni.fleck@intelligenteye.com',
    # 'emiliano.rudenick@intelligenteye.com',
    # 'steven.seaward@intelligenteye.com'
]

SPIDER_TRAFFIC_DISPLAY_THRESHOLD = 2 * 1024 * 1024 * 1024  # 2 GB


if __name__ == '__main__':
    res = get_amazon_traffic_usage('1w')
    send_report(res, 'amazon', 'last 7 days', SPIDER_TRAFFIC_DISPLAY_THRESHOLD, EMAILS)
