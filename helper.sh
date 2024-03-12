#!/bin/bash

# Concatenate all .csv files into email_list.csv
cat *.csv > email_list.csv

# Sort and deduplicate the contents
sort -u -o email_list.csv email_list.csv