======
audeer
======

|tests| |coverage| |docs| |python-versions| |license| 

The Python package **audeer** collects small tools and functions
that deal with common tasks.
For example, it incorporates functions for handling file paths,
using multi-threading, or showing progress bars.

The package is lightweight,
and has the small tqdm_ package
as it's only external dependency.

Have a look at the installation_ and usage_ instructions as a starting point.

Code example,
that lists all WAV files in the ``data`` folder:

.. code-block:: python

    import audeer

    files = audeer.list_file_names('data', filetype='wav')


.. _tqdm: https://tqdm.github.io/
.. _installation: https://audeering.github.io/audeer/installation.html
.. _usage: https://audeering.github.io/audeer/usage.html

.. badges images and links:
.. |tests| image:: https://github.com/audeering/audeer/workflows/Test/badge.svg
    :target: https://github.com/audeering/audeer/actions?query=workflow%3ATest
    :alt: Test status
.. |coverage| image:: https://codecov.io/gh/audeering/audeer/branch/main/graph/badge.svg?token=PUA9P2UJW1
    :target: https://codecov.io/gh/audeering/audeer
    :alt: code coverage
.. |docs| image:: https://img.shields.io/pypi/v/audeer?label=docs
    :target: https://audeering.github.io/audeer/
    :alt: audeer's documentation
.. |license| image:: https://img.shields.io/badge/license-MIT-green.svg
    :target: https://github.com/audeering/audeer/blob/main/LICENSE
    :alt: audeer's MIT license
.. |python-versions| image:: https://img.shields.io/pypi/pyversions/audeer.svg
    :target: https://pypi.org/project/audeer/
    :alt: audeer's supported Python versions
