from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
import concurrent.futures
import copy
import functools
import hashlib
import importlib
import importlib.metadata
import inspect
import multiprocessing
import operator
import os
import queue
import subprocess
import sys
import threading
import uuid
import warnings

from audeer.core.path import path as safe_path
from audeer.core.tqdm import progress_bar as audeer_progress_bar
from audeer.core.version import LooseVersion


__doctest_skip__ = ["git_repo_tags", "git_repo_version"]


def deprecated(
    *,
    removal_version: str,
    alternative: str = None,
) -> Callable:
    r"""Mark code as deprecated.

    Provide a `decorator <https://www.python.org/dev/peps/pep-0318/>`_
    to mark functions/classes as deprecated.

    You have to specify the version,
    for which the deprecated code will be removed.
    If you change only small things
    like renaming a function or an argument,
    it will be fine to remove the code
    with the next minor release (`X.(Y+1).Z`).
    Otherwise, choose the next major release (`(X+1).Y.Z`).

    Args:
        removal_version: version the code will be removed
        alternative: alternative code to use

    Examples:
        >>> @audeer.deprecated(removal_version="2.0.0")
        ... def deprecated_function():
        ...     pass

    """

    def _deprecated(func):
        # functools.wraps preserves the name
        # and docstring of the decorated code:
        # https://docs.python.org/3/library/functools.html#functools.wraps
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            message = (
                f"{func.__name__} is deprecated and will be removed "
                f"with version {removal_version}."
            )
            if alternative is not None:
                message += f" Use {alternative} instead."
            warnings.warn(message, category=UserWarning, stacklevel=2)
            return func(*args, **kwargs)

        return new_func

    return _deprecated


def deprecated_default_value(
    *,
    argument: str,
    change_in_version: str,
    new_default_value: object,
) -> Callable:
    """Mark default value of keyword argument as deprecated.

    Provide a `decorator <https://www.python.org/dev/peps/pep-0318/>`_
    to mark the default value of a keyword argument as deprecated.
    You have to specify the version
    for which the default value will change
    and the new default value.

    Args:
        argument: keyword argument
        change_in_version: version the default value will change
        new_default_value: new default value

    Examples:
        >>> @audeer.deprecated_default_value(
        ...     argument="foo",
        ...     change_in_version="2.0.0",
        ...     new_default_value="bar",
        ... )
        ... def deprecated_function(foo="foo"):
        ...     pass
    """

    def _deprecated(func):
        # functools.wraps preserves the name
        # and docstring of the decorated code:
        # https://docs.python.org/3/library/functools.html#functools.wraps
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            if argument not in kwargs:
                signature = inspect.signature(func)
                default_value = signature.parameters[argument].default
                message = (
                    f"The default of '{argument}' will change from "
                    f"'{default_value}' to '{new_default_value}' "
                    f"with version {change_in_version}."
                )
                warnings.warn(message, category=UserWarning, stacklevel=2)
            return func(*args, **kwargs)

        return new_func

    return _deprecated


def deprecated_keyword_argument(
    *,
    deprecated_argument: str,
    removal_version: str,
    new_argument: str = None,
    mapping: Callable = None,
    remove_from_kwargs: bool = True,
) -> Callable:
    r"""Mark keyword argument as deprecated.

    Provide a `decorator <https://www.python.org/dev/peps/pep-0318/>`_
    to mark keyword arguments as deprecated.

    You have to specify the version,
    for which the deprecated argument will be removed.
    The content assigned to ``deprecated_argument``
    is passed on to the ``new_argument``.

    Args:
        deprecated_argument: keyword argument to be marked as deprecated
        removal_version: version the code will be removed
        new_argument: keyword argument that should be used instead
        mapping: if the keyword argument is not only renamed,
            but expects also different input values,
            you can map to the new ones with this callable
        remove_from_kwargs: if ``True``,
            ``deprecated_argument`` will be removed
            from ``kwargs`` inside the decorated object

    Examples:
        >>> @audeer.deprecated_keyword_argument(
        ...     deprecated_argument="foo",
        ...     new_argument="bar",
        ...     removal_version="2.0.0",
        ... )
        ... def function_with_new_argument(*, bar):
        ...     pass

    """

    def _deprecated(func):
        # functools.wraps preserves the name
        # and docstring of the decorated code:
        # https://docs.python.org/3/library/functools.html#functools.wraps
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            if deprecated_argument in kwargs:
                message = (
                    f"'{deprecated_argument}' argument is deprecated "
                    f"and will be removed with version {removal_version}."
                )
                if remove_from_kwargs:
                    argument_content = kwargs.pop(deprecated_argument)
                else:
                    argument_content = kwargs[deprecated_argument]
                if new_argument is not None:
                    message += f" Use '{new_argument}' instead."
                    if mapping is not None:
                        kwargs[new_argument] = mapping(argument_content)
                    else:
                        kwargs[new_argument] = argument_content
                warnings.warn(
                    message,
                    category=UserWarning,
                    stacklevel=2,
                )
            return func(*args, **kwargs)

        return new_func

    return _deprecated


