#!/usr/bin/env python3

import argparse
import fileinput
import os
import re
import sys

if __name__ == '__main__':
    script_path = os.path.dirname(os.path.realpath(__file__))
    init_script_path = os.path.join(script_path, 'apertium-init.py')

    parser = argparse.ArgumentParser(description='Update the bootstraper script for an Apertium lttoolbox-based language module')
    parser.add_argument('-d', '--vanillaDirectory', help='location of directory with vanilla files', default=script_path)
    parser.add_argument('-f', '--bootstraperScript', help='location of bootstraper script', default=init_script_path)
    args = parser.parse_args()

    english_lang_names = {}
    for line in fileinput.input([os.path.join(args.vanillaDirectory, 'language_names.tsv')]):
        code, name = line.strip().split('\t')
        english_lang_names[code] = name

    iso639_codes = {}
    for line in fileinput.input([os.path.join(args.vanillaDirectory, 'iso639_codes.tsv')]):
        code1, code2 = line.strip().split('\t')
        iso639_codes[code1] = code2

    for line in fileinput.input([args.bootstraperScript], inplace=True):
        line = re.sub(r'^english_lang_names = {.*?}  # noqa: E501$', 'english_lang_names = %s  # noqa: E501' % repr(english_lang_names), line)
        line = re.sub(r'^iso639_codes = {.*?}  # noqa: E501$', 'iso639_codes = %s  # noqa: E501' % repr(iso639_codes), line)
        sys.stdout.write(line)
