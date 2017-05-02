# -*- coding: utf-8 -*-
import hashlib

from productspidersweb.models import (
    DBSession,
    User,
    UserGroup,
)

from pyramid.security import (
    Authenticated,
    authenticated_userid,
    unauthenticated_userid,
)

from pyramid.httpexceptions import HTTPFound
from pyramid.authentication import AuthTktAuthenticationPolicy

def __sha256(string):
    m = hashlib.sha256()
    m.update(string)
    return m.hexdigest()

def _hash_password(password):
    return __sha256(password)

def _get_user_hashed_password(request, user):
    db_session = DBSession()
    user_db = db_session.query(User).filter(User.username == user).first()
    return user_db.password if user_db else None

class InsightAuthorizationPolicy(object):
    """ An object representing a Pyramid authorization policy. """
    def permits(self, context, principals, permission):
        for perm in principals:
            if perm == permission:
                return True
            if ("g:" + permission) == perm:
                return True
        else:
            return False

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()

def principals_finder(userid, request):
    db_session = DBSession()
    perms = []
    if _get_user_hashed_password(request, userid) is not None:
        for group in db_session.query(UserGroup).filter(UserGroup.username == userid).all():
            perms.append(group.name)

    return perms

def get_user(request):
    db_session = DBSession()
    userid = unauthenticated_userid(request)
    if userid is not None:
        return db_session.query(User).filter(User.username == userid).first()

def add_authorization(config):
    """ Adds authentication/authorization
    Use as include to config in application init function
    Arguments:
        :param config: application configurator object
        :type config: pyramid.config.Configurator
    """

    authorization_enabled = True
    settings = config.registry.settings
    if 'app.authorization.enabled' in settings:
        if 'app.authorization.enabled' in settings and\
           (settings['app.authorization.enabled'].lower() == 'false' or
            settings['app.authorization.enabled'] == '0'):
            authorization_enabled = False

    if authorization_enabled:
        config.set_default_permission(Authenticated)
        config.set_authorization_policy(InsightAuthorizationPolicy())
        config.set_authentication_policy(AuthTktAuthenticationPolicy('sosecret', callback=principals_finder))
        config.add_request_method(get_user, 'user', reify=True)
        config.include(add_routes)

def add_routes(config):
    """ Adds security related routes
    Arguments:
        :param config: application configurator object
        :type config: pyramid.config.Configurator
    """
    def forbidden(request):
        if authenticated_userid(request):
            return HTTPFound(request.route_url("home"))
        else:
            return HTTPFound(request.route_url("login"))
    config.add_forbidden_view(forbidden)

def authenticate(request, login, password):
    hashed_password = _get_user_hashed_password(request, login)
    if hashed_password is None:
        return False
    if _hash_password(password) == hashed_password:
        return True

def is_login_disabled(login):
    db_session = DBSession()
    user_db = db_session.query(User).filter(User.username == login).first()
    return user_db.login_disabled
