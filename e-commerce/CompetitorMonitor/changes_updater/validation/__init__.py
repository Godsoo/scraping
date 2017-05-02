import json
import csv
from ..join_computation import ChangeJoinComputation


class ValidationError(object):
    """ Represents a crawl validation error
    """
    def __init__(self, code, msg, new_element=None, old_element=None):
        """
        Constructor
        :param code: Error code
        :param msg: Error message
        :return:
        """
        self.code = code
        self.msg = msg
        self.new_element = new_element
        self.old_element = old_element

    def format_json(self):
        return json.dumps({'code': str(self.code), 'msg': self.msg})

    def format_csv(self):
        row = [str(self.code), self.msg.encode('utf8')]
        class f(object):
            res = ''

            def write(self, s):
                self.res = s.strip()

        file_ = f()
        writer = csv.writer(file_)
        writer.writerow(row)

        return file_.res


class Validator(ChangeJoinComputation):
    """
    Join computation class to implement validators.
    Each inheriting validator will need to implement the validate method.
    """
    def __init__(self, exporter, *args, **kwargs):
        super(Validator, self).__init__(*args, **kwargs)
        self.exporter = exporter

    def process_res(self, result):
        for error in self.validate(result) or []:
            self.exporter.export(error)

    def validate(self, result):
        raise NotImplemented()
