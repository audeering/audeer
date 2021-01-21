Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_,
and this project adheres to `Semantic Versioning`_.


Version 1.9.0 (2021-01-21)
--------------------------

* Added: ``audeer.list_dir_names()``


Version 1.8.0 (2020-12-03)
--------------------------

* Added: :func:`audeer.is_uid`


Version 1.7.0 (2020-12-02)
--------------------------

* Added: :func:`audeer.deprecated_keyword_argument` decorator
* Changed: :func:`audeer.deprecated` raises now a ``UserWarning``
  instead of ``DeprecationWarning``


Version 1.6.7 (2020-11-18)
--------------------------

* Changed: return member filenames of archives in
  :func:`audeer.extract_archive`
  and :func:`audeer.extract_archives`


Version 1.6.6 (2020-10-27)
--------------------------

* Fixed: multi-line statements in Github releases


Version 1.6.5 (2020-10-27)
--------------------------

* Fixed: long description in ``setup.cfg``,
  which is included on pypi.org
* Fixed: multi-line statements in Github releases


Version 1.6.4 (2020-10-23)
--------------------------

* Added: run tests on Windows
* Removed: deprecated :func:`audb.run_worker_threads` from docs
  and code coverage
* Fixed: "Edit on Github" link in docs


Version 1.6.3 (2020-10-22)
--------------------------

* Fixed: release instructions for Github


Version 1.6.2 (2020-10-21)
--------------------------

* Changed: host documentation on Github pages


Version 1.6.1 (2020-10-20)
--------------------------

* Fixed: license specification in Python package


Version 1.6.0 (2020-10-20)
--------------------------

* Added: first public release on Github


Version 1.5.1 (2020-09-28)
--------------------------

* Fixed: return actual path for symbolic links with :func:`audeer.safe_path`
  by using :func:`os.path.realpath` instead of :func:`os.path.abspath`
* Fixed: clean up test scripts and remove obsolete :file:`tests/test_audeer.py`


Version 1.5.0 (2020-09-22)
--------------------------

* Added: :func:`audeer.common_directory`


Version 1.4.0 (2020-09-21)
--------------------------

* Added: :func:`audeer.run_tasks`


Version 1.3.0 (2020-09-08)
--------------------------

* Added: :func:`audeer.uid`


Version 1.2.3 (2020-09-01)
--------------------------

* Changed: use ``url`` and ``project_urls`` in :file:`setup.cfg`


Version 1.2.2 (2020-08-28)
--------------------------

* Changed: switch home page of package to documentation page


Version 1.2.1 (2020-08-18)
--------------------------

* Changed: :func:`audb.extract_archive` raises ``RuntimeError`` for broken
    archives


Version 1.2.0 (2020-08-14)
--------------------------

* Added: :func:`audb.extract_archive`
* Added: :func:`audb.extract_archives`
* Added: Python 3.8 support
* Removed: Python 3.5 support


Version 1.1.2 (2020-06-12)
--------------------------

* Fixed: wrong homepage link in :file:`setup.cfg`


Version 1.1.1 (2020-05-20)
--------------------------

* Added: ``mode`` argument to :func:`audeer.mkdir`


Version 1.1.0 (2020-04-08)
--------------------------

* Added: :func:`audeer.to_list`
* Added: code coverage
* Removed: deprecated :func:`audeer.generate_dir`
* Removed: deprecated :func:`audeer.basename`


Version 1.0.7 (2020-02-19)
--------------------------

* Fixed: CI again token for automatic package publishing


Version 1.0.6 (2020-02-19)
--------------------------

* Fixed: CI token for automatic package publishing


Version 1.0.5 (2020-02-19)
--------------------------

* Fixed: make :func:`audeer.mkdir` multiprocessing safe


Version 1.0.4 (2020-02-07)
--------------------------

* Fixed: republish due to broken package


Version 1.0.3 (2020-02-07)
--------------------------

