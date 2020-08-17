#!/usr/bin/env python3

__author__ = 'Sushain K. Cherivirala, Kevin Brubeck Unhammer'
__copyright__ = 'Copyright 2014--2018, Sushain K. Cherivirala, Kevin Brubeck Unhammer'
__credits__ = ['Sushain K. Cherivirala', 'Kevin Brubeck Unhammer', 'Jonathan North Washington', 'Shardul Chiplunkar']
__license__ = 'GPLv3+'
__status__ = 'Production'
__version__ = '2.3.0'

import argparse
import base64
import getpass
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import urllib.request
import zlib

if False:  # for mypy
    import http.client  # noqa: F401
    from typing import Dict, List, Tuple  # noqa: F401

# DO NOT MODIFY, USE `make` which calls `./updateBoostraper.py`
any_module_files = {}  # noqa: E501
lttoolbox_language_module_files = {}  # noqa: E501
hfst_language_module_files = {}  # noqa: E501
bilingual_module_files = {}  # noqa: E501
# DO NOT MODIFY, USE `make` which calls `./updateBoostraper.py`

english_lang_names = {}  # noqa: E501
iso639_codes = {}  # noqa: E501
organization_name = 'apertium'
default_prefix = 'apertium'
default_email = 'apertium-stuff@lists.sourceforge.net'


def get_lang_name(code):  # type: (str) -> str
    code = iso639_codes[code] if len(code) > 2 and code in iso639_codes else code
    if code in english_lang_names:
        return english_lang_names[code]
    else:
        sys.stdout.write('Unable to find English language name for %s, using ISO code instead.\n' % code)
        return code


def init_pair(args, email):  # type: (argparse.Namespace, str) -> Tuple[Dict[str, bytes], Dict[str, str], List[str]]
    language_code_1, language_code_2 = args.name.split('-')
    replacements = {
        'languageCode1': language_code_1,
        'languageCode2': language_code_2,
        'languageName1': get_lang_name(language_code_1),
        'languageName2': get_lang_name(language_code_2),
        'email': email,
    }

    if args.analyser == 'hfst' or (args.analyser1 == 'hfst' and args.analyser2 == 'hfst'):
        conditionals = ['hfst', 'hfst1', 'hfst2']
    elif args.analyser1 == 'hfst' and args.analyser2 in ['lt', 'lttoolbox']:
        conditionals = ['hfst', 'hfst1', 'lttoolbox2']
    elif args.analyser1 in ['lt', 'lttoolbox'] and args.analyser2 == 'hfst':
        conditionals = ['hfst', 'lttoolbox1', 'hfst2']
    else:
        conditionals = ['lttoolbox1', 'lttoolbox2']

    if not args.no_prob1:
        conditionals.append('prob1')
    if not args.no_prob2:
        conditionals.append('prob2')

    if not args.no_rlx1:
        conditionals.append('rlx1')
    if not args.no_rlx2:
        conditionals.append('rlx2')

    if not args.no_pgen1:
        conditionals.append('pgen1')
    if not args.no_pgen2:
        conditionals.append('pgen2')

    files = dict(bilingual_module_files, **any_module_files)

    if args.with_lsx:
        conditionals.append('lsx')
    else:
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.lsx']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.lsx']

    if args.with_anaphora:
        conditionals.append('anaphora')
    else:
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.arx']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.arx']

    if args.transfer == 'chunk':
        conditionals.append('chunk')
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.rtx']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.rtx']
    else:
        conditionals.append('rtx')
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.t1x']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.t2x']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode1}}-{{languageCode2}}.t3x']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.t1x']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.t2x']
        del files['apertium-{{languageCode1}}-{{languageCode2}}.{{languageCode2}}-{{languageCode1}}.t3x']

    return files, replacements, conditionals


