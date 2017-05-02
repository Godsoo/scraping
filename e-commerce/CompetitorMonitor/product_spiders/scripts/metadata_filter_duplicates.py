# -*- coding: utf-8 -*-
"""
Removes duplicate records in metadata. Ignores names. By default picks non-old products
"""
import os
import sys
import json
import tempfile

import click

sys.path.append('../..')

from changes_updater.datafiles import sort_metadata_file


def _hash_identifier(product):
    identifier = product['identifier']
    identifier = identifier.decode('utf-8') if isinstance(identifier, str) else identifier
    return identifier.encode('utf-8')


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option('--merge_type', type=click.Choice(['remove_old']), default='remove_old')
def remove_metadata_duplicates(input_path, output_path, merge_type):
    sorted_fd, sorted_path = tempfile.mkstemp()
    # sort products by identifier
    sort_metadata_file(input_path, sorted_path, hash_func=_hash_identifier)

    if merge_type == 'remove_old':
        dups_removed = 0
        dups_kept = 0
        with open(sorted_path) as fs:
            with open(output_path, 'w+') as fo:
                other_prev_prods = []
                prev_prod = None
                for row in fs:
                    prod = json.loads(row, encoding='utf-8')
                    if not prev_prod:
                        # first cycle
                        prev_prod = prod
                        other_prev_prods = []
                        continue
                    if prev_prod['identifier'] != prod['identifier']:
                        # write to output file
                        fo.write(json.dumps(prev_prod, encoding='utf-8'))
                        fo.write('\n')
                        for p in other_prev_prods:
                            fo.write(json.dumps(p, encoding='utf-8'))
                            fo.write('\n')
                        prev_prod = prod
                        other_prev_prods = []
                        continue

                    if prev_prod['identifier'] == prod['identifier']:
                        # found duplicate
                        if prev_prod.get('_status', None) == 'old':
                            # replace prev_prod if it's for old product
                            prev_prod = prod
                            dups_removed += 1
                        elif prod.get('_status') == 'old':
                            # skip duplicate if it's for old product
                            dups_removed += 1
                        else:
                            # saving all non-old products
                            other_prev_prods.append(prod)
                            dups_kept += 1

        click.echo('Removed {} duplicates with "old" status'.format(dups_removed))
        click.echo('Kept {} duplicates with non-"old" status'.format(dups_kept))
    os.unlink(sorted_path)


if __name__ == '__main__':
    remove_metadata_duplicates()
