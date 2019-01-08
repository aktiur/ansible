#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Matt Wright <matt@nobien.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import sys
import operator
import re
from distutils.version import LooseVersion

from ansible.module_utils._text import to_native
from ansible.module_utils.common.file import is_executable
from ansible.module_utils.six import PY3

#: Python one-liners to be run at the command line that will determine the
# installed version for these special libraries.  These are libraries that
# don't end up in the output of pip freeze.
_SPECIAL_PACKAGE_CHECKERS = {'setuptools': 'import setuptools; print(setuptools.__version__)',
                             'pip': 'import pkg_resources; print(pkg_resources.get_distribution("pip").version)'}

_VCS_RE = re.compile(r'(svn|git|hg|bzr)\+')




op_dict = {">=": operator.ge, "<=": operator.le, ">": operator.gt,
           "<": operator.lt, "==": operator.eq, "!=": operator.ne, "~=": operator.ge}


def _is_vcs_url(name):
    """Test whether a name is a vcs url or not."""
    return re.match(_VCS_RE, name)


def _is_package_name(name):
    """Test whether the name is a package name or a version specifier."""
    return not name.lstrip().startswith(tuple(op_dict.keys()))


def _recover_package_name(names):
    """Recover package names as list from user's raw input.

    :input: a mixed and invalid list of names or version specifiers
    :return: a list of valid package name

    eg.
    input: ['django>1.11.1', '<1.11.3', 'ipaddress', 'simpleproject>1.1.0', '<2.0.0']
    return: ['django>1.11.1,<1.11.3', 'ipaddress', 'simpleproject>1.1.0,<2.0.0']

    input: ['django>1.11.1,<1.11.3,ipaddress', 'simpleproject>1.1.0,<2.0.0']
    return: ['django>1.11.1,<1.11.3', 'ipaddress', 'simpleproject>1.1.0,<2.0.0']
    """
    # rebuild input name to a flat list so we can tolerate any combination of input
    tmp = []
    for one_line in names:
        tmp.extend(one_line.split(","))
    names = tmp

    # reconstruct the names
    name_parts = []
    package_names = []
    for name in names:
        if _is_package_name(name):
            if name_parts:
                package_names.append(",".join(name_parts))
            name_parts = []
        name_parts.append(name)
    package_names.append(",".join(name_parts))
    return package_names


def _get_cmd_options(module, cmd):
    thiscmd = cmd + " --help"
    rc, stdout, stderr = module.run_command(thiscmd)
    if rc != 0:
        module.fail_json(msg="Could not get output from %s: %s" % (thiscmd, stdout + stderr))

    words = stdout.strip().split()
    cmd_options = [x for x in words if x.startswith('--')]
    return cmd_options


