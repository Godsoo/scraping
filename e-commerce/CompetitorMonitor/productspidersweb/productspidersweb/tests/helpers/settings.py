__author__ = 'juraseg'

def _getTestSettings():
    from productspidersweb.security import _hash_password
    settings = {
        'sqlalchemy.url': 'sqlite://',
        'app.authorization.enabled': 'true',
        'app.authorization.user': _hash_password('123'),
        'app.authorization.admin': _hash_password('123'),
    }
    return settings