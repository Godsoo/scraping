
if __name__ == '__main__':
    import csv

    main_header = 'MTS Stock Code,Website,Pattern,Brand,Segment,Full Tyre Size,Width,Aspect Ratio,Rim,Load rating,Speed Rating,Alternative speed rating,XL,Run Flat,Manufacturer mark,Fitted or Delivered,Price'

    with open('new_manual_mts_codes.csv', 'w') as f:
        header = main_header.split(',')
        writer = csv.DictWriter(f, header)
        writer.writeheader()
        with open('micheldever_new_master_file.csv') as f2:
            reader = csv.DictReader(f2)
            for row in reader:
                new_row = dict([(k, row[k]) for k in row.keys() if k in header])
                if row['New Code'].strip():
                    new_row['MTS Stock Code'] = row['New Code']
                    writer.writerow(new_row)
                elif 'remove' in row['Comments'].lower():
                    new_row['MTS Stock Code'] = ''
                    writer.writerow(new_row)
