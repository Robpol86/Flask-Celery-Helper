import ast
import atexit
from codecs import open
from distutils.spawn import find_executable
import os
import sys
import subprocess

import setuptools
import setuptools.command.sdist
from setuptools.command.test import test

HERE = os.path.abspath(os.path.dirname(__file__))
setuptools.command.sdist.READMES = tuple(list(getattr(setuptools.command.sdist, 'READMES', ())) + ['README.md'])


def get_metadata(main_file):
    """Get metadata about the package/module.

    Positional arguments:
    main_file -- python file path within `HERE` which has __author__ and the others defined as global variables.

    Returns:
    Dictionary to be passed into setuptools.setup().
    """
    with open(os.path.join(HERE, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()

    with open(os.path.join(HERE, main_file), encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.startswith('__')]
    metadata = ast.literal_eval("{'" + ", '".join([l.replace(' = ', "': ") for l in lines]) + '}')
    __author__, __license__, __version__ = [metadata[k] for k in ('__author__', '__license__', '__version__')]

    everything = dict(version=__version__, long_description=long_description, author=__author__, license=__license__)
    if not all(everything.values()):
        raise ValueError('Failed to obtain metadata from package/module.')

    return everything


class PyTest(test):
    TEST_ARGS = ['--cov-report', 'term-missing', '--cov', 'flask_celery', 'tests']

    def finalize_options(self):
        test.finalize_options(self)
        setattr(self, 'test_args', self.TEST_ARGS)
        setattr(self, 'test_suite', True)

    def run_tests(self):
        # Import here, cause outside the eggs aren't loaded.
        pytest = __import__('pytest')
        err_no = pytest.main(self.test_args)
        sys.exit(err_no)


class PyTestPdb(PyTest):
    TEST_ARGS = ['--pdb', 'tests']


class PyTestCovWeb(PyTest):
    TEST_ARGS = ['--cov-report', 'html', '--cov', 'flask_celery', 'tests']

    def run_tests(self):
        if find_executable('open'):
            atexit.register(lambda: subprocess.call(['open', os.path.join(HERE, 'htmlcov', 'index.html')]))
        PyTest.run_tests(self)


class CmdFlake(setuptools.Command):
    user_options = []
    CMD_ARGS = ['flake8', '--max-line-length', '120', '--statistics', 'flask_celery']

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.call(self.CMD_ARGS)


class CmdLint(CmdFlake):
    CMD_ARGS = ['pylint', '--max-line-length', '120', 'flask_celery']


# Setup definition.
setuptools.setup(
    name='Flask-Celery-Helper',
    description='Celery support for Flask without breaking PyCharm inspections.',

    # The project's main homepage.
    url='https://github.com/Robpol86/Flask-Celery-Helper',

    # Author details
    author_email='robpol86@gmail.com',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    # What does your project relate to?
    keywords='flask celery redis',

    py_modules=['flask_celery'],
    zip_safe=False,

    # List run-time dependencies here.  These will be installed by pip when your
    # project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/technical.html#install-requires-vs-requirements-files
    install_requires=['Flask', 'redis', 'celery'],

    tests_require=['pytest', 'pytest-cov', 'Flask-Redis-Helper'],
    cmdclass=dict(test=PyTest, testpdb=PyTestPdb, testcovweb=PyTestCovWeb, style=CmdFlake, lint=CmdLint),

    # Pass the rest from get_metadata().
    **get_metadata(os.path.join('flask_celery.py'))
)
