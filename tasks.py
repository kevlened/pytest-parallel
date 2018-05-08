from invoke import task
from codecs import open
from os import path
import shutil
import re

with open(path.join('pytest_parallel', '__init__.py'), encoding='utf-8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


@task
def test(c):
    c.run('tox')


@task
def build(c):
    shutil.rmtree('build')
    shutil.rmtree('dist')
    shutil.rmtree('pytest_parallel.egg-info')
    c.run('python setup.py sdist bdist_wheel')


@task
def release(c):
    test(c)
    build(c)
    c.run('git commit -am {}'.format(version))
    c.run('git tag {}'.format(version))
    c.run('git push')
    c.run('git push --tags')
    c.run('twine upload dist/*')
