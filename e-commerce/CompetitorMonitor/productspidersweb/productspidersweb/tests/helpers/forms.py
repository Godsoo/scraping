__author__ = 'juraseg'

class RandomFormFieldsGenerator(object):
    @classmethod
    def __randomBool(cls):
        import random
        random.seed()
        return bool(random.randint(0, 1))  # return False on 0 and True on 1

    @classmethod
    def __randomInt(cls):
        import random
        random.seed()
        limit = 2 ** 63 - 1
        return random.randint(0, limit)

    @classmethod
    def __randomEmail(cls):
        names = [
            'test',
            'test2',
            'admin',
            'foo',
            'bar',
            'admin',
            'administrator',
            'example',
            'foobar',
            'pyramid',
            'unittest',
            'python'
        ]
        domains = [
            'org',
            'net',
            'com',
            'co.uk',
            'io'
        ]
        import random
        random.seed()
        name = random.choice(names)
        domain = random.choice(names) + "." + random.choice(domains)

        return name + "@" + domain

    @classmethod
    def __randomEmailList(cls):
        limit = 5
        import random
        random.seed()
        emails = [cls.__randomEmail() for i in xrange(0, random.randint(1, limit))]
        return ",".join(emails)

    @classmethod
    def generateField(cls, field_type):
        from productspidersweb.formschemas import (
            EmailList
            )
        from formencode.validators import (
            Bool,
            Int
            )
        if isinstance(field_type, Bool):
            return RandomFormFieldsGenerator.__randomBool()
        elif isinstance(field_type, Int):
            return RandomFormFieldsGenerator.__randomInt()
        elif isinstance(field_type, EmailList):
            return RandomFormFieldsGenerator.__randomEmailList()
        else:
            return None