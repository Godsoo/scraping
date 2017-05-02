class SortedJoin(object):
    """
    Class to compute join operations between sorted iterables.
    When joining two elements a passed function will be called with them.
    """
    def __init__(self, sorted_left, sorted_right):
        """
        Constructor
        :param sorted_left: Sorted iterable
        :param sorted_right: Sorted iterable
        :return:
        """
        self.sorted_left = sorted_left
        self.sorted_right = sorted_right

    def _get_element(self, f):
        try:
            return f.next()
        except StopIteration:
            return None

    def full_join(self, join_func, cmp_func):
        """
        Perform a full join between the elements of the two iterables.
        :param join_func: Function to call when joining two items.
        The function should receive two parameters, the left element and the right element.
        Since this is a full join when there's no right or left element the None object will be passed instead.
        :param cmp_func: function to compare the elements from the sorted iterables.
        Should return -1, 0, or 1 depending on which element has a higher value.
        :return:
        """
        left_el = self._get_element(self.sorted_left)
        right_el = self._get_element(self.sorted_right)

        while left_el and right_el:
            comp = cmp_func(left_el, right_el)
            if comp < 0:
                join_func(left_el, None)
                left_el = self._get_element(self.sorted_left)
            elif comp > 0:
                join_func(None, right_el)
                right_el = self._get_element(self.sorted_right)
            else:
                join_func(left_el, right_el)
                left_el = self._get_element(self.sorted_left)
                right_el = self._get_element(self.sorted_right)

        while left_el:
            join_func(left_el, None)
            left_el = self._get_element(self.sorted_left)

        while right_el:
            join_func(None, right_el)
            right_el = self._get_element(self.sorted_right)

    def inner_join(self, join_func, cmp_func):
        """
        Perform an inner join between the elements of the two iterables.
        :param join_func: Function to call when joining two items.
        The function should receive two parameters, the left element and the right element.
        :param cmp_func: function to compare the elements from the sorted iterables.
        Should return -1, 0, or 1 depending on which element has a higher value.
        :return:
        """
        left_el = self._get_element(self.sorted_left)
        right_el = self._get_element(self.sorted_right)

        while left_el and right_el:
            comp = cmp_func(left_el, right_el)
            if comp < 0:
                left_el = self._get_element(self.sorted_left)
            elif comp > 0:
                right_el = self._get_element(self.sorted_right)
            else:
                join_func(left_el, right_el)
                left_el = self._get_element(self.sorted_left)
                right_el = self._get_element(self.sorted_right)


class JoinFunction(object):
    """
    Helper class to create objects to pass over to SortedJoin.
    It receives a result class that will create an object representing the join operation
    between the right and the left element. This object is then passsed over to different updaters
    that perform operations on it.
    """
    def __init__(self, result_cls, updaters, settings=None):
        """
        Constructor
        :param result_cls: Result constructor, receives the left element and right element as parameters
        :param updaters: List of updaters, each updater receives the result
        constructed with result_cls as a parameter
        :param settings: Update settings dict
        :return:
        """
        self.result_cls = result_cls
        self.updaters = updaters
        self.settings = settings or {}

    def __call__(self, left_el, right_el):
        result = self.result_cls(left_el, right_el, self.settings)
        for updater in self.updaters:
            updater.process_result(result)


class CompositeJoinFunction(object):
    """
    Class to manage a list of JoinFunction objects in a join operation.
    This is useful when we need to create different results when joining and use different updaters
    for each result
    """
    def __init__(self, join_funcs):
        """
        Constructor
        :param join_funcs: List of JoinFunction objects
        :return:
        """
        self.join_funcs = join_funcs

    def __call__(self, left_el, right_el):
        for j in self.join_funcs:
            j(left_el, right_el)