def flatten_list(nested_list: list) -> list:
    """Flatten an arbitrarily nested list.

    Implemented without  recursion to avoid stack overflows.
    Returns a new list, the original list is unchanged.

    Args:
        nested_list: nested list

    Returns:
        flattened list

    Examples:
        >>> audeer.flatten_list([1, 2, 3, [4], [], [[[[[[[[[5]]]]]]]]]])
        [1, 2, 3, 4, 5]
        >>> audeer.flatten_list([[1, 2], 3])
        [1, 2, 3]

    """

    def _flat_generator(nested_list):
        while nested_list:
            sublist = nested_list.pop(0)
            if isinstance(sublist, list):
                nested_list = sublist + nested_list
            else:
                yield sublist

    nested_list = copy.deepcopy(nested_list)
    return list(_flat_generator(nested_list))


def freeze_requirements(outfile: str):
    r"""Log Python packages of activate virtual environment.

    Args:
        outfile: file to store the packages.
            Usually a name like :file:`requirements.txt.lock` should be picked.

    Raises:
        RuntimeError: if running ``pip freeze`` returns an error

    """
    outfile = safe_path(outfile)
    try:
        with open(outfile, "w") as fp:
            subprocess.run(
                _pip(["freeze"]),
                stdout=fp,
                stderr=subprocess.PIPE,
                check=True,
            )
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        raise RuntimeError(f"Freezing Python packages failed: {err}")


def git_repo_tags(
    *,
    v: bool = None,
) -> list:
    r"""Get a list of available git tags.

    The tags are inferred by executing
    ``git tag`` in the current folder.
    If the command fails,
    an empty list is returned.

    Args:
        v: if ``True`` tags start always with ``v``,
            if ``False`` they never start with ``v``,
            if ``None`` the original tag names are returned

    Returns:
        list of tags

    Examples:
        .. skip: next

        >>> audeer.git_repo_tags()
        ['v1.0.0', 'v1.1.0', 'v2.0.0']

    """
    try:
        git = ["git", "tag"]
        tags = subprocess.check_output(git)
        tags = tags.decode().strip().split("\n")
    except Exception:  # pragma: no cover
        tags = []
    if v is None:
        return tags
    if v:
        tags = [f"v{t}" if not t.startswith("v") else t for t in tags]
    else:
        tags = [t.removeprefix("v") for t in tags]
    return tags


def git_repo_version(
    *,
    v: bool = True,
) -> str:
    r"""Get a version number from current git ref.

    The version is inferred executing
    ``git describe --tags --always``.
    If the command fails,
    ``'<unknown>'`` is returned.

    Args:
        v: if ``True`` version starts always with ``v``,
            otherwise it never starts with ``v``

    Returns:
        version number

    Examples:
        .. skip: next

        >>> audeer.git_repo_version()
        'v1.0.0'

    """
    try:
        git = ["git", "describe", "--tags", "--always"]
        version = subprocess.check_output(git)
        version = version.decode().strip()
    except Exception:  # pragma: no cover
        version = "<unknown>"
    if version.startswith("v") and not v:  # pragma: no cover (only local)
        version = version[1:]
    elif not version.startswith("v") and v:  # pragma: no cover (only github)
        version = f"v{version}"
    return version


