#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Arthur Cheysson <arthur@cheysson.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: pipenv
short_description: Manages Python library dependencies using pipenv
description:
     - "Manage Python library dependencies with pipenv. To use this module, the following key is necessary:
       C(directory)."
version_added: "0.1"
options:
  path:
    description:
      - The path of the directory where the Pipfile and Pipfile.lock are located.
  include_dev:
    description:
      - A boolean describing whether to also install dev dependencies
  fail_when_lockfile_outdated:
    description:
      - Whether to fail when the Pipfile.lock is out-of-date (as compared with
        the Pipfile)
  virtualenv:
    description:
      - An optional path to a I(virtualenv) directory to install into.
        If the virtualenv does not exist, it will be created before installing
        packages. The optional virtualenv_site_packages, virtualenv_command,
        and virtualenv_python options affect the creation of the virtualenv.
  virtualenv_site_packages:
    description:
      - Whether the virtual environment will inherit packages from the
        global site-packages directory.  Note that if this setting is
        changed on an already existing virtual environment it will not
        have any effect, the environment must be deleted and newly
        created.
    type: bool
    default: "no"
    version_added: "0.1"
  virtualenv_command:
    description:
      - The command or a pathname to the command to create the virtual
        environment with. For example C(pyvenv), C(virtualenv),
        C(virtualenv2), C(~/bin/virtualenv), C(/usr/local/bin/virtualenv).
    default: virtualenv
    version_added: "0.1"
  virtualenv_python:
    description:
      - The Python executable used for creating the virtual environment.
        For example C(python3.5), C(python2.7). When not specified, the
        Python version used to run the ansible module is used. This parameter
        should not be used when C(virtualenv_command) is using C(pyvenv) or
        the C(-m venv) module.
    version_added: "0.0"
  executable:
    description:
      - The explicit executable or a pathname to the executable to be used to
        run pipenv for a specific version of Python installed in the system. For
        example C(/path/to/virtualenv/bin/pipenv), if you want to execute it from a
        virtualenv.
        It cannot be specified together with the 'virtualenv' parameter (added in 2.1)..
    version_added: "0.1"
  umask:
    description:
      - The system umask to apply before installing the pip package. This is
        useful, for example, when installing on systems that have a very
        restrictive umask by default (e.g., 0077) and you want to pip install
        packages which are to be used by all users. Note that this requires you
        to specify desired umask mode in octal, with a leading 0 (e.g., 0077).
    version_added: "0.1"
notes:
   - Please note that virtualenv (U(http://www.virtualenv.org/)) must be
     installed on the remote host if the virtualenv parameter is specified and
     the virtualenv needs to be created.
requirements:
- pipenv
- virtualenv
- setuptools
author:
- Arthur Cheysson
'''

EXAMPLES = '''
# Install packages from Pipfile.lock
- pip:
    path: /path/to/project/
'''

RETURN = '''
cmd:
  description: pipenv command used by the module
  returned: success
  type: string
  sample: "pipenv sync"
path:
  description: path
  returned: success
  type: list
  sample: "/path/to/project"
virtualenv:
  description: Path to the virtualenv
  returned: success, if a virtualenv path was provided
  type: string
  sample: "/tmp/virtualenv"
'''

import os
import re
import sys
import tempfile
import operator
import shlex
from distutils.version import LooseVersion

try:
    from pkg_resources import Requirement

    HAS_SETUPTOOLS = True
except ImportError:
    HAS_SETUPTOOLS = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pip import setup_virtualenv, _get_pip, _get_packages, _is_present, _fail
from ansible.module_utils._text import to_native


def _get_pipenv(module, env, executable):
    if env:
        return os.path.join(env, 'bin/pipenv')

    candidate_name = 'pipenv'

    if executable:
        if os.path.abspath(executable):
            return executable
        else:
            candidate_name = executable

    pipenv = module.get_bin_path(candidate_name)
    if pipenv is None:
        module.fail_json(msg='Unable to find %s. pipenv'
                             ' needs to be installed.' % ', '.join(candidate_name))

    return pipenv


def has_changes(module, lockfile, pip):
    return True


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='path'),
            include_dev=dict(type='bool', default=False),
            fail_when_lockfile_outdated=dict(type='bool', default=True),
            virtualenv=dict(type='path'),
            virtualenv_site_packages=dict(type='bool', default=False),
            virtualenv_command=dict(type='path', default='virtualenv'),
            virtualenv_python=dict(type='str'),
            chdir=dict(type='path'),
            executable=dict(type='path'),
            umask=dict(type='str'),
        ),
        required_one_of=['path'],
        mutually_exclusive=[['executable', 'virtualenv']],
    )

    if not HAS_SETUPTOOLS:
        module.fail_json(msg="No setuptools found in remote host, please install it first.")

    path = module.params['path']
    include_dev = module.params['include_dev']
    fail_when_lockfile_outdated = module.params['fail_when_lockfile_outdated']
    umask = module.params['umask']
    env = module.params['virtualenv']
    chdir = module.params['chdir']
    executable = module.params['executable']

    venv_created = False
    pipenv_installed = False
    ran_pipenv = False
    cmd = None

    if env and chdir:
        env = os.path.join(chdir, env)

    if umask and not isinstance(umask, int):
        try:
            umask = int(umask, 8)
        except Exception:
            module.fail_json(msg="umask must be an octal integer",
                             details=to_native(sys.exc_info()[1]))

    old_umask = None
    if umask is not None:
        old_umask = os.umask(umask)

    try:
        if chdir is None:
            # this is done to avoid permissions issues with privilege escalation and virtualenvs
            chdir = tempfile.gettempdir()

        err = ''
        out = ''

        if env:
            if not os.path.exists(os.path.join(env, 'bin', 'activate')):
                venv_created = True
                out, err = setup_virtualenv(module, env, chdir, out, err)

        pip = _get_pip(module, env, chdir)
        packages = _get_packages(module, pip, chdir)

        if not _is_present(module, 'pipenv', packages) and env:
            pipenv_installed = True
            rc, out_pip, err_pip = module.run_command(['pip', 'install', 'pipenv'])

            out += out_pip
            err += err_pip

            if rc != 0:
                _fail(module, ['pip', 'install', 'pipenv'], out, err)

        if has_changes(module, os.path.join(path, 'Pipfile.lock'), pip):
            pipenv = _get_pipenv(module, env, executable)

            cmd = [pipenv, 'sync']

            if env:
                os.environ['VIRTUAL_ENV'] = env
            rc, out_pipenv, err_pipenv = module.run_command(cmd, cwd=path, )
            ran_pipenv = True

            out += out_pipenv
            err += err_pipenv

            if rc != 0:
                _fail(module, cmd, out, err)

        changed = venv_created or pipenv_installed or ran_pipenv

        module.exit_json(changed=changed, cmd=cmd, path=path, virtualenv=env, stdout=out, stderr=err)

    finally:
        if old_umask is not None:
            os.umask(old_umask)


if __name__ == '__main__':
    main()