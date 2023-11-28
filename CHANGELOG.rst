Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_,
and this project adheres to `Semantic Versioning`_.


Version 1.20.2 (2023-11-28)
---------------------------

* Added: support for Python 3.12
* Fixed: avoid deprecation warning
  by replacing
  ``pkg_resources``
  internally with
  ``importlib.metadata``
* Removed: support for Python 3.7


Version 1.20.1 (2023-05-04)
---------------------------

* Fixed: add missing changelog entry
  for version 1.20.0
  stating that the return values of
  ``audeer.extract_archive()``
  and ``audeer.extract_archives()``
  have changed under Windows
  due to a bug fix


Version 1.20.0 (2023-05-02)
---------------------------

* Added: ``audeer.md5()`` to calculate MD5 checksum
  of a file or folder
* Added: ``short`` argument to ``audeer.is_uid()``.
  If ``True`` it checks for a short UID
  like ``ad855840``
* Added: examples to the API documentation of
  ``audeer.create_archive()``,
  ``audeer.extract_archive()``,
  ``audeer.extract_archives()``
* Changed: ``audeer.list_file_names()``
  raises a ``NotADirectoryError``
  if the provided ``path`` argument
  is a non-existing folder
  or a folder that is part
  of a search pattern
  that does not exists
* Changed: ``audeer.create_archive()``
  supports now ``None`` as ``files`` argument,
  which will automatically include all files under ``root``
* Changed: ``audeer.create_archive()``
  now raises a ``FileNotFoundError``
  if ``root`` or a file in ``files`` cannot be found,
  ``NotADirectoryError``
  if ``root`` is not a directory,
  ``RuntimeError``
  if a file in ``files``
  is not located below ``root``
* Changed: ``audeer.extract_archive()``
  and ``audeer.extract_archives()``
  now raise a ``FileNotFoundError``
  if an archive cannot be found,
  ``IsADirectoryError``
  if an archive is a directory,
  ``NotADirectoryError``
  if ``destination`` is not a directory
* Fixed: ``audeer.replace_file_extension()``
  now adds the new file extension to the filename
  if no original file extension was present
  instead of replacing the filename
* Fixed: ``audeer.replace_file_extension()``
  now returns the original filename
  when an empty new file extension is provided
  instead of adding ``'.'`` at the end of the filename
* Fixed: ``audeer.extract_archive()``
  and ``audeer.extract_archives()``
  now return normalized relative paths
  also under Windows
* Fixed: add raises section
  to API documentation of ``audeer.list_file_names()``
* Fixed: add raises section
  to API documentation of ``audeer.StrictVersion``


Version 1.19.0 (2022-12-19)
---------------------------

* Added: ``hidden`` argument to
  ``audeer.list_dir_names()``
  to include hidden folders in results
* Added: ``remove_from_kwargs`` argument to
  ``audeer.deprecated_keyword_argument()``
  to indicate if the keyword marked as deprecated
  should be removed from ``kwargs``.
  Default is ``True``
* Added: ``ext`` argument to
  ``audeer.replace_file_extension()``
* Added: support for Python 3.10
* Added: support for Python 3.11
* Changed: split API documentation into sub-pages
  for each function/class
* Fixed: add raises section to docstring of
  ``audeer.list_dir_names()``


Version 1.18.0 (2022-03-04)
---------------------------

* Added: ``audeer.path()``
  as replacement for ``audeer.safe_path()``
* Added: ``*paths`` argument to ``audeer.safe_path()``
  to join paths
* Added: ``recursive`` argument to ``audeer.list_dir_names()``
* Added: ``recursive`` argument to ``audeer.list_file_names()``
* Added: ``audeer.StrictVersion()``
* Added: ``audeer.LooseVersion()``
* Added: ``audeer.install_package()``
* Added: ``audeer.move_file()``
* Added: ``audeer.touch()``
* Deprecated: ``audeer.safe_path()``
* Fixed: add test for MacOS


Version 1.17.2 (2022-01-03)
---------------------------

* Added: Python 3.9 support
* Removed: Python 3.6 support


Version 1.17.1 (2021-11-25)
---------------------------

* Added: ``verbose`` argument to ``audeer.create_archive()``


Version 1.17.0 (2021-11-19)
---------------------------

* Added: ``audeer.rmdir()``


Version 1.16.0 (2021-06-01)
---------------------------

* Added: ``audeer.download_url()``


Version 1.15.0 (2021-05-21)
---------------------------

* Changed: default value of ``num_workers`` argument
  for ``audeer.tun_tasks()`` changed from ``None``
  to ``1``


Version 1.14.0 (2021-04-26)
---------------------------

* Added: ``audeer.replace_file_extension()``


Version 1.13.1 (2021-04-15)
---------------------------

* Added: usage example to ``audeer.progress_bar()``


Version 1.13.0 (2021-04-14)
---------------------------

* Added: ``basenames`` argument to ``audeer.list_dir_names()``
* Added: ``basenames`` argument to ``audeer.list_file_names()``


