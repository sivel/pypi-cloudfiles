#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2013 Matt Martz
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import re
import sys
import pyrax
import StringIO
import ConfigParser

from collections import defaultdict


def guess_pkgname(path):
    path = os.path.basename(path).replace('.tar.gz', '')
    if '-' not in path:
        pkgname = path
    elif path.count('-') == 1:
        pkgname = path.split('-', 1)[0]
    elif '.' not in path:
        pkgname = path.rsplit('-', 1)[0]
    else:
        parts = re.split(r'-(?=(?i)v?\d+[\.a-z])', path)
        pkgname = '-'.join(parts[:-1])
    return pkgname


def set_sys_argv():
    sys.argv = sys.argv[1:]


def set_paths():
    setup_py_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(setup_py_dirname)
    sys.path.insert(0, setup_py_dirname)


def check_args():
    upload_index = sys.argv.index('upload')
    if upload_index:
        try:
            dash_r_index = sys.argv.index('-r')
        except ValueError:
            raise SystemExit('-r is required')
        else:
            try:
                env = sys.argv[dash_r_index + 1]
            except IndexError:
                raise SystemExit('-r requires an environment')

        del sys.argv[dash_r_index + 1]
        del sys.argv[dash_r_index]
        del sys.argv[upload_index]

        return env
    return False


def include_setup_py():
    sys_stdout = sys.stdout
    sys_stderr = sys.stderr
    sys.stdout = StringIO.StringIO()
    sys.stderr = StringIO.StringIO()

    try:
        __import__(os.path.basename(sys.argv[0]).replace('.py', ''))
    except ImportError:
        sys.stdout.close()
        sys.stdout = sys_stdout
        raise SystemExit('Cannot find %s' % sys.argv[0])
    except Exception as e:
        sys.stdout.close()
        sys.stdout = sys_stdout
        raise SystemExit('%s' % e)

    stdout = sys.stdout.getvalue()
    stderr = sys.stderr.getvalue()
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = sys_stdout
    sys.stderr = sys_stderr

    if stdout:
        print stdout
    if stderr:
        print stderr

    return stdout


def do_upload(env, stdout):
    defaults = dict(repository='pypi')

    config = ConfigParser.RawConfigParser(defaults)
    config.read(os.path.expanduser('~/.pypirc'))

    username = config.get(env, 'username')
    api_key = config.get(env, 'password')
    repository = os.path.basename(config.get(env, 'repository').rstrip('/'))

    pyrax.set_setting('identity_type', 'rackspace')
    pyrax.set_credentials(username, api_key)

    cf = pyrax.cloudfiles
    try:
        cont = cf.get_container(repository)
    except pyrax.exceptions.NoSuchContainer:
        cont = cf.create_container(repository)

    cont.make_public(ttl=900)
    cont.set_web_index_page('index.html')

    creates = re.findall(r'creating (\S+)', stdout)
    package = os.path.abspath(os.path.join('dist', '%s.tar.gz' % creates[0]))

    filename = os.path.basename(package)

    print 'running upload'
    print 'Submitting dist/%s to %s' % (filename, cont.cdn_uri)
    cont.upload_file(package, return_none=True,
                     obj_name='packages/%s' % filename)

    objs = cont.get_objects(prefix='packages/', delimiter='/',
                            full_listing=True)
    packages = []
    for pkg in objs:
        if pkg.name.endswith('.tar.gz'):
            packages.append(pkg)

    return cont, packages


def build_indexes(cont, packages):
    print 'Creating static index pages'

    header = """<html><head>
<title>%(title)s</title>
</head><body>
<h1>%(title)s</h1>"""

    footer = """</body></html>"""

    main = """
<p>This is a PyPI compatible package index serving %(count)s packages.</p>

<p> To use this server with pip, run the the following command:
<blockquote><pre>
pip install -i %(url)s/simple/ PACKAGE [PACKAGE2...]
</pre></blockquote></p>

<p> To use this server with easy_install, run the the following command:
<blockquote><pre>
easy_install -i %(url)s/simple/ PACKAGE
</pre></blockquote></p>

<p>The complete list of all packages can be found <a href="/packages/">here</a>
or via the <a href="/simple/">simple</a> index.</p>
"""

    cont.store_object('index.html',
                      '%s%s%s' % (header % dict(title='Welcome to '
                                                      'pypi-cloudfiles!'),
                                  main % dict(count=len(packages),
                                              url=cont.cdn_uri),
                                  footer))

    pkg_list = []
    pkgs = defaultdict(set)
    for pkg in packages:
        pkg_list.append('<a href="/%s">%s</a><br>' %
                        (pkg.name, os.path.basename(pkg.name)))
        pkgs[guess_pkgname(os.path.basename(pkg.name))].add(pkg.name)

    cont.store_object('packages/index.html',
                      '%s%s%s' % (header % dict(title='Index of packages'),
                                  '\n'.join(pkg_list),
                                  footer))

    all_pkg_list = []
    for pkg, full_pkgs in pkgs.items():
        single_pkg_list = []
        for full_pkg in full_pkgs:
            single_pkg_list.append('<a href="/%s">%s</a><br>' %
                                   (full_pkg, os.path.basename(full_pkg)))
        all_pkg_list.append('<a href="/simple/%s/">%s</a><br>' % (pkg, pkg))

        cont.store_object('simple/%s/index.html' % pkg,
                          '%s%s%s' % (header % dict(title='Links for %s' %
                                                          pkg),
                                      '\n'.join(single_pkg_list),
                                      footer))
    cont.store_object('simple/index.html',
                      '%s%s%s' % (header % dict(title='Simple Index'),
                                  '\n'.join(all_pkg_list),
                                  footer))


def main():
    set_sys_argv()
    set_paths()
    env = check_args()
    stdout = include_setup_py()
    if env:
        cont, packages = do_upload(env, stdout)
        if packages:
            build_indexes(cont, packages)


if __name__ == '__main__':
    main()
