import tempfile
import subprocess
import json
import os
import csv
import shutil


class SortedFile(object):
    """
    An object of SortedFile provides a way to iterate over a file by sorting it first using a sort function.
    Also a reader will be passed as a parameter to return the data after being parsed.
    """
    def __init__(self, path, sort_function, reader=None):
        """
        Constructor
        :param path: path of the file
        :param sort_function: function that receives a path as the only argument and returns a new path
        that contains the same file but sorted
        :param reader: object in charge to parse the lines of the sorted file and convert them to a python object
        :return:
        """
        self.path = path
        self.sort_function = sort_function
        self._sorted_path = None
        self._sorted_file = None
        self.reader = reader

    def __iter__(self):
        return self

    def next(self):
        if not self._sorted_path:
            self._sorted_path = tempfile.mktemp()
            self.sort_function(self.path, self._sorted_path)
            self._sorted_file = open(self._sorted_path)
            if self.reader:
                self._sorted_file = self.reader(self._sorted_path)

        return self._sorted_file.next()

    def close(self):
        pass


def sort_products_file(path, sorted_path, hash_func=None):
    """
    Sort a csv file with products by the first column(identifier)
    :param path: file's path
    :param sorted_path: path to save the sorted file
    :param hash_func: optional hash function to put as the first column
    """
    src = path
    if hash_func:
        temp_ = tempfile.mktemp()
        with open(path) as f:
            with open(temp_, 'w') as out:
                reader = csv.DictReader(f)
                # only do this if header is present
                if reader.fieldnames:
                    writer = csv.DictWriter(out, ['product_hash'] + reader.fieldnames)
                    writer.writeheader()

                    for row in reader:
                        row['product_hash'] = hash_func(row)
                        writer.writerow(row)
                else:
                    for row in reader:
                        raise ValueError("File header is missing in %s but there are records" % path)
        src = temp_

    subprocess.call('head -n 1 {} > {}'.format(src, sorted_path), shell=True)
    subprocess.call('tail -n +2 {} | sort --buffer-size=10M -t "," -k 1,1 >> {}'.format(src, sorted_path), shell=True)


def sort_metadata_file(path, sorted_path, hash_func=None):
    """
    Sort Json-lines file containing the metadata of each product.
    The file is sorted by the universal_identifier attribute if it's in the metadata, if not,
     the identifier attribute is used.
    :param path: file's path
    :param sorted_path: path to save the sorted file
    :return:
    """
    temp_ = tempfile.mktemp()
    with open(path) as f:
        with open(temp_, 'w') as out:
            for line in f:
                data = json.loads(line, encoding='utf-8')
                if hash_func:
                    ident = hash_func(data)
                else:
                    ident = data.get('universal_identifier') or data.get('identifier')
                    ident = ident.encode('utf-8')
                ident = ident.replace('|', '')
                out.write(ident + '|' + line)

    subprocess.call('sort -k 1,1 -t "|"  --buffer-size=10M {} | cut -d "|" -f 2- > {}'.format(temp_, sorted_path),
                    shell=True)
    os.unlink(temp_)


def remove_non_unique_hashes(path):
    """
    Given a path to a csv file with a hash in the first column, removes all the rows that have non unique hashes.
    :param path: path to the csv file
    :return:
    """
    def get_element(it):
        try:
            return it.next()
        except StopIteration:
            return None

    temp_ = tempfile.mktemp()
    with open(path) as f:
        with open(temp_, 'w') as out:
            reader = csv.reader(f)
            writer = csv.writer(out)
            header = reader.next()
            writer.writerow(header)
            previous_row = None
            current_row = get_element(reader)
            while current_row:
                next_row = get_element(reader)
                if (not previous_row or previous_row[0] != current_row[0]) and \
                    (not next_row or next_row[0] != current_row[0]):
                    writer.writerow(current_row)
                previous_row = current_row
                current_row = next_row

    shutil.move(temp_, path)


class JsonLinesReader(object):
    """Simple wrapper class to read a json-lines file in an iterative way"""
    def __init__(self, path):
        self.path = path
        self.file_ = open(path)

    def __iter__(self):
        return self

    def next(self):
        n = self.file_.next()
        return json.loads(n)


class CSVReader(object):
    """Simple wrapper class to read a csv file in an iterative way"""
    def __init__(self, path):
        self.path = path
        self.file_ = csv.DictReader(open(path))

    def __iter__(self):
        return self

    def next(self):
        n = self.file_.next()
        for c in n:
            n[c] = n[c].decode('utf8')
        return n
