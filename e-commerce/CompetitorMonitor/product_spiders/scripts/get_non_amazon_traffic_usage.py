# -*- coding: utf-8 -*-
from argparse import ArgumentParser, FileType

from get_domain_traffic_usage import check_period, get_traffic_usage, print_results
from get_amazon_traffic_usage import is_amazon_domain


def get_non_amazon_traffic_usage(period, verbose=False):
    return get_traffic_usage(period, verbose, domain_filter_fns=[lambda domain: not is_amazon_domain(domain)])


if __name__ == '__main__':
    parser = ArgumentParser(description='Collects statistics of traffic usage by non-amazon spiders split by spider')
    parser.add_argument('--period', dest='period', type=str, default='1d')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--output-file', dest='output_file', type=FileType('w+'), default=None)

    args = parser.parse_args()
    if not check_period(args.period):
        print "ERROR: unknown period format: %s. Please specify format in a way: <number><d|w|m>" % args.period
        exit(1)

    res = get_non_amazon_traffic_usage(args.period, args.verbose)

    print_results(res, args)