def init_lang_module(args, email):  # type: (argparse.Namespace, str) -> Tuple[Dict[str, bytes], Dict[str, str], List[str]]
    replacements = {
        'languageCode': args.name,
        'languageName': get_lang_name(args.name),
        'email': email,
    }

    conditionals = []

    if args.analyser in ['lt', 'lttoolbox']:
        files = dict(lttoolbox_language_module_files, **any_module_files)
    elif args.analyser == 'hfst':
        files = dict(hfst_language_module_files, **any_module_files)
        if args.with_twoc:
            conditionals.append('twoc')
        else:
            del files['apertium-{{languageCode}}.{{languageCode}}.twoc']
        if args.with_spellrelax:
            conditionals.append('spellrelax')
        else:
            del files['apertium-{{languageCode}}.{{languageCode}}.spellrelax']
    else:
        raise Exception('Unrecognized analyser: ' % args.analyser)

    return files, replacements, conditionals


def make_replacements(s, replacements, conditionals):  # type: (str, Dict[str, str], List[str]) -> str
    for _ in range(2):
        s = re.sub(r'{{if_(\w+)[^\n]*(.*?)\nif_\1}}', lambda x: x.group(2) if x.group(1) in conditionals else '', s, flags=re.DOTALL)
        s = re.sub(r'{{ifnot_(\w+)[^\n]*(.*?)\nifnot_\1}}', lambda x: x.group(2) if x.group(1) not in conditionals else '', s, flags=re.DOTALL)
    for replacement_name, replacement_value in replacements.items():
        s = s.replace('{{%s}}' % replacement_name, replacement_value)
    return s


def make_all_replacements(destination, files, replacements, conditionals):  # type: (str, Dict[str, bytes], Dict[str, str], List[str]) -> None
    for filename, encoded_file in files.items():
        replacements_filename = make_replacements(filename, replacements, conditionals)
        path = os.path.join(destination, replacements_filename)
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        if os.path.exists(path):
            backup = os.path.join(folder, '.bak')
            if not os.path.isdir(backup):
                os.mkdir(backup)
            os.rename(path, os.path.join(backup, replacements_filename))
        with open(path, 'wb') as f:
            decomp = zlib.decompress(base64.b85decode(encoded_file))
            try:
                f.write(make_replacements(str(decomp, encoding='utf-8'), replacements, conditionals).encode('utf-8'))
            except UnicodeDecodeError:  # binary file
                f.write(decomp)


def push_to_github(args, folder, username):  # type: (argparse.Namespace, str, str) -> None
    remote_name = 'origin'
    repository_name = '{}-{}'.format(args.prefix, args.name)
    if '-' in args.name:
        code1, code2 = args.name.split('-')
        description = 'Apertium translation pair for {} and {}'.format(get_lang_name(code1), get_lang_name(code2))
    else:
        description = 'Apertium linguistic data for {}'.format(get_lang_name(args.name))

    def create_github_repository():  # type: () -> http.client.HTTPResponse
        password = getpass.getpass(prompt='GitHub Password ({}): '.format(username))
        data = bytes(json.dumps({
            'name': repository_name,
            'description': description,
        }), encoding='utf-8')
        req = urllib.request.Request('https://api.github.com/orgs/{}/repos'.format(organization_name), data=data)
        credentials = '{}:{}'.format(username, password)
        encoded_credentials = base64.b64encode(credentials.encode('ascii'))
        req.add_header('Authorization', 'Basic {}'.format(encoded_credentials.decode('ascii')))
        try:
            response = urllib.request.urlopen(req)
            print('Successfully created GitHub repository {}/{}.'.format(organization_name, repository_name))
            return response  # type: ignore
        except urllib.error.HTTPError as e:  # type: ignore
            if e.getcode() == 401:
                print('Authentication failed. Retrying...')
                return create_github_repository()
            else:
                sys.stderr.write('Failed to create GitHub repository: {}.'.format(e))
                sys.exit(-1)

    response = create_github_repository()
    body = json.loads(response.read().decode('utf-8'))

    try:
        remote_url = body['ssh_url']
        subprocess.check_output(shlex.split('git remote add {} {}'.format(remote_name, remote_url)), cwd=args.destination, stderr=subprocess.STDOUT)
        print('Added GitHub remote {}.'.format(remote_url))
    except subprocess.CalledProcessError as e:
        sys.stderr.write('Adding remote {} ({}) failed: {}'.format(remote_name, remote_url, e.output))

    try:
        subprocess.check_output(shlex.split('git push {} master'.format(remote_name)), cwd=args.destination, stderr=subprocess.STDOUT)
        print('Pushed to GitHub. Visit your new repository at {}.'.format(body['html_url']))
    except subprocess.CalledProcessError as e:
        sys.stderr.write('Pushing to remote %s failed: {}'.format(remote_name, e.output))