def install_package(
    name: str,
    *,
    version: str = None,
    silent: bool = False,
):
    r"""Install a Python package with pip.

    An error is raised if a different version
    of the package is already installed.
    However,
    it is possible to use one of the following
    operators in front of the version string:
    ``'>='``, ``'>'``, ``'<='``, ``'<'``.
    In that case,
    an error is raised only
    if the condition is not satisfied.
    If version is set to ``None``
    and the package is not installed yet,
    the latest version will be installed.

    Args:
        name: package name
        version: version string (see description)
        silent: suppress messages to stdout

    Raises:
        subprocess.CalledProcessError: if the sub-process calling pip fails,
            e.g. because requested version of the package is not found
        RuntimeError: if a version of the package is already
            installed that does not satisfy the requested version

    """
    version = version.strip() if version is not None else None
    version_org = version
    op = operator.eq

    # check for operators, e.g.
    # >=1.0, >1.0, <=1.0, <1.0
    if version is not None:
        if version.startswith(">="):
            op = operator.ge
            version = version[2:].strip()
        elif version.startswith(">"):
            op = operator.gt
            version = version[1:].strip()
        elif version.startswith("<="):
            op = operator.le
            version = version[2:].strip()
        elif version.startswith("<"):
            op = operator.lt
            version = version[1:].strip()

    # raise error if package is already installed
    # and does not satisfy requested version
    try:
        current_version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        current_version = None

    if current_version is not None:
        if version is None:
            return  # any version is fine
        if op(LooseVersion(current_version), LooseVersion(version)):
            return  # installed version satisfies requested version
        raise RuntimeError(
            f"The installed version "
            f"'{current_version}' "
            f"of "
            f"{name} "
            "does not satisfy "
            f"'{version_org}'."
        )

    # install package
    version = version_org
    if version is not None:
        if op == operator.eq:
            # since we do not support ==1.0
            # we have to add it here
            name = f"{name}=={version}"
        else:
            name = f"{name}{version}"

    subprocess.check_call(
        _pip(["install", name]),
        stdout=subprocess.DEVNULL if silent else None,
    )

    # This function should be called if any modules
    # are created/installed while your program is running
    # to guarantee all finders will notice the new module’s existence.
    # see https://docs.python.org/3/library/importlib.html
    importlib.invalidate_caches()


def is_semantic_version(version: str) -> bool:
    r"""Check if given string represents a semantic version.

    To be a `semantic version`_
    your version has to comply to ``X.Y.Z`` or ``vX.Y.Z``,
    where X, Y, Z are all integers.
    Additional version information, like ``beta``
    has to be added using a ``-`` or ``+``,
    e.g. ``X.Y.Z-beta``.

    .. _semantic version: https://semver.org

    Args:
        version: version string

    Returns:
        ``True`` if version is a semantic version

    Examples:
        >>> audeer.is_semantic_version("v1")
        False
        >>> audeer.is_semantic_version("1.2.3-r3")
        True
        >>> audeer.is_semantic_version("v0.7.2-9-g1572b37")
        True

    """
    version_parts = version.split(".")

    if len(version_parts) < 3:
        return False

    def is_integer_convertable(x):
        try:
            int(x)
            return True
        except ValueError:
            return False

    x, y = version_parts[:2]
    # Ignore starting 'v'
    x = x.removeprefix("v")

    z = ".".join(version_parts[2:])
    # For Z, '-' and '+' are also allowed as separators,
    # but you are not allowed to have an additional '.' before
    z = z.split("-")[0]
    z = z.split("+")[0]
    if len(z.split(".")) > 1:
        return False

    for v in (x, y, z):
        if not is_integer_convertable(v):
            return False

    return True


def is_uid(uid: str) -> bool:
    r"""Check if string is a unique identifier.

    Unique identifiers can be generated with :func:`audeer.uid`.

    Args:
        uid: string

    Returns:
        ``True`` if string is a unique identifier

    Examples:
        >>> audeer.is_uid("626f68e6-d336-70b9-e753-ed9fad855840")
        True
        >>> audeer.is_uid("ad855840")
        True
        >>> audeer.is_uid("not a unique identifier")
        False

    """
    if uid is None:
        return False
    if not isinstance(uid, str):
        return False
    if len(uid) != 8 and len(uid) != 36:
        return False

    if len(uid) == 8:
        uid = f"00000000-0000-0000-0000-0000{uid}"

    for pos in [8, 13, 18, 23]:
        if not uid[pos] == "-":
            return False

    try:
        uuid.UUID(uid, version=1)
    except ValueError:
        return False

    return True


