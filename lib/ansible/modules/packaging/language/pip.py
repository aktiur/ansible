#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Matt Wright <matt@nobien.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'core'}

DOCUMENTATION = '''
---
module: pip
short_description: Manages Python library dependencies
description:
     - "Manage Python library dependencies. To use this module, one of the following keys is required: C(name)
       or C(requirements)."
version_added: "0.7"
options:
  name:
    description:
      - The name of a Python library to install or the url(bzr+,hg+,git+,svn+) of the remote package.
      - This can be a list (since 2.2) and contain version specifiers (since 2.7).
  version:
    description:
      - The version number to install of the Python library specified in the I(name) parameter.
  requirements:
    description:
      - The path to a pip requirements file, which should be local to the remote system.
        File can be specified as a relative path if using the chdir option.
  virtualenv:
    description:
      - An optional path to a I(virtualenv) directory to install into.
        It cannot be specified together with the 'executable' parameter
        (added in 2.1).
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
    version_added: "1.0"
  virtualenv_command:
    description:
      - The command or a pathname to the command to create the virtual
        environment with. For example C(pyvenv), C(virtualenv),
        C(virtualenv2), C(~/bin/virtualenv), C(/usr/local/bin/virtualenv).
    default: virtualenv
    version_added: "1.1"
  virtualenv_python:
    description:
      - The Python executable used for creating the virtual environment.
        For example C(python3.5), C(python2.7). When not specified, the
        Python version used to run the ansible module is used. This parameter
        should not be used when C(virtualenv_command) is using C(pyvenv) or
        the C(-m venv) module.
    version_added: "2.0"
  state:
    description:
      - The state of module
      - The 'forcereinstall' option is only available in Ansible 2.1 and above.
    choices: [ absent, forcereinstall, latest, present ]
    default: present
  extra_args:
    description:
      - Extra arguments passed to pip.
    version_added: "1.0"
  editable:
    description:
      - Pass the editable flag.
    type: bool
    default: 'no'
    version_added: "2.0"
  chdir:
    description:
      - cd into this directory before running the command
    version_added: "1.3"
  executable:
    description:
      - The explicit executable or a pathname to the executable to be used to
        run pip for a specific version of Python installed in the system. For
        example C(pip-3.3), if there are both Python 2.7 and 3.3 installations
        in the system and you want to run pip for the Python 3.3 installation.
        It cannot be specified together with the 'virtualenv' parameter (added in 2.1).
        By default, it will take the appropriate version for the python interpreter
        use by ansible, e.g. pip3 on python 3, and pip2 or pip on python 2.
    version_added: "1.3"
  umask:
    description:
      - The system umask to apply before installing the pip package. This is
        useful, for example, when installing on systems that have a very
        restrictive umask by default (e.g., 0077) and you want to pip install
        packages which are to be used by all users. Note that this requires you
        to specify desired umask mode in octal, with a leading 0 (e.g., 0077).
    version_added: "2.1"
notes:
   - Please note that virtualenv (U(http://www.virtualenv.org/)) must be
     installed on the remote host if the virtualenv parameter is specified and
     the virtualenv needs to be created.
   - By default, this module will use the appropriate version of pip for the
     interpreter used by ansible (e.g. pip3 when using python 3, pip2 otherwise)
requirements:
- pip
- virtualenv
- setuptools
author:
- Matt Wright (@mattupstate)
'''

