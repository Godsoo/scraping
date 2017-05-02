from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from pyramid.security import (
    Authenticated,
    has_permission,
)

from productspidersweb.models import (
    DBSession,
    Account,
    Spider,
    SpiderSpec,

    ERROR_TYPES,
)

ERROR_TYPES_DICT = dict(ERROR_TYPES)

from spider_doc import get_spider_doc_pyramid, parse_spec_desc_from_assembla_from_assembla
from spider_ratings import calculate_spider_rating

import assembla


@view_config(route_name='show_doc', renderer='spider_doc.mako', permission=Authenticated)
def show_doc(request):
    back_url = request.session.pop_flash(queue='spider_doc_back_url')
    if back_url:
        back_url = back_url[0]
    elif request.referrer != request.url and not request.GET.get('ignore_referrer', False):
        back_url = request.referrer
    else:
        back_url = None

    account_name = request.matchdict['account']
    spider_name = request.matchdict['spider']
    db_session = DBSession()
    account = db_session.query(Account).filter(Account.name == account_name).first()
    spider = db_session.query(Spider).filter(Spider.name == spider_name).filter(Spider.account_id == account.id).first()
    spec_active = False

    if request.method == 'POST':
        spec_active = True
        spider_spec = db_session.query(SpiderSpec).get(spider.id)
        if not spider_spec:
            spider_spec = SpiderSpec()
            spider_spec.spider_id = spider.id

        spider_spec.data = dict(request.POST.items())
        db_session.add(spider_spec)

    spider_spec = db_session.query(SpiderSpec).get(spider.id)
    if spider_spec:
        spec_data = spider_spec.data
    else:
        spec_data = {}

    spec_from_assembla = request.session.pop_flash(queue='assembla_ticket_spec_data')
    if spec_from_assembla:
        spec_active = True
        spec_from_assembla = spec_from_assembla[0]
        if spec_from_assembla:
            spec_data.update(spec_from_assembla)

    spec_errors = request.session.pop_flash(queue='assembla_ticket_spec_error')
    if spec_errors:
        spec_active = True

    refresh_cache = request.GET.get('refresh_cache')
    if refresh_cache:
        get_spider_doc_pyramid(spider, account, request.registry.settings, db_session, refresh_cache=True)
        return HTTPFound(request.route_url('show_doc', account=account_name, spider=spider_name))
    spider_doc = get_spider_doc_pyramid(spider, account, request.registry.settings, db_session)

    if 'assembla' in request.session\
       and 'authorized' in request.session['assembla']\
       and request.session['assembla']['authorized']:
        assembla_authorized = True
    else:
        assembla_authorized = False

    res = {
        'spider': spider,
        'spider_rating': calculate_spider_rating(db_session, spider),
        'edit_spider_rating': request.route_url('edit_rating', account=account_name, spider=spider_name),
        'refresh_cache_url': request.route_url('show_doc', account=account_name, spider=spider_name,
                                               _query={'refresh_cache': 'true'}),
        'back_url': back_url,
        'can_edit_spec': has_permission('administration', None, request),
        'assembla_authorized': assembla_authorized,
        'spec_active': spec_active,

        'spec': spec_data,

        'spec_errors': spec_errors,
    }
    res.update(spider_doc)

    return res


@view_config(route_name='assembla_load_spec_from_ticket', permission='administration')
def assembla_load_spec_from_ticket(request):
    assembla_ticket_num = request.POST.get('ticket_num')
    if not assembla_ticket_num:
        request.session.flash('Empty ticket number', queue='assembla_ticket_spec_error')
        raise HTTPFound(request.referrer)

    assembla_ticket = assembla.get_ticket_by_num(request, assembla_ticket_num)
    if not assembla_ticket:
        request.session.flash('Error loading ticket data for ticket #%s' % assembla_ticket_num, 
                              queue='assembla_ticket_spec_error')
        raise HTTPFound(request.referrer)

    try:
        spec = parse_spec_desc_from_assembla_from_assembla(assembla_ticket['description'])
        if spec:
            request.session.flash(spec, queue='assembla_ticket_spec_data')
        else:
            request.session.flash("Can't parse spec from ticket {}".format(assembla_ticket_num),
                                  queue='assembla_ticket_spec_error')
    except assembla.AssemblaNotAuthorized:
        pass

    # set proper back_url for spider_doc page
    back_url = request.POST.get('back_url')
    if back_url:
        request.session.flash(back_url, queue='spider_doc_back_url')

    return HTTPFound(request.referrer)