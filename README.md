# pytest-parallel
a pytest plugin for parallel and concurrent testing

## What?

This plugin makes it possible to run tests quickly using multiprocessing (parallelism) and multithreading (concurrency).

## Why?

`pytest-xdist` is great to run tests that:
  1. aren't threadsafe
  2. perform poorly when multithreaded
  3. need state isolation

`pytest-parallel` is better for some use cases (like Selenium tests) that:
  1. can be threadsafe
  2. can use non-blocking IO for http requests to make it performant
  3. manage little or no state in the Python environment

Put simply, `pytest-xdist` does parallelism while `pytest-parallel` does parallelism and concurrency.

## Requirements

* Python3 version [3.6+]
* Unix or Mac for `--workers`
* Unix, Mac, or Windows for `--tests-per-worker`

## Installation

`pip install pytest-parallel`

## Options

* `workers` (optional) - max workers (aka processes) to start. Can be a **positive integer or `auto`** which uses one worker per core. **Defaults to 1**.
* `tests-per-worker` (optional) - max concurrent tests per worker. Can be a **positive integer or `auto`** which evenly divides tests among the workers up to 50 concurrent tests. **Defaults to 1**.

## Examples

```bash
# runs 2 workers with 1 test per worker at a time
pytest --workers 2

# runs 4 workers (assuming a quad-core machine) with 1 test per worker
pytest --workers auto

# runs 1 worker with 4 tests at a time
pytest --tests-per-worker 4

# runs 1 worker with up to 50 tests at a time
pytest --tests-per-worker auto

# runs 2 workers with up to 50 tests per worker
pytest --workers 2 --tests-per-worker auto
```

## Notice

Beginning with Python 3.8, forking behavior is forced on macOS at the expense of safety.

    Changed in version 3.8: On macOS, the spawn start method is now the default. The fork start method should be considered unsafe as it can lead to crashes of the subprocess. See bpo-33725.

[Source](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods)

## License

MIT
