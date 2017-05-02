from changes import Change


class ChangeJoinComputation(object):
    """
    Represents a single updater to be passed over to a JoinFunction.
    This class expects to receive Change objects as the result.
    Attributes:
        accept_codes -- Change codes that will be accepted when performing the computation.
                        This is to be able to create computations that just operate over certain types of changes.
    """
    accept_codes = [Change.NO_CHANGE, Change.UPDATE, Change.OLD, Change.NEW]

    def __init__(self, settings=None):
        """

        :param settings: Updater's settings
        :return:
        """
        self.settings = settings or {}

    def process_result(self, result):
        """
        Process a result(change)
        :param result:
        :return:
        """
        change_type, _ = result.change_data()
        if change_type in self.accept_codes:
            return self.process_res(result)

    def process_res(self, result):
        """
        Method to be implemented by each class performing the real computation
        :param result:
        :return:
        """
        raise NotImplemented()