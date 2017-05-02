import json
import datetime
import os.path

import requests

import logging

log = logging.getLogger("assembla")

LOGIN_URL_TEMPLATE = "https://api.assembla.com/authorization?client_id=%(client_id)s&response_type=code"
AUTHORIZATION_URL = "https://api.assembla.com/token?grant_type=authorization_code&code=%(authorization_code)s"

USERS_URL = 'https://api.assembla.com/v1/users'
SPACE_USERS_URL = 'https://api.assembla.com/v1/spaces/%(space)s/users.json'

TICKETS_URL = 'https://api.assembla.com/v1/spaces/%(space)s/tickets'
TICKET_STATUSES_URL = 'https://api.assembla.com/v1/spaces/%(space)s/tickets/statuses'
TICKET_COMMENTS_URL = 'https://api.assembla.com//v1/spaces/%(space)s/tickets/%(ticket_number)s/ticket_comments'
DOCUMENTS_URL = 'https://api.assembla.com/v1/spaces/%(space)s/documents'

FRONTEND_TICKET_URL = 'https://www.assembla.com/spaces/%(space)s/tickets'

class TicketStatus(object):
    CLOSED = 0
    OPENED = 1


class AssemblaNotAuthorized(Exception):
    pass

def _generate_ticket_url(ticket, space):
    ticket_number = str(ticket['number'])
    url = FRONTEND_TICKET_URL % {'space': space} + '/' + ticket_number
    return url

def __get_auth_header(request):
    if 'assembla' not in request.session:
        return None
    config = request.session['assembla']
    if 'authorized' not in config:
        return None
    elif not config['authorized']:
        return None
    if 'access_token' not in config:
        if 'authorized' in config:
            request.session['assembla']['authorized'] = False
        return None
    access_token = request.session['assembla']['access_token']
    return {'Authorization': 'Bearer ' + access_token}

def get_login_url(request):
    client_id = request.registry.settings['assembla.client_id']
    return LOGIN_URL_TEMPLATE % {'client_id': client_id}

def authorize(request, code):
    client_id = request.registry.settings['assembla.client_id']
    client_secret = request.registry.settings['assembla.client_secret']

    authorization_url = AUTHORIZATION_URL % \
        {
            'client_id': client_id,
            'client_secret': client_secret,
            'authorization_code': code
        }
    response = requests.post(authorization_url, auth=(client_id, client_secret))

    if response.status_code != 200:
        log.error("Assembla: authorization failed: wrong return HTTP status code")
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    if 'error' in res:
        log.error("Assembla: authorization failed: %s" % res['error'])
        request.session['assembla']['authorized'] = False
        return None

    if not 'assembla' in request.session:
        request.session['assembla'] = {}
    request.session['assembla']['authorized'] = True
    request.session['assembla']['token_type'] = res['token_type']
    request.session['assembla']['access_token'] = res['access_token']
    request.session['assembla']['expires_in'] = datetime.datetime.now() + datetime.timedelta(seconds=res['expires_in'])
    request.session['assembla']['refresh_token'] = res['refresh_token']

    return res['access_token']

def forget(request):
    if 'assembla' in request.session:
        request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False

def get_users(request):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    url = SPACE_USERS_URL % {'space': space}

    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code == 404:
        log.error("Assembla: getting users list failed: space '%s' not found" % space)
        print "Assembla: getting users list failed: space '%s' not found" % space
        return None

    if response.status_code != 200:
        log.error("Assembla: getting users list failed: wrong return HTTP status code")
        print "Assembla: getting users list failed: wrong return HTTP status code: %s" % str(response.status_code)
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    users = [{'name': user['name'], 'id': user['id']} for user in res]

    return users

def get_user(request, id):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    url = USERS_URL + "/%(id)s.json" % {'id': id}
    print url

    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code != 200:
        log.error("Assembla: getting user failed: wrong return HTTP status code")
        print "Assembla: getting user failed: wrong return HTTP status code: %s" % str(response.status_code)
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    return res