def run_tasks(
    task_func: Callable,
    params: Sequence[
        tuple[
            Sequence[object],
            dict[str, object],
        ]
    ],
    *,
    num_workers: int = 1,
    multiprocessing: bool = False,
    progress_bar: bool = False,
    task_description: str = None,
    maximum_refresh_time: float = None,
) -> list[object]:
    r"""Run parallel tasks using multprocessing.

    .. note:: Result values are returned in order of ``params``.

    Args:
        task_func: task function with one or more
            parameters, e.g. ``x, y, z``, and optionally returning a value
        params: sequence of tuples holding parameters for each task.
            Each tuple contains a sequence of positional arguments and a
            dictionary with keyword arguments, e.g.:
            ``[((x1, y1), {'z': z1}), ((x2, y2), {'z': z2}), ...]``
        num_workers: number of parallel jobs or 1 for sequential
            processing. If ``None`` will be set to the number of
            processors on the machine multiplied by 5 in case of
            multithreading and number of processors in case of
            multiprocessing
        multiprocessing: use multiprocessing instead of multithreading
        progress_bar: show a progress bar
        task_description: task description
            that will be displayed next to progress bar
        maximum_refresh_time: refresh the progress bar
            at least every ``maximum_refresh_time`` seconds,
            using another thread.
            If ``None``,
            no refreshing is enforced

    Returns:
        list of computed results

    Examples:
        >>> power = lambda x, n: x**n
        >>> params = [([2, n], {}) for n in range(10)]
        >>> audeer.run_tasks(power, params, num_workers=3)
        [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]

    """
    num_tasks = max(1, len(params))
    results = [None] * num_tasks

    if num_workers == 1:  # sequential
        with audeer_progress_bar(
            params,
            total=len(params),
            desc=task_description,
            maximum_refresh_time=maximum_refresh_time,
            disable=not progress_bar,
        ) as pbar:
            for index, param in enumerate(pbar):
                results[index] = task_func(*param[0], **param[1])

    else:  # parallel
        if multiprocessing:
            executor = concurrent.futures.ProcessPoolExecutor
        else:
            executor = concurrent.futures.ThreadPoolExecutor
        with executor(max_workers=num_workers) as pool:
            with audeer_progress_bar(
                total=len(params),
                desc=task_description,
                maximum_refresh_time=maximum_refresh_time,
                disable=not progress_bar,
            ) as pbar:
                futures = []
                for param in params:
                    future = pool.submit(task_func, *param[0], **param[1])
                    future.add_done_callback(lambda p: pbar.update())
                    futures.append(future)
                for idx, future in enumerate(futures):
                    result = future.result()
                    results[idx] = result

    return results


@deprecated(removal_version="2.0.0", alternative="run_tasks")
def run_worker_threads(
    task_fun: Callable,
    params: Sequence[object] = None,
    *,
    num_workers: int = None,
    progress_bar: bool = False,
    task_description: str = None,
) -> Sequence[object]:  # pragma: no cover
    r"""Run parallel tasks using worker threads.

    .. note:: Result values are returned in order of ``params``.

    Args:
        task_fun: task function with one or more
            parameters, e.g. ``x, y, z``, and optionally returning a value
        params: list of parameters (use tuples in case of multiple parameters)
            for each task, e.g. ``[(x1, y1, z1), (x2, y2, z2), ...]``
        num_workers: number of worker threads (defaults to number of available
            CPUs multiplied by ``5``)
        progress_bar: show a progress bar
        task_description: task description
            that will be displayed next to progress bar

    Examples:
        >>> power = lambda x, n: x**n
        >>> params = [(2, n) for n in range(10)]
        >>> audeer.run_worker_threads(power, params, num_workers=3)
        [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]

    """
    if params is None:
        params = []
    num_tasks = max(1, len(params))
    results = [None] * num_tasks
    if num_workers is None:
        num_workers = multiprocessing.cpu_count() * 5

    # Ensure num_workers is positive
    num_workers = max(1, num_workers)
    # Do not use more workers as needed
    num_workers = min(num_workers, num_tasks)

    # num_workers == 1 -> run sequentially
    if num_workers == 1:
        for index, param in enumerate(params):
            if type(param) in (list, tuple):
                results[index] = task_fun(*param)
            else:
                results[index] = task_fun(param)

    # num_workers > 1 -> run parallel
    else:
        # Create queue, possibly with a progress bar
        if progress_bar:

            class QueueWithProgbar(queue.Queue):
                def __init__(self, num_tasks, maxsize=0):
                    super().__init__(maxsize)
                    self.pbar = audeer_progress_bar(
                        total=num_tasks,
                        desc=task_description,
                    )

                def task_done(self):
                    super().task_done()
                    self.pbar.update(1)

            q = QueueWithProgbar(num_tasks)
        else:
            q = queue.Queue()

        # Fill queue
        for index, param in enumerate(params):
            q.put((index, param))

        # Define worker thread
        def _worker():
            while True:
                item = q.get()
                if item is None:
                    break
                index, param = item
                if type(param) in (list, tuple):
                    results[index] = task_fun(*param)
                else:
                    results[index] = task_fun(param)
                q.task_done()

        # Start workers
        threads = []
        for i in range(num_workers):
            t = threading.Thread(target=_worker)
            t.start()
            threads.append(t)

        # Block until all tasks are done
        q.join()

        # Stop workers
        for _ in range(num_workers):
            q.put(None)
        for t in threads:
            t.join()
    return results