EXAMPLES = '''
# Install (Bottle) python package.
- pip:
    name: bottle

# Install (Bottle) python package on version 0.11.
- pip:
    name: bottle==0.11

# Install (bottle) python package with version specifiers
- pip:
    name: bottle>0.10,<0.20,!=0.11

# Install multi python packages with version specifiers
- pip:
    name:
      - django>1.11.0,<1.12.0
      - bottle>0.10,<0.20,!=0.11

# Install (MyApp) using one of the remote protocols (bzr+,hg+,git+,svn+). You do not have to supply '-e' option in extra_args.
- pip:
    name: svn+http://myrepo/svn/MyApp#egg=MyApp

# Install MyApp using one of the remote protocols (bzr+,hg+,git+).
- pip:
    name: git+http://myrepo/app/MyApp

# Install (MyApp) from local tarball
- pip:
    name: file:///path/to/MyApp.tar.gz

# Install (Bottle) into the specified (virtualenv), inheriting none of the globally installed modules
- pip:
    name: bottle
    virtualenv: /my_app/venv

# Install (Bottle) into the specified (virtualenv), inheriting globally installed modules
- pip:
    name: bottle
    virtualenv: /my_app/venv
    virtualenv_site_packages: yes

# Install (Bottle) into the specified (virtualenv), using Python 2.7
- pip:
    name: bottle
    virtualenv: /my_app/venv
    virtualenv_command: virtualenv-2.7

# Install (Bottle) within a user home directory.
- pip:
    name: bottle
    extra_args: --user

# Install specified python requirements.
- pip:
    requirements: /my_app/requirements.txt

# Install specified python requirements in indicated (virtualenv).
- pip:
    requirements: /my_app/requirements.txt
    virtualenv: /my_app/venv

# Install specified python requirements and custom Index URL.
- pip:
    requirements: /my_app/requirements.txt
    extra_args: -i https://example.com/pypi/simple

# Install (Bottle) for Python 3.3 specifically,using the 'pip-3.3' executable.
- pip:
    name: bottle
    executable: pip-3.3

# Install (Bottle), forcing reinstallation if it's already installed
- pip:
    name: bottle
    state: forcereinstall

# Install (Bottle) while ensuring the umask is 0022 (to ensure other users can use it)
- pip:
    name: bottle
    umask: "0022"
  become: True
'''

RETURN = '''
cmd:
  description: pip command used by the module
  returned: success
  type: string
  sample: pip2 install ansible six
name:
  description: list of python modules targetted by pip
  returned: success
  type: list
  sample: ['ansible', 'six']
requirements:
  description: Path to the requirements file
  returned: success, if a requirements file was provided
  type: string
  sample: "/srv/git/project/requirements.txt"
version:
  description: Version of the package specified in 'name'
  returned: success, if a name and version were provided
  type: string
  sample: "2.5.1"
virtualenv:
  description: Path to the virtualenv
  returned: success, if a virtualenv path was provided
  type: string
  sample: "/tmp/virtualenv"
'''

import os
import sys
import tempfile
import shlex

try:
    from pkg_resources import Requirement

    HAS_SETUPTOOLS = True
except ImportError:
    HAS_SETUPTOOLS = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils.pip import (
    setup_virtualenv, _is_vcs_url, Package, _get_packages, _recover_package_name, _get_package_info, _is_present,
    _get_pip, _fail
)