def create_ticket(request, summary, description, assign_to, followers=None):
    if followers is None:
        followers = []
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    for follower_id in followers:
        follower = get_user(request, follower_id)
        if not follower:
            return None

    space = request.registry.settings['assembla.space']

    url = TICKETS_URL % {'space': space} + ".json"

    data = {
        'ticket': {
            'summary': summary,
            'description': description,
            'assigned_to_id': assign_to,
            'followers': followers,
            'custom_fields': {u'Component': u'Maintenance'},
        }
    }

    headers = __get_auth_header(request)
    headers['Content-type'] = 'application/json'
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code == 404:
        log.error("Assembla: creating ticket error: space '%s' not found" % space)
        return None

    if response.status_code == 422:
        log.error("Assembla: creating ticket error: wrong data format")
        return None

    if response.status_code != 201:
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    return res['id']

def get_ticket(request, ticket_id):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    ticket_id = str(ticket_id)

    url = TICKETS_URL % {'space': space} + "/id/%s.json" % ticket_id

    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code == 404:
        log.error("Assembla: getting ticket error: space '%s' or ticket id '%s' not found" % (space, ticket_id))
        return None

    if response.status_code != 200:
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()
    res['url'] = _generate_ticket_url(res, space)

    return res

def get_ticket_by_num(request, ticket_num):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        print "not authorized"
        return None

    space = request.registry.settings['assembla.space']

    ticket_id = str(ticket_num)

    url = TICKETS_URL % {'space': space} + "/%s.json" % ticket_id

    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code == 404:
        log.error("Assembla: getting ticket error: space '%s' or ticket id '%s' not found" % (space, ticket_id))
        return None

    if response.status_code != 200:
        forget(request)
        raise AssemblaNotAuthorized()

    res = response.json()
    res['url'] = _generate_ticket_url(res, space)

    return res

def get_ticket_status(request, status_id):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    status_id = str(status_id)

    url = TICKET_STATUSES_URL % {'space': space} + "/%s.json" % status_id

    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code == 404:
        log.error("Assembla: getting ticket status error: space '%s' or ticket status id '%s' not found" % (space, status_id))
        return None

    if response.status_code != 200:
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    return res

def close_ticket(request, ticket_id):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    # load ticket information
    ticket = get_ticket(request, ticket_id)
    if not ticket:
        return None

    if ticket['state'] == TicketStatus.CLOSED:
        return None

    ticket_number = str(ticket['number'])

    data = {
        "ticket": {
            "state": TicketStatus.CLOSED,
            "status": "Sign Off"
        }
    }

    url = TICKETS_URL % {'space': space} + "/%s.json" % ticket_number

    headers = __get_auth_header(request)
    headers['Content-type'] = 'application/json'
    response = requests.put(url, data=json.dumps(data), headers=headers)

    if response.status_code == 404:
        log.error("Assembla: updating ticket error: space '%s' or ticket id '%s' not found" % (space, ticket_id))
        return None

    if response.status_code == 422:
        log.error("Assembla: updating ticket error: wrong data format")
        return None

    if response.status_code != 200:
        request.session['assembla']['authorized'] = False
        return None

    return ticket_id

def get_document(request, document_id):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    document_id = str(document_id)

    url = DOCUMENTS_URL % {'space': space} + "/%s.json" % document_id

    log.info("Getting document url: %s" % url)
    response = requests.get(url, headers=__get_auth_header(request))

    if response.status_code == 404:
        log.error("Assembla: getting document error: space '%s' or document id '%s' not found" % (space, document_id))
        return None

    if response.status_code != 200:
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    return res

def create_document(request, file_path):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None
    if not os.path.isfile(file_path):
        return None

    space = request.registry.settings['assembla.space']

    url = DOCUMENTS_URL % {'space': space} + ".json"

    files = {'document[file]': open(file_path, 'rb')}

    log.info("Sending request to %s" % url)
    log.info("Headers: %s" % __get_auth_header(request))
    response = requests.post(url, files=files, headers=__get_auth_header(request))

    if response.status_code == 404:
        print "Assembla: error uploading file '%s': space '%s' not found" % (file_path, space)
        log.error("Assembla: error uploading file '%s': space '%s' not found" % (file_path, space))
        return None

    if response.status_code == 422:
        print "Assembla: error uploading file '%s': wrong data format" % file_path
        log.error("Assembla: error uploading file '%s': wrong data format" % file_path)
        return None

    res = response.json()

    log.info("Create document response:")
    log.info(res)

    return res['id']