def sort_versions(
    versions: list[str],
) -> list[str]:
    """Sort version numbers.

    If a version starts with ``v``,
    the ``v`` is ignored during sorting.

    Args:
        versions: sequence with semantic version numbers

    Returns:
        sorted list of versions with highest as last entry

    Raises:
        ValueError: if the version does not comply
            with :func:`is_semantic_version`

    Examples:
        >>> vers = [
        ...     "2.0.0",
        ...     "2.0.1",
        ...     "v1.0.0",
        ...     "v2.0.0-1-gdf29c4a",
        ... ]
        >>> audeer.sort_versions(vers)
        ['v1.0.0', '2.0.0', 'v2.0.0-1-gdf29c4a', '2.0.1']

    """
    for version in versions:
        if not is_semantic_version(version):
            raise ValueError(
                "All version numbers have to be semantic versions, "
                "following 'X.Y.Z', "
                "where X, Y, Z are integers. "
                f"But your version is: '{version}'."
            )

    def sort_key(value):
        value = value.removeprefix("v")
        return LooseVersion(value)

    return sorted(versions, key=sort_key)


def to_list(x: object):
    """Convert to list.

    If an iterable is passed,
    that is not a string it will be converted using :class:`list`.
    Otherwise, ``x`` is converted by ``[x]``.

    Args:
        x: input to be converted to a list

    Returns:
        input as a list

    Examples:
        >>> audeer.to_list("abc")
        ['abc']
        >>> audeer.to_list((1, 2, 3))
        [1, 2, 3]

    """
    if not isinstance(x, Iterable) or isinstance(x, str):
        return [x]
    else:
        return list(x)


def uid(
    *,
    from_string: str = None,
    short: bool = False,
) -> str:
    r"""Generate unique identifier.

    A unique identifier contains 36 characters
    with ``-`` at position 9, 14, 19, 24.
    If ``short`` is ``True``,
    only the last 8 digits are returned.

    Args:
        from_string: create a unique identifier
            by hashing the provided string.
            This will return the same identifier
            for identical strings.
            If ``None`` :func:`uuid.uuid1` is used.
        short: if ``True`` returns
            a short unique identifier
            (last 8 digits)

    Returns:
        unique identifier

    Examples:
        >>> audeer.uid(from_string="example_string")
        '626f68e6-d336-70b9-e753-ed9fad855840'
        >>> audeer.uid(from_string="example_string", short=True)
        'ad855840'

    """
    if from_string is None:
        uid = str(uuid.uuid1())
    else:
        uid = hashlib.md5()
        uid.update(from_string.encode("utf-8"))
        uid = uid.hexdigest()
        uid = f"{uid[0:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:]}"

    if short:
        uid = uid[-8:]

    return uid


def unique(sequence: Iterable) -> list:
    r"""Unique values in its original order.

    This is an alternative to ``list(set(x))``,
    which does not preserve the original order.

    Args:
        sequence: sequence of values

    Returns:
        unique values from ``x`` in order of appearance

    Examples:
        >>> list(set([2, 2, 1]))
        [1, 2]
        >>> audeer.unique([2, 2, 1])
        [2, 1]

    """
    # https://stackoverflow.com/a/480227
    seen = set()
    seen_add = seen.add
    return [x for x in sequence if not (x in seen or seen_add(x))]


def _pip(arguments: list[str]) -> list[str]:
    """Pip command in the given virtual environment.

    The virtual environment can be created with Python,
    virtualenv,
    or be managed by uv.

    Returns:
        command to run pip in current virtual environment

    """
    if _is_uv():
        return ["uv", "pip"] + arguments  # pragma: no pip cover
    return [sys.executable, "-m", "pip"] + arguments  # pragma: no uv cover


@functools.lru_cache(maxsize=1)
def _is_uv() -> bool:
    """Check if current virtual environment is managed by uv.

    The result is cached for the same virtual environment,
    to avoid unnecessary disk reads.

    """
    current_virtual_env_path = sys.prefix
    pyenv_cfg = os.path.join(current_virtual_env_path, "pyvenv.cfg")
    if os.path.exists(pyenv_cfg):
        with open(pyenv_cfg) as fp:  # pragma: no pip cover
            for line in fp:
                if line.startswith("uv = "):
                    return True
    return False  # pragma: no uv cover
