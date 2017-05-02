from join_computation import ChangeJoinComputation


class Exporter(ChangeJoinComputation):
    """ Class to export Join functions results
    """
    def __init__(self, output_file=None, header=None, format_func=None, accept_codes=None, **kwargs):
        """
        Constructor
        :param output_file: path to save the resulting file
        :param header: file's header (only for csv)
        :param format_func: formatting function
        :return:
        """
        super(Exporter, self).__init__(**kwargs)
        self._exported_lines = 0
        if accept_codes:
            self.accept_codes = accept_codes
        self.format_func = format_func
        self.output_file = output_file
        if header:
            self.output_file.write(header + '\n')

    def process_res(self, result):
        line = self.format_func(result)
        if line:
            self._exported_lines += 1
            self.output_file.write(line + '\n')

    def export(self, result):
        self.process_res(result)

    @property
    def exported_lines(self):
        return self._exported_lines