def create_ticket_for_spider(request, summary, description, assign_to):
    followers = []
    supervisor_manager_id = request.registry.settings['assembla.supervisor_manager_id']
    if supervisor_manager_id and get_user(request, supervisor_manager_id):
        followers.append(supervisor_manager_id)
    return create_ticket(request, summary, description, assign_to, followers)

def associate_document_with_ticket(request, document_id, ticket_id, description):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    document_id = str(document_id)
    ticket_id = str(ticket_id)

    # load ticket information
    ticket = get_ticket(request, ticket_id)
    if not ticket:
        return None

    document = get_document(request, document_id)
    if not document:
        return None

    data = {
        "document": {
            "attachable_type": "Ticket",
            "attachable_id": ticket_id,
            "description": description
        }
    }

    url = DOCUMENTS_URL % {'space': space} + "/%s.json" % document_id

    headers = __get_auth_header(request)
    headers['Content-type'] = 'application/json'
    response = requests.put(url, data=json.dumps(data), headers=headers)

    if response.status_code == 404:
        print "Assembla: updating document error: space '%s' or ticket id '%s' or document id '%s' not found" % (space, ticket_id, document_id)
        log.error("Assembla: updating document error: space '%s' or ticket id '%s' or document id '%s' not found" % (space, ticket_id, document_id))
        return None

    if response.status_code == 422:
        print "Assembla: updating document error: wrong data format"
        log.error("Assembla: updating document error: wrong data format")
        return None

    if response.status_code not in (200, 204):
        print "Assembla: `associate_document_with_ticket` error response: %s" % response.status_code
        request.session['assembla']['authorized'] = False
        return None

    return document_id

def create_comment(request, ticket_id, comment):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    space = request.registry.settings['assembla.space']

    ticket_id = str(ticket_id)

    # load ticket information
    ticket = get_ticket(request, ticket_id)
    if not ticket:
        return None

    ticket_number = str(ticket['number'])

    url = TICKET_COMMENTS_URL % {'space': space, 'ticket_number': ticket_number} + ".json"

    data = {
        'ticket_comment': {
            'comment': comment
        }
    }

    headers = __get_auth_header(request)
    headers['Content-type'] = 'application/json'
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code == 404:
        print "Assembla: creating ticket comment error: space '%s' or ticket id '%s' not found" % (space, ticket_id)
        log.error("Assembla: creating ticket comment error: space '%s' or ticket id '%s' not found" % (space, ticket_id))
        return None

    if response.status_code == 422:
        print "Assembla: creating ticket comment error: wrong data format"
        log.error("Assembla: creating ticket comment error: wrong data format")
        return None

    if response.status_code != 201:
        print "Assembla: `create_comment` error response: %s" % response.status_code
        request.session['assembla']['authorized'] = False
        return None

    res = response.json()

    return res['id']

def create_attachment_comment(request, ticket_id, document_id, description):
    if 'assembla' not in request.session or 'access_token' not in request.session['assembla']:
        if 'assembla' not in request.session:
            request.session['assembla'] = {}
        request.session['assembla']['authorized'] = False
        return None

    document_id = str(document_id)
    document = get_document(request, document_id)
    if not document:
        return None

    comment = "[[file:%s]]\n%s" % (document_id, description)

    return create_comment(request, ticket_id, comment)


def ticket_add_attachment(request, ticket_id, file_path, description=None):
    document_id = create_document(request, file_path)
    if not document_id:
        print "Assembla: `ticket_add_attachment` not document id error"
        return None
    attached = associate_document_with_ticket(request, document_id, ticket_id, description)
    if not attached:
        print "Assembla: `ticket_add_attachment` not attached error"
        return None
    comment_created = create_attachment_comment(request, ticket_id, document_id, description)
    if not comment_created:
        print "Assembla: `ticket_add_attachment` not comment created error"
        return None
    return document_id