def _get_packages(module, pip, chdir):
    '''Return results of pip command to get packages.'''
    # Try 'pip list' command first.
    command = '%s list --format=freeze' % pip
    lang_env = {'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}
    rc, out, err = module.run_command(command, cwd=chdir, environ_update=lang_env)

    # If there was an error (pip version too old) then use 'pip freeze'.
    if rc != 0:
        command = '%s freeze' % pip
        rc, out, err = module.run_command(command, cwd=chdir)
        if rc != 0:
            _fail(module, command, out, err)

    return command, out, err


def _is_present(module, req, installed_pkgs):
    '''Return whether or not package is installed.'''
    for pkg in installed_pkgs:
        if '==' in pkg:
            pkg_name, pkg_version = pkg.split('==')
        else:
            continue

        if pkg_name.lower() == req.package_name and req.is_satisfied_by(pkg_version):
            return True

    return False


def _get_pip(module, env=None, executable=None):
    # Older pip only installed under the "/usr/bin/pip" name.  Many Linux
    # distros install it there.
    # By default, we try to use pip required for the current python
    # interpreter, so people can use pip to install modules dependencies
    candidate_pip_basenames = ('pip2', 'pip')
    if PY3:
        # pip under python3 installs the "/usr/bin/pip3" name
        candidate_pip_basenames = ('pip3',)

    pip = None
    if executable is not None:
        if os.path.isabs(executable):
            pip = executable
        else:
            # If you define your own executable that executable should be the only candidate.
            # As noted in the docs, executable doesn't work with virtualenvs.
            candidate_pip_basenames = (executable,)

    if pip is None:
        if env is None:
            opt_dirs = []
            for basename in candidate_pip_basenames:
                pip = module.get_bin_path(basename, False, opt_dirs)
                if pip is not None:
                    break
            else:
                # For-else: Means that we did not break out of the loop
                # (therefore, that pip was not found)
                module.fail_json(msg='Unable to find any of %s to use.  pip'
                                     ' needs to be installed.' % ', '.join(candidate_pip_basenames))
        else:
            # If we're using a virtualenv we must use the pip from the
            # virtualenv
            venv_dir = os.path.join(env, 'bin')
            candidate_pip_basenames = (candidate_pip_basenames[0], 'pip')
            for basename in candidate_pip_basenames:
                candidate = os.path.join(venv_dir, basename)
                if os.path.exists(candidate) and is_executable(candidate):
                    pip = candidate
                    break
            else:
                # For-else: Means that we did not break out of the loop
                # (therefore, that pip was not found)
                module.fail_json(msg='Unable to find pip in the virtualenv, %s, ' % env +
                                     'under any of these names: %s. ' % (', '.join(candidate_pip_basenames)) +
                                     'Make sure pip is present in the virtualenv.')

    return pip


def _fail(module, cmd, out, err):
    msg = ''
    if out:
        msg += "stdout: %s" % (out, )
    if err:
        msg += "\n:stderr: %s" % (err, )
    module.fail_json(cmd=cmd, msg=msg)


def _get_package_info(module, package, env=None):
    """This is only needed for special packages which do not show up in pip freeze

    pip and setuptools fall into this category.

    :returns: a string containing the version number if the package is
        installed.  None if the package is not installed.
    """
    if env:
        opt_dirs = ['%s/bin' % env]
    else:
        opt_dirs = []
    python_bin = module.get_bin_path('python', False, opt_dirs)

    if python_bin is None:
        formatted_dep = None
    else:
        rc, out, err = module.run_command([python_bin, '-c', _SPECIAL_PACKAGE_CHECKERS[package]])
        if rc:
            formatted_dep = None
        else:
            formatted_dep = '%s==%s' % (package, out.strip())
    return formatted_dep


def setup_virtualenv(module, env, chdir, out, err):
    if module.check_mode:
        module.exit_json(changed=True)

    cmd = module.params['virtualenv_command']
    if os.path.basename(cmd) == cmd:
        cmd = module.get_bin_path(cmd, True)

    if module.params['virtualenv_site_packages']:
        cmd += ' --system-site-packages'
    else:
        cmd_opts = _get_cmd_options(module, cmd)
        if '--no-site-packages' in cmd_opts:
            cmd += ' --no-site-packages'

    virtualenv_python = module.params['virtualenv_python']
    # -p is a virtualenv option, not compatible with pyenv or venv
    # this if validates if the command being used is not any of them
    if not any(ex in module.params['virtualenv_command'] for ex in ('pyvenv', '-m venv')):
        if virtualenv_python:
            cmd += ' -p%s' % virtualenv_python
        elif PY3:
            # Ubuntu currently has a patch making virtualenv always
            # try to use python2.  Since Ubuntu16 works without
            # python2 installed, this is a problem.  This code mimics
            # the upstream behaviour of using the python which invoked
            # virtualenv to determine which python is used inside of
            # the virtualenv (when none are specified).
            cmd += ' -p%s' % sys.executable

    # if venv or pyvenv are used and virtualenv_python is defined, then
    # virtualenv_python is ignored, this has to be acknowledged
    elif module.params['virtualenv_python']:
        module.fail_json(
            msg='virtualenv_python should not be used when'
                ' using the venv module or pyvenv as virtualenv_command'
        )

    cmd = "%s %s" % (cmd, env)
    rc, out_venv, err_venv = module.run_command(cmd, cwd=chdir)
    out += out_venv
    err += err_venv
    if rc != 0:
        _fail(module, cmd, out, err)
    return out, err


class Package:
    """Python distribution package metadata wrapper.

    A wrapper class for Requirement, which provides
    API to parse package name, version specifier,
    test whether a package is already satisfied.
    """

    def __init__(self, name_string, version_string=None):
        self._plain_package = False
        self.package_name = name_string
        self._requirement = None

        if version_string:
            version_string = version_string.lstrip()
            separator = '==' if version_string[0].isdigit() else ' '
            name_string = separator.join((name_string, version_string))
        try:
            self._requirement = Requirement.parse(name_string)
            # old pkg_resource will replace 'setuptools' with 'distribute' when it already installed
            if self._requirement.project_name == "distribute":
                self.package_name = "setuptools"
            else:
                self.package_name = self._requirement.project_name
            self._plain_package = True
        except ValueError as e:
            pass

    @property
    def has_version_specifier(self):
        if self._plain_package:
            return bool(self._requirement.specs)
        return False

    def is_satisfied_by(self, version_to_test):
        if not self._plain_package:
            return False
        try:
            return self._requirement.specifier.contains(version_to_test)
        except AttributeError:
            # old setuptools has no specifier, do fallback
            version_to_test = LooseVersion(version_to_test)
            return all(
                op_dict[op](version_to_test, LooseVersion(ver))
                for op, ver in self._requirement.specs
            )

    def __str__(self):
        if self._plain_package:
            return to_native(self._requirement)
        return self.package_name
