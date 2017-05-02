# -*- coding: utf-8 -*-
import sys

from get_domain_traffic_usage import get_traffic_usage

sys.path.append('..')
from emailnotifier import EmailNotifier
import config


def send_report(res, spiders_str, period_str, display_traffic_threshold, emails, display_domains_below_threshold=False):
    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)

    header = 'Report on %s traffic for %s' % (spiders_str, period_str)

    body = "Hello\n\nThis is automatic report of %s traffic usage by spiders, generated for %s.\n" % (spiders_str,
                                                                                                      period_str)

    total_traffic = sum([data['traffic'] for data in res.values()])
    body += "Total traffic: %0.2f GB\n" % (total_traffic / 1024 / 1024 / 1024, )

    if res:
        domains = set([data['domain'] for data in res.values()])
        domains_traffic = {domain: sum([data['traffic'] for data in res.values() if data['domain'] == domain])
                           for domain in domains}
        sorted_domains = sorted(domains_traffic, key=lambda x: domains_traffic[x], reverse=True)
        for domain in sorted_domains:
            res_domain = {spider: data for spider, data in res.items() if data['domain'] == domain}
            sorted_spiders = sorted(res_domain, key=lambda x: res_domain[x]['traffic'], reverse=True)
            total_traffic = sum([data['traffic'] for data in res_domain.values()])
            above_threshold = total_traffic > display_traffic_threshold
            display_spider_traffic_threshold = display_traffic_threshold / 2
            spider_above_threshold = res_domain[sorted_spiders[0]]['traffic'] > display_spider_traffic_threshold

            if above_threshold or display_domains_below_threshold:
                body += "\n\n"
                body += "Domain: %s\n" % domain

                body += "Total traffic: %0.2f GB\n" % (total_traffic / 1024 / 1024 / 1024, )

            if spider_above_threshold:
                for i, spider in enumerate(sorted_spiders, 1):
                    data = res_domain[spider]
                    if data['traffic'] < display_traffic_threshold:
                        break
                    body += "%d. %s: %0.2f GB\n" % (i, spider, data['traffic'] / 1024 / 1024 / 1024)
    else:
        body += "No traffic"

    body += "\n\n"
    body += "Best regards"

    notifier.send_notification(emails,
                               header,
                               body)


EMAILS = [
    # 'yuri.abzyanov@intelligenteye.com',
    # 'james.mishreki@intelligenteye.com',
    # 'toni.fleck@intelligenteye.com',
    # 'emiliano.rudenick@intelligenteye.com',
    # 'steven.seaward@intelligenteye.com'
]

SPIDER_TRAFFIC_DISPLAY_THRESHOLD = 5 * 1024 * 1024 * 1024  # 5 GB


if __name__ == '__main__':
    res = get_traffic_usage('1w')
    send_report(res, 'all domains', 'last 7 days', SPIDER_TRAFFIC_DISPLAY_THRESHOLD, EMAILS)