* Added: more docstring examples
* Changed: add extra development section in docs


Version 1.0.2 (2020-02-07)
--------------------------

* Added: automatic Python package publishing
* Fixed: another link to `audeer.configfile`_


Version 1.0.1 (2020-02-06)
--------------------------

* Fixed: link to `audeer.configfile`_


Version 1.0.0 (2020-02-06)
--------------------------

* Added: :func:`audeer.format_display_message`
* Added: :func:`audeer.progress_bar`
* Added: :func:`audeer.deprecated`
* Added: :func:`audeer.run_worker_threads`
* Added: :func:`audeer.safe_path`
* Changed: introduce `audeer.core` structure
* Changed: rename :func:`audeer.generate_dir` to :func:`audeer.mkdir`
* Changed: rename :func:`basename` to :func:`basename_wo_ext`
* Removed: all config related code is moved to `audeer.configfile`_
* Removed: Python 2.7 support


Version 0.9.3 (2019-08-16)
--------------------------

* Changed: update installation commands in doc
* Changed: update documentation building commands in doc


Version 0.9.2 (2019-08-16)
--------------------------

* Fixed: Gitlab CI tests for Python 3.7


Version 0.9.1 (2019-08-13)
--------------------------

* Added: tests for documentation
* Added: documentation deployed as Gitlab pages
* Fixed: inclusion of changelog in doc


Version 0.9.0 (2019-06-27)
--------------------------

* Added: Gitlab CI tests for Python 2.7, 3.6, 3.7
* Added: flake8 PEP8 tests
* Changed: switch to new internal PyPI server
* Changed: switch to use ``yaml.safe_load``
* Fixed: ``generate_dir`` for Python 2.7
* Removed: ``audeer.wav`` in favor of audiofile_


Version 0.8.0 (2019-04-04)
--------------------------

* Deprecated: ``audeer.wav`` in favor of audiofile_


Version 0.7.2 (2019-03-05)
--------------------------

* Added: missing requirement toml to ``doc/requirements.txt``


Version 0.7.1 (2019-03-05)
--------------------------

* Fixed: URL to sphinx-audeering-theme in ``doc/requirements.txt``


Version 0.7.0 (2019-03-01)
--------------------------

* Added: ``always_2d`` option to ``wav.read``
* Removed: ``wav.to_mono``


Version 0.6.2 (2019-02-21)
--------------------------

* Added: support for subdirectories in ``generate_dir``
* Changed: speedup ``wav`` operations
* Deprecated: ``wav.to_mono``


Version 0.6.1 (2019-02-08)
--------------------------

* Fixed: samples and duration for uncommon audio formats


Version 0.6.0 (2019-02-08)
--------------------------

* Added: support for a lot more audio formats in ``wav``


Version 0.5.0 (2019-02-05)
--------------------------

* Added: ``util.flatten_list``
* Changed: improve documentation


Version 0.4.0 (2019-01-07)
--------------------------

* Added: MP3 support (not for writing)
* Changed: make ``[channels, samples]`` default audio shape
* Changed: switch to sox_ for audio file info


Version 0.3.0 (2018-11-16)
--------------------------

* Changed: make Python 2.7 compatible
* Changed: restructure config module


Version 0.2.0 (2018-11-12)
--------------------------

* Added: ``config`` module


Version 0.1.1 (2018-10-29)
--------------------------

* Fixed: automatic version discovery


Version 0.1.0 (2018-10-29)
--------------------------

* Added: ``wav`` and ``util`` module
* Added: Initial release


.. _Keep a Changelog: https://keepachangelog.com/en/1.0.0/
.. _Semantic Versioning: https://semver.org/spec/v2.0.0.html
.. _audiofile: https://github.com/audeering/audiofile
.. _sox: https://github.com/rabitt/pysox
.. _audeer.configfile: http://tools.pp.audeering.com/pyaudeer-configfile
