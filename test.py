#!/usr/bin/env python

import csv
import json
import io
from io import StringIO
import subprocess
from subprocess import check_output

import pandas as pd
from tabulate import tabulate

seq = '>test1\nTGGGGAATATTGGGCAATGGAGGAAACTCTGACCCAGCGACGCCGCGTGCGGGATGAAGGCCTTCGGGTTGTAAACCGCTTTCAGCAGGGAAGAAGCGAAAGTGACGGTACCTGCAGAAGAAGCACCGGCTAACTATGTGCCAGCAGCCGCGGTAATACATAGGGTGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGAGCTCGTAGGTGGTTCGTCACGTCGGATGTGAAACTCTGGGGCTTAACCCCAGACCTGCATTCGATACGGGCGAGCTTGAGTATGGTAGGGGAGTCTGGAATTCCTGGTGTAGCGGTGGAATGCGCAGATATCAGGAGGAACACCAATGGCGAAGGCAGGACTCTGGGCCATTACTGACACTGAGGAGCGAAAGCGTGGGGAGCGAACA'


def main():

    raw_data = {'first_name': ['JasonXXXTest', 'Molly', 'Tina', 'Jake', 'Amy'],
                'last_name': ['Miller', 'Jacobson', 'Ali', 'Milner', 'Cooze'],
                'age': [42, 52, 36, 24, 73],
                'preTestScore': [4, 24, 31, 2, 3],
                'postTestScore': [25, 94, 57, 62, 70]}

    # df = pd.DataFrame({'A': [0, 1, 2, 3, 4],
    #                    'B': [5, 6, 7, 8, 9],
    #                    'C': ['a', 'b', 'c', 'd', 'e']})

    # print(tabulate(df))

    # df = df.replace(0, 5)

    # print(tabulate(df))

    df = pd.DataFrame(raw_data, columns=['first_name',
                                         'last_name', 'age', 'preTestScore', 'postTestScore'])

    print(tabulate(df))

    df['first_name'] = df['first_name'].str.replace('XXX', '')

    df[['First', 'Last']] = df['first_name'].str.split("i", expand=True,)
    print(tabulate(df))


if __name__ == '__main__':
    main()
