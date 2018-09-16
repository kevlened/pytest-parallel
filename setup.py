from setuptools import setup
from codecs import open
from os import path
import re

# Get the long description from the README file
with open(path.join('README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version from the module
with open(path.join('pytest_parallel', '__init__.py'), encoding='utf-8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

# Get the install_requires from the Pipfile
with open(path.join('Pipfile'), encoding='utf-8') as f:
    pkgs = re.search(r'^\[packages\]([^\[]*)', f.read(), re.M).group(1).strip()
    pkg_pattern = re.compile(r'"?(.*?)"? = ["\'](.*?)["\']')
    install_requires = [name if version == '*' else name + version
                        for (name, version)
                        in re.findall(pkg_pattern, pkgs)]

setup(
    name='pytest-parallel',
    version=version,
    license='MIT',
    description='a pytest plugin for parallel and concurrent testing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/browsertron/pytest-parallel',
    author='Browsertron',
    author_email='team@browsertron.com',

    include_package_data=True,
    install_requires=install_requires,
    packages=['pytest_parallel'],
    entry_points={
        'pytest11': [
            'parallel = pytest_parallel',
        ]
    },

    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Framework :: Pytest',

        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
