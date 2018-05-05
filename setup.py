from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pytest-parallel',
    version='0.0.1',
    license='MIT',
    description='a py.test plugin for parallel and concurrent testing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/browsertron/pytest-parallel',
    author='Browsertron',
    author_email='team@browsertron.com',

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

    packages=find_packages(),
    install_requires=['pytest>=3.0.0'],
)
