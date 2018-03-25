import attr
import toml

import codecs
import json
import hashlib
import platform
import sys
import os


def format_full_version(info):
    version = '{0.major}.{0.minor}.{0.micro}'.format(info)
    kind = info.releaselevel
    if kind != 'final':
        version += kind[0] + str(info.serial)
    return version



class PipfileParser(object):
    def __init__(self, filename='Pipfile'):
        self.filename = filename
        self.sources = []
        self.groups = {
            'default': [],
            'develop': []
        }
        self.group_stack = ['default']
        self.requirements = []

    def __repr__(self):
        return '<PipfileParser path={0!r}'.format(self.filename)

    def inject_environment_variables(self, d):
        """
        Recursively injects environment variables into TOML values
        """

        if not d:
            return d

        for k, v in d.items():
            if isinstance(v, str):
                d[k] = os.path.expandvars(v)
            elif isinstance(v, dict):
                d[k] = self.inject_environment_variables(v)
            elif isinstance(v, list):
                d[k] = [self.inject_environment_variables(e) for e in v]

        return d

    def parse(self):
        # Open the Pipfile.
        with open(self.filename) as f:
            content = f.read()

        # Load the default configuration.
        default_config = {
            u'source': [{u'url': u'https://pypi.python.org/simple', u'verify_ssl': True, 'name': "pypi"}],
            u'packages': {},
            u'requires': {},
            u'dev-packages': {}
        }

        config = {}
        config.update(default_config)

        # Deserialize the TOML, and parse for Environment Variables
        parsed_toml = self.inject_environment_variables(toml.loads(content))

        # Load the Pipfile's configuration.
        config.update(parsed_toml)

        # Structure the data for output.
        data = {
            '_meta': {
                'sources': config['source'],
                'requires': config['requires']
            },
        }

        # TODO: Validate given data here.
        self.groups['default'] = config['packages']
        self.groups['develop'] = config['dev-packages']

        # Update the data structure with group information.
        data.update(self.groups)
        return data


@attr.s(frozen=True)
class Source(object):
    #: URL to PyPI instance
    url = attr.ib(default='')
    #: If False, skip SSL checks
    verify_ssl = attr.ib(default=True, validator=attr.validators.optional(attr.validators.instance_of(bool)))
    #: human name to refer to this source (can be referenced in packages or dev-packages)
    name = attr.ib(default='')

_optional_instance_of = lambda cls: attr.validators.optional(attr.validators.instance_of(cls))


@attr.s(frozen=True)
class Requires(object):
    """System-level requirements - see PEP508 for more detail"""
    os_name = attr.ib(default=None)
    sys_platform = attr.ib(default=None)
    platform_machine = attr.ib(default=None)
    platform_python_implementation = attr.ib(default=None)
    platform_release = attr.ib(default=None)
    platform_system = attr.ib(default=None)
    platform_version = attr.ib(default=None)
    python_version = attr.ib(default=None)
    python_full_version = attr.ib(default=None)
    implementation_name = attr.ib(default=None)
    implementation_version = attr.ib(default=None)

@attr.s(frozen=True)
class VCSRequirement(object):
    #: vcs reference name (branch / commit / tag)
    ref = attr.ib(default=None)
    #: path to hit - without any of the VCS prefixes (like git+ / http+ / etc)
    uri = attr.ib(default=None)
    subdirectory = attr.ib(default=None)




@attr.s(frozen=True)
class PackageRequirement(object):
    #: pypi name (internally normalized via something like, e.g., pkg_resources.safe_name)
    name = attr.ib(default=None)
    #: extra requirements - see pip / setuptools docs for more
    extras = attr.ib(default=tuple(),
                     validator=_optional_instance_of(tuple))
    specs = attr.ib(default=None)
    editable = attr.ib(default=False)
    vcs = attr.ib(default=None,
                  validator=_optional_instance_of(VCSRequirement))
    # "specs" in pip requirement
    version = attr.ib(default=None)


@attr.s(frozen=True)
class RequirementSet(object):
    packages = attr.ib(validator=_optional_instance_of(PackageRequirement))


class Pipfile(object):
    #: source filename
    filename = attr.ib()
    sources = attr.ib(validator=iterable_of(Source))
    packages = attr.ib(validator=_optional_instance_of(RequirementSet))
    dev_packages = attr.ib(validator=_optional_instance_of(RequirementSet))


def load(pipfile_path=None):
    """Loads a pipfile from a given path.
    If none is provided, one will try to be found.
    """

    if pipfile_path is None:
        pipfile_path = Pipfile.find()

    return Pipfile.load(filename=pipfile_path)
