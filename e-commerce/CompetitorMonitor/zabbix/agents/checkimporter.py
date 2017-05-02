#!/usr/bin/python
import os

here = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(here, 'importer_status')) as f:
    print f.read()

