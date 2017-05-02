# -*- coding: utf-8 -*-
from get_domain_traffic_usage import get_traffic_usage
from send_domain_weekly_traffic_usage_report import send_report

EMAILS = [
    'yuri.abzyanov@competitormonitor.com',
    'lucas.moauro@intelligenteye.com',
    'toni.fleck@competitormonitor.com',
    'steven.seaward@competitormonitor.com',
    'stephen.sharp@intelligenteye.com',
    'adrian.teasdale@competitormonitor.com',
]

SPIDER_TRAFFIC_DISPLAY_THRESHOLD = 20 * 1024 * 1024 * 1024  # 20 GB


if __name__ == '__main__':
    res = get_traffic_usage('1m')
    send_report(res, 'all domain', 'last month', SPIDER_TRAFFIC_DISPLAY_THRESHOLD, EMAILS)
