# How to contribute

Thanks for asking! We graciously accept PRs, assuming they meet quality standards and align with the direction of the project. If they don't, we'll do our best to help you understand what to modify in order to merge.

## Setting up your environment

1) Install pipenv and Python 3.7 if not already installed
2) `git clone git@github.com:browsertron/pytest-parallel.git`
3) `cd pytest-parallel`
4) `pipenv install --dev`
5) `pipenv run test` - if this fails due to missing Python versions, see Testing below.

Congrats! You should have a working dev environment now.

## Testing

No PR will be merged without tests or test modifications unless the PR is a non-functional change (docs, text, etc). We test across Python versions using tox (listed in `tox.ini`). If you're missing a Python version, we recommend `pyenv` to install the versions you need.

Assuming you've set up your environment, you can run `pipenv run test` to run the tests.

## Installing pyenv on OSX

1) `brew install pyenv`
2) `pyenv init` - this prompts you to add to `~/.bash_profile`
3) `pyenv install x.x.x`
4) `pyenv local 3.6.x 3.7.x 3.x.x ...` to set the patch version for each minor version
5) Ensure that running `python3.6` starts a REPL and doesn't list available versions

## Building

Build a wheel with `pipenv run build`

## Releasing to PyPI

1) Install twine if not already installed
2) Checkout the master branch
3) Ensure your branch is up-to-date
4) Change \_\_version__ in pytest_parallel/\_\_init__.py
5) `pipenv run release`
