from changes_updater.join import SortedJoin, JoinFunction, CompositeJoinFunction
from changes_updater.export import Exporter
from changes_updater.stats import ChangesStats, AdditionalChangesStats
from changes_updater.datafiles import sort_products_file, SortedFile, CSVReader
from changes_updater.changes import PriceChange, AdditionalChange

old_file = SortedFile('/home/lucas/old.csv', sort_products_file, reader=CSVReader)
new_file = SortedFile('/home/lucas/new.csv', sort_products_file, reader=CSVReader)
sorted_join = SortedJoin(old_file, new_file)

f1 = open('/tmp/changes.csv', 'w')
exporter1 = Exporter(output_file=f1, format_func=lambda result: result.format_csv())
stats1 = ChangesStats()
join_function1 = JoinFunction(PriceChange, [exporter1, stats1])

f2 = open('/tmp/additional_changes.csv', 'w')
exporter2 = Exporter(output_file=f2, format_func=lambda result: result.format_json())
stats2 = AdditionalChangesStats()
join_function2 = JoinFunction(AdditionalChange, [exporter2, stats2])

join_function = CompositeJoinFunction([join_function1, join_function2])

sorted_join.full_join(join_function, lambda x, y: cmp(x['identifier'], y['identifier']))

print stats1.stats
print stats2.stats