def main():
    state_map = dict(
        present=['install'],
        absent=['uninstall', '-y'],
        latest=['install', '-U'],
        forcereinstall=['install', '-U', '--force-reinstall'],
    )

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type='str', default='present', choices=state_map.keys()),
            name=dict(type='list'),
            version=dict(type='str'),
            requirements=dict(type='str'),
            virtualenv=dict(type='path'),
            virtualenv_site_packages=dict(type='bool', default=False),
            virtualenv_command=dict(type='path', default='virtualenv'),
            virtualenv_python=dict(type='str'),
            use_mirrors=dict(type='bool', default=True),
            extra_args=dict(type='str'),
            editable=dict(type='bool', default=False),
            chdir=dict(type='path'),
            executable=dict(type='path'),
            umask=dict(type='str'),
        ),
        required_one_of=[['name', 'requirements']],
        mutually_exclusive=[['name', 'requirements'], ['executable', 'virtualenv']],
        supports_check_mode=True,
    )

    if not HAS_SETUPTOOLS:
        module.fail_json(msg="No setuptools found in remote host, please install it first.")

    state = module.params['state']
    name = module.params['name']
    version = module.params['version']
    requirements = module.params['requirements']
    extra_args = module.params['extra_args']
    chdir = module.params['chdir']
    umask = module.params['umask']
    env = module.params['virtualenv']

    venv_created = False
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
        if state == 'latest' and version is not None:
            module.fail_json(msg='version is incompatible with state=latest')

        if chdir is None:
            # this is done to avoid permissions issues with privilege escalation and virtualenvs
            chdir = tempfile.gettempdir()

        err = ''
        out = ''

        if env:
            if not os.path.exists(os.path.join(env, 'bin', 'activate')):
                venv_created = True
                out, err = setup_virtualenv(module, env, chdir, out, err)

        pip = _get_pip(module, env, module.params['executable'])

        cmd = [pip] + state_map[state]

        # If there's a virtualenv we want things we install to be able to use other
        # installations that exist as binaries within this virtualenv. Example: we
        # install cython and then gevent -- gevent needs to use the cython binary,
        # not just a python package that will be found by calling the right python.
        # So if there's a virtualenv, we add that bin/ to the beginning of the PATH
        # in run_command by setting path_prefix here.
        path_prefix = None
        if env:
            path_prefix = "/".join(pip.split('/')[:-1])

        # Automatically apply -e option to extra_args when source is a VCS url. VCS
        # includes those beginning with svn+, git+, hg+ or bzr+
        has_vcs = False
        if name:
            for pkg in name:
                if pkg and _is_vcs_url(pkg):
                    has_vcs = True
                    break

            # convert raw input package names to Package instances
            packages = [Package(pkg) for pkg in _recover_package_name(name)]
            # check invalid combination of arguments
            if version is not None:
                if len(packages) > 1:
                    module.fail_json(
                        msg="'version' argument is ambiguous when installing multiple package distributions. "
                            "Please specify version restrictions next to each package in 'name' argument."
                    )
                if packages[0].has_version_specifier:
                    module.fail_json(
                        msg="The 'version' argument conflicts with any version specifier provided along with a package name. "
                            "Please keep the version specifier, but remove the 'version' argument."
                    )
                # if the version specifier is provided by version, append that into the package
                packages[0] = Package(packages[0].package_name, version)

        if module.params['editable']:
            args_list = []  # used if extra_args is not used at all
            if extra_args:
                args_list = extra_args.split(' ')
            if '-e' not in args_list:
                args_list.append('-e')
                # Ok, we will reconstruct the option string
                extra_args = ' '.join(args_list)

        if extra_args:
            cmd.extend(shlex.split(extra_args))

        if name:
            cmd.extend(to_native(p) for p in packages)
        elif requirements:
            cmd.extend(['-r', requirements])
        else:
            module.exit_json(
                changed=False,
                warnings=["No valid name or requirements file found."],
            )

        if module.check_mode:
            if extra_args or requirements or state == 'latest' or not name:
                module.exit_json(changed=True)

            pkg_cmd, out_pip, err_pip = _get_packages(module, pip, chdir)

            out += out_pip
            err += err_pip

            changed = False
            if name:
                pkg_list = [p for p in out.split('\n') if not p.startswith('You are using') and not p.startswith('You should consider') and p]

                if pkg_cmd.endswith(' freeze') and ('pip' in name or 'setuptools' in name):
                    # Older versions of pip (pre-1.3) do not have pip list.
                    # pip freeze does not list setuptools or pip in its output
                    # So we need to get those via a specialcase
                    for pkg in ('setuptools', 'pip'):
                        if pkg in name:
                            formatted_dep = _get_package_info(module, pkg, env)
                            if formatted_dep is not None:
                                pkg_list.append(formatted_dep)
                                out += '%s\n' % formatted_dep

                for package in packages:
                    is_present = _is_present(module, package, pkg_list)
                    if (state == 'present' and not is_present) or (state == 'absent' and is_present):
                        changed = True
                        break
            module.exit_json(changed=changed, cmd=pkg_cmd, stdout=out, stderr=err)

        out_freeze_before = None
        if requirements or has_vcs:
            _, out_freeze_before, _ = _get_packages(module, pip, chdir)

        rc, out_pip, err_pip = module.run_command(cmd, path_prefix=path_prefix, cwd=chdir)
        out += out_pip
        err += err_pip
        if rc == 1 and state == 'absent' and \
           ('not installed' in out_pip or 'not installed' in err_pip):
            pass  # rc is 1 when attempting to uninstall non-installed package
        elif rc != 0:
            _fail(module, cmd, out, err)

        if state == 'absent':
            changed = 'Successfully uninstalled' in out_pip
        else:
            if out_freeze_before is None:
                changed = 'Successfully installed' in out_pip
            else:
                _, out_freeze_after, _ = _get_packages(module, pip, chdir)
                changed = out_freeze_before != out_freeze_after

        changed = changed or venv_created

        module.exit_json(changed=changed, cmd=cmd, name=name, version=version,
                         state=state, requirements=requirements, virtualenv=env,
                         stdout=out, stderr=err)
    finally:
        if old_umask is not None:
            os.umask(old_umask)


if __name__ == '__main__':
    main()
