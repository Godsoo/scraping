# -*- coding: utf-8 -*-
import re
import subprocess
import os
from contextlib import contextmanager


commit_reg = re.compile(r"""changeset:\s+(?P<changeset>.*)
user:\s+(?P<user>.*)
date:\s+(?P<date>.*)
files:\s+(?P<files>.*)
description:
(?P<desc>.*)

""", re.MULTILINE + re.IGNORECASE)

commiter_reg = re.compile(r'user:\s*(.*)', re.I)

commit_reg2 = re.compile(r"""changeset:\s+(?P<changeset>.*)
user:\s+(?P<user>.*)
date:\s+(?P<date>.*)
summary:\s+ (?P<desc>.*)

""", re.MULTILINE + re.IGNORECASE)


summary_reg = re.compile(r"""parent:\s+(?P<changeset>[^\s]*)(?:\s+.*)?
.*
branch: (?P<branch>.*)
commit: .*
update: .*
""", re.MULTILINE + re.IGNORECASE + re.DOTALL)


def parse_commits(history):
    parsed = False
    for m in commit_reg.finditer(history):
        parsed = True
        yield m.groupdict()
    if parsed:
        return
    for m in commit_reg2.finditer(history):
        parsed = True
        yield m.groupdict()


def parse_summary(summary):
    m = summary_reg.search(summary)
    if not m:
        return None
    return m.groupdict()


def get_commits_for_file(filepath, hg_exec):
    try:
        history = subprocess.check_output([hg_exec, 'log', filepath])
    except subprocess.CalledProcessError, e:
        print "Error getting commiters for file %s: %s" % (filepath, str(e))
        return None, None
    commits = parse_commits(history)
    return list(commits)


@contextmanager
def chwd(path):
    """
    Context manager changes current working directory.
    It reverts working directory on clean-up
    """
    curwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(curwd)


def get_directory_active_changeset_data(path, hg_exec):
    with chwd(path):
        os.chdir(path)
        try:
            summary = subprocess.check_output([hg_exec, 'summary'])
        except subprocess.CalledProcessError, e:
            print "Error summary for path %s: %s" % (path, str(e))
            return None
    return parse_summary(summary)


PRODUCT_SPIDERS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PRODUCT_SPIDERS)
BRANCH_FILENAME = 'current_branch.txt'
CHANGESET_FILENAME = 'current_changeset.txt'


def save_root_active_changeset_data(hg_exec):
    data = get_directory_active_changeset_data(ROOT, hg_exec)
    branch_filepath = os.path.join(ROOT, BRANCH_FILENAME)
    with open(branch_filepath, 'w+') as f:
        f.write(data['branch'])
    changeset_filepath = os.path.join(ROOT, CHANGESET_FILENAME)
    with open(changeset_filepath, 'w+') as f:
        f.write(data['changeset'])
    return data


def load_root_active_changeset_data():
    try:
        res = {}
        branch_filepath = os.path.join(ROOT, BRANCH_FILENAME)
        with open(branch_filepath, 'r') as f:
            res['branch'] = f.read()
        changeset_filepath = os.path.join(ROOT, CHANGESET_FILENAME)
        with open(changeset_filepath, 'r') as f:
            res['changeset'] = f.read()
        return res
    except IOError:
        return {}