def main(cli_args):  # type: (List[str]) -> None
    parser = argparse.ArgumentParser(description='Bootstrap an Apertium language module/pair')
    parser.add_argument('name', help='name of new Apertium language module/pair using ISO-639-3 language code(s)')
    parser.add_argument('-d', '--destination', help='destination directory for new language module/pair (default: cwd)', default=os.getcwd())
    parser.add_argument('-p', '--push-new-to-github', help='push newly created repository to incubator on the Apertium organisation on GitHub (use with -u)',
                        action='store_true', default=False)
    parser.add_argument('-pe', '--push-existing-to-github', help='push existing repository to incubator on the Apertium organisation on GitHub', default=None)
    parser.add_argument('-u', '--username', help='override GitHub username (for pushing repository to GitHub); otherwise git config is used', default=None)
    parser.add_argument('--prefix', help='directory prefix (default: {})'.format(default_prefix), default=default_prefix)
    parser.add_argument('-r', '--rebuild', help='construct module or pair with different features using existing files',
                        action='store_true', default=False)

    parser.add_argument('-a', '--analyser', help='analyser to use for all languages', choices=['lt', 'lttoolbox', 'hfst'], default='lt')
    parser.add_argument('-a1', '--analyser1', help='analyser to use for first language of pair', choices=['lt', 'lttoolbox', 'hfst'], default='lt')
    parser.add_argument('-a2', '--analyser2', help='analyser to use for second language of pair', choices=['lt', 'lttoolbox', 'hfst'], default='lt')

    parser.add_argument('-t', '--transfer', help='structural transfer module to use', choices=['chunk', 'rtx'], default='chunk')

    rlx_prob_group1 = parser.add_mutually_exclusive_group()
    rlx_prob_group1.add_argument('--no-rlx1', help='no .rlx present in first language of pair (only used for bilingual pairs)',
                                 action='store_true', default=False)
    rlx_prob_group1.add_argument('--no-prob1', help='no .prob present in first language of pair (only used for bilingual pairs)',
                                 action='store_true', default=False)

    rlx_prob_group2 = parser.add_mutually_exclusive_group()
    rlx_prob_group2.add_argument('--no-prob2', help='no .prob present in second language of pair (only used for bilingual pairs)',
                                 action='store_true', default=False)
    rlx_prob_group2.add_argument('--no-rlx2', help='no .rlx present in second language of pair (only used for bilingual pairs)',
                                 action='store_true', default=False)

    parser.add_argument('--no-pgen1', help='no post-dix present in first language of pair (only used for bilingual pairs)', action='store_true', default=False)
    parser.add_argument('--no-pgen2', help='no post-dix present in second language of pair (only used for bilingual pairs)', action='store_true', default=False)
    parser.add_argument('--with-twoc', help='include .twoc file (only used for monolingual hfst modules)', action='store_true', default=False)
    parser.add_argument('--with-lsx', help='include apertium-separable .lsx files (only used for bilingual pairs)', action='store_true', default=False)
    parser.add_argument('--with-spellrelax', help='include spellrelax file (only used for monolingual hfst modules)', action='store_true', default=False)
    parser.add_argument('--with-anaphora', help='include anaphora resolution file (only used for bilingual pairs)', action='store_true', default=False)

    args = parser.parse_args(cli_args)

    if args.analyser in ['lt', 'lttoolbox'] and args.with_twoc:
        parser.error('--with-twoc can only be used in hfst modules')
    if args.analyser in ['lt', 'lttoolbox'] and args.with_spellrelax:
        parser.error('--with-spellrelax can only be used in hfst modules')

    try:
        email = subprocess.check_output(shlex.split('git config user.email')).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        email = default_email
        sys.stderr.write('Unable to get email, defaulting to %s: %s\n' % (email, str(e).strip()))

    username = args.username or email
    args.name = re.sub(r'^{}-'.format(re.escape(args.prefix)), '', args.name)
    repository_name = '{}-{}'.format(args.prefix, args.name)
    args.destination = os.path.join(args.destination, repository_name)

    if args.push_existing_to_github:
        if not os.path.isdir(args.push_existing_to_github):
            parser.error('--push_existing_to_github requires an existing directory')
        push_to_github(args, args.destination, username)
        return

    if '-' in args.name and args.name.count('-') == 1:
        files, replacements, conditionals = init_pair(args, email)
    elif '-' not in args.name:
        files, replacements, conditionals = init_lang_module(args, email)
    else:
        parser.error('Invalid language module name: %s' % args.name)

    if args.rebuild:
        if not os.path.exists(args.destination):
            sys.stderr.write('Directory {} does not exist, cannot rebuild, quitting.\n'.format(args.destination))
            sys.exit(-1)
        files_to_delete = []
        for filename in files:
            if filename in ['README', 'modes.xml', 'autogen.sh', 'configure.ac', 'Makefile.am']:
                continue
            if filename.endswith('.pc.in'):
                continue
            fname = make_replacements(filename, replacements, conditionals)
            if os.path.exists(os.path.join(args.destination, fname)):
                files_to_delete.append(filename)
        for filename in files_to_delete:
            del files[filename]
    elif os.path.exists(args.destination):
        sys.stderr.write('Directory {} already exists, quitting.\n'.format(args.destination))
        sys.exit(-1)
    else:
        os.makedirs(args.destination)

    make_all_replacements(args.destination, files, replacements, conditionals)

    autogen_path = os.path.join(args.destination, 'autogen.sh')
    os.chmod(autogen_path, os.stat(autogen_path).st_mode | stat.S_IEXEC)

    try:
        readme_path = os.path.join(args.destination, 'README')
        if args.rebuild:
            readme_md_path = os.path.join(args.destination, 'README.md')
            if os.path.exists(readme_md_path):
                os.remove(readme_md_path)
        if os.path.exists(readme_path):
            os.symlink('README', os.path.join(args.destination, 'README.md'))
    except OSError as err:  # e.g. on Windows without running as an admin
        sys.stderr.write('Unable to create symlink from README.md -> README: {}\n'.format(err))

    print('Successfully created %s.' % args.destination)

    try:
        subprocess.check_output(shlex.split('git init .'), cwd=args.destination, universal_newlines=True, stderr=subprocess.STDOUT)
        print('Initialized git repository {}.'.format(repository_name))
    except subprocess.CalledProcessError as e:
        sys.stderr.write('Unable to initialize git repository: {}'.format(e.output))
        sys.exit(-1)

    try:
        subprocess.check_output(shlex.split('git add .'), cwd=args.destination, universal_newlines=True, stderr=subprocess.STDOUT)
        msg = 'Rebuild with apertium-init' if args.rebuild else 'Initial commit'
        subprocess.check_output(shlex.split('git commit -m "{}"'.format(msg)), cwd=args.destination, universal_newlines=True, stderr=subprocess.STDOUT)
        print('Successfully added and committed files to git repository {}.'.format(repository_name))
    except subprocess.CalledProcessError as e:
        sys.stderr.write('Unable to add/commit files to git repository {}: {}'.format(repository_name, e.output))
        sys.exit(-1)

    if args.push_new_to_github:
        push_to_github(args, args.destination, username)
    else:
        print('To push your new local repository to incubator in the {} organisation on GitHub:'.format(organization_name))
        print('\tapertium-init.py -pe {} {}'.format(args.destination, repository_name))


if __name__ == '__main__':
    main(sys.argv[1:])