Version 1.12.0 (2021-02-22)
---------------------------

* Added: ``audeer.create_archive()``


Version 1.11.0 (2021-02-09)
---------------------------

* Added: ``audeer.deprecated_default_value()``
* Added: ``audeer.is_semantic_version()``
* Added: ``audeer.sort_versions()``


Version 1.10.0 (2021-01-29)
---------------------------

* Added: ``audeer.git_repo_version()``
* Added: ``audeer.git_repo_tags()``


Version 1.9.0 (2021-01-21)
--------------------------

* Added: ``audeer.list_dir_names()``


Version 1.8.0 (2020-12-03)
--------------------------

* Added: ``audeer.is_uid()``


Version 1.7.0 (2020-12-02)
--------------------------

* Added: ``audeer.deprecated_keyword_argument()`` decorator
* Changed: ``audeer.deprecated()`` raises now a ``UserWarning``
  instead of ``DeprecationWarning``


Version 1.6.7 (2020-11-18)
--------------------------

* Changed: return member filenames of archives in
  ``audeer.extract_archive()``
  and ``audeer.extract_archives()``


Version 1.6.6 (2020-10-27)
--------------------------

* Fixed: multi-line statements in GitHub releases


Version 1.6.5 (2020-10-27)
--------------------------

* Fixed: long description in ``setup.cfg``,
  which is included on pypi.org
* Fixed: multi-line statements in GitHub releases


Version 1.6.4 (2020-10-23)
--------------------------

* Added: run tests on Windows
* Removed: deprecated ``audb.run_worker_threads()``
  from docs and code coverage
* Fixed: "Edit on Github" link in docs


Version 1.6.3 (2020-10-22)
--------------------------

* Fixed: release instructions for GitHub


Version 1.6.2 (2020-10-21)
--------------------------

* Changed: host documentation on GitHub pages


Version 1.6.1 (2020-10-20)
--------------------------

* Fixed: license specification in Python package


Version 1.6.0 (2020-10-20)
--------------------------

* Added: first public release on GitHub


Version 1.5.1 (2020-09-28)
--------------------------

* Fixed: return actual path
  for symbolic links with ``audeer.safe_path()``
  by using ``os.path.realpath()``
  instead of ``os.path.abspath()``
* Fixed: clean up test scripts
  and remove obsolete ``tests/test_audeer.py``


Version 1.5.0 (2020-09-22)
--------------------------

* Added: ``audeer.common_directory()``


Version 1.4.0 (2020-09-21)
--------------------------

* Added: ``audeer.run_tasks()``


Version 1.3.0 (2020-09-08)
--------------------------

* Added: ``audeer.uid()``


Version 1.2.3 (2020-09-01)
--------------------------

* Changed: use ``url`` and ``project_urls`` in ``setup.cfg``


Version 1.2.2 (2020-08-28)
--------------------------

* Changed: switch home page of package to documentation page


Version 1.2.1 (2020-08-18)
--------------------------

* Changed: ``audb.extract_archive()``
    raises ``RuntimeError`` for broken archives


Version 1.2.0 (2020-08-14)
--------------------------

* Added: ``audb.extract_archive()``
* Added: ``audb.extract_archives()``
* Added: Python 3.8 support
* Removed: Python 3.5 support


Version 1.1.2 (2020-06-12)
--------------------------

* Fixed: wrong homepage link in ``setup.cfg``


Version 1.1.1 (2020-05-20)
--------------------------

* Added: ``mode`` argument to ``audeer.mkdir()``


Version 1.1.0 (2020-04-08)
--------------------------

* Added: ``audeer.to_list()``
* Added: code coverage
* Removed: deprecated ``audeer.generate_dir()``
* Removed: deprecated ``audeer.basename()``


Version 1.0.7 (2020-02-19)
--------------------------

* Fixed: CI again token for automatic package publishing


Version 1.0.6 (2020-02-19)
--------------------------

* Fixed: CI token for automatic package publishing


Version 1.0.5 (2020-02-19)
--------------------------

* Fixed: make ``audeer.mkdir()`` multiprocessing safe


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
* Fixed: another link to ``audeer.configfile``


Version 1.0.1 (2020-02-06)
--------------------------

* Fixed: link to ``audeer.configfile``


Version 1.0.0 (2020-02-06)
--------------------------

* Added: ``audeer.format_display_message()``
* Added: ``audeer.progress_bar()``
* Added: ``audeer.deprecated()``
* Added: ``audeer.run_worker_threads()``
* Added: ``audeer.safe_path``
* Changed: introduce ``audeer.core`` structure
* Changed: rename ``audeer.generate_dir()`` to ``audeer.mkdir()``
* Changed: rename ``audeer.basename`` to ``audeer.basename_wo_ext``
* Removed: all config related code is moved to ``audeer.configfile``
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
* Changed: switch to ``sox`` for audio file info


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
