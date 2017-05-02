# -*- coding: utf-8 -*-
import re
import sys
import os.path
import datetime as dt

from productspidersweb.utils import (
    get_spider_source_file,
    get_spider_module
)

from productspidersweb.models import SpiderDoc

HERE = os.path.dirname(__file__)
path = os.path.abspath(os.path.join(HERE, '../..'))

sys.path.append(path)
path = os.path.join(path, 'product_spiders')

sys.path.append(path)

from product_spiders.hgread import (get_commits_for_file, load_root_active_changeset_data,
                                    save_root_active_changeset_data)

_ticket_url_reg = '(https?://(?:www.)?assembla\.com.*tickets/(\d+).*)'

_ticket_regs = [
    re.compile(r'Original ticket: *%s' % _ticket_url_reg),
    re.compile(r'Ticket link: *%s' % _ticket_url_reg),
    re.compile(r'Ticket reference: *%s' % _ticket_url_reg),
]

_ticket_num_regs = [
    re.compile(r'Original assembla ticket\s*#?\:\s*(\d+)')
]

_assembla_ticket_url_template = 'https://www.assembla.com/spaces/competitormonitor/tickets/{ticket_num:d}'


def _build_assembla_ticket_url(ticket_num):
    return _assembla_ticket_url_template.format(ticket_num=ticket_num)


def _get_ticket_url(line):
    for reg in _ticket_regs:
        m = reg.search(line)
        if m:
            ticket_url, ticket_num = m.groups()
            return int(ticket_num), ticket_url.strip()

    # try extracting ticket number and building URL using it
    for reg in _ticket_num_regs:
        m = reg.search(line)
        if m:
            ticket_num = int(m.group(1))
            return ticket_num, _build_assembla_ticket_url(ticket_num)

    return None, None


def parse_spider_top_comment(module_doc):
    res_lines = []
    ticket_num = None
    ticket_url = None

    for line in module_doc.decode('utf-8').splitlines():
        line = line.strip()
        new_ticket_num, new_ticket_url = _get_ticket_url(line)
        if not new_ticket_url:
            res_lines.append(line)
        else:
            assert ticket_url is None, "Two ticket urls found in doc:\n%s" % module_doc
            ticket_url = new_ticket_url
            ticket_num = new_ticket_num
    return ticket_num, ticket_url, res_lines


HG_EXEC = '/usr/bin/hg'


def get_spider_doc_pyramid(spider, account, settings, db_session, refresh_cache=False):
    hg_exec = settings.get('hg_exec', None) or HG_EXEC
    return get_spider_doc(spider, account, hg_exec, db_session, refresh_cache)


def get_spider_doc(spider, account, hg_exec, db_session, refresh_cache=False):
    root_changeset = load_root_active_changeset_data()
    if not root_changeset:
        root_changeset = save_root_active_changeset_data(hg_exec)

    # load cache from db
    cache = db_session.query(SpiderDoc).get(spider.id)
    if not refresh_cache:
        if cache and cache.latest_changeset == root_changeset['changeset'] and cache.branch == root_changeset['branch']:
            return cache.data

    filepath = get_spider_source_file(account.name, spider.name)
    commits = get_commits_for_file(filepath, hg_exec)

    module = get_spider_module(account.name, spider.name)
    if module.__doc__ is not None:
        ticket_num, ticket_url, top_comment_lines = parse_spider_top_comment(module.__doc__)
    else:
        ticket_num = ticket_url = top_comment_lines = None

    if commits:
        created_by = commits[-1]['user']
        last_commit_by = commits[0]['user']
    else:
        created_by = None
        last_commit_by = None

    res = {
        'ticket_url': ticket_url,
        'ticket_num': ticket_num,
        'top_comment_lines': top_comment_lines,
        'created_by': created_by,
        'last_commit_by': last_commit_by,
        'commits': commits
    }
    # save cache only if spider is checked in to repo
    latest_changeset = commits[0]['changeset'] if commits else None
    if latest_changeset:
        if not cache:
            cache = SpiderDoc()
            cache.spider_id = spider.id
        cache.latest_changeset = root_changeset['changeset']
        cache.branch = root_changeset['branch']
        cache.data = res
        db_session.add(cache)

    return res


# Regex to parse spider specification from Assembla ticket description for this spider
assembla_ticket_desc_reg = re.compile(r"""
.*  # skipping header of description

\*?Specification\*?\s*  # start of specification

\*?Client:?\*?\s*
(?P<client>[^*].*)\s*

\*?Date:?\*?\s*
(?P<date>[^*].*)\s*

\*?Site\ Name:?\*?\s*
(?P<site_name>[^*].*)\s*

\*?Monitor\ all\ products\ on\ site\?\*?\s
(?P<all_products>[^*].*)

\*?Price:?\*?\s*
(?P<price>[^*].*)

\*?Currency:?\*?\s*
(?P<currency>[^*].*)

\*?Stock:?\*?\s*
(?P<stock>[^*].*)

\*?Categories:?\*?\s*
(?P<cat>[^*].*)

\*?Brands:?\*?\s*
(?P<brand>[^*].*)

\*?Shipping:?\?\*?
(?P<shipping>[^*].*)

\*?Product\ codes:?\*?
(?P<sku>[^*].*)""", re.MULTILINE + re.VERBOSE + re.DOTALL)


def parse_spec_desc_from_assembla_from_assembla(ticket_desc):
    m = assembla_ticket_desc_reg.search(ticket_desc)
    if not m:
        return None
    res = m.groupdict()

    for k in res:
        res[k] = res[k].strip("* \n")

    # parse date
    try:
        res['date'] = dt.datetime.strptime(res['date'], "%d/%m/%Y").date()
    except ValueError:
        pass

    # filter out ending
    endings = [
        'please see the spider code convention',
        'any questions',
        'thanks'
    ]
    for s in endings:
        try:
            idx = res['sku'].lower().index(s)
        except ValueError:
            pass
        else:
            res['sku'] = res['sku'][:idx].strip()

    return res
