import concurrent.futures
from collections.abc import Iterable
import copy
import functools
import hashlib
import queue
import threading
import typing
import multiprocessing
import subprocess
from typing import Any, Callable, List, Sequence
import uuid
import warnings

import audeer


def deprecated(
        *,
        removal_version: str,
        alternative: str = None
) -> Callable:
    """Mark code as deprecated.

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

    Example:
        >>> @deprecated(removal_version='2.0.0')
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
                f'{func.__name__} is deprecated and will be removed '
                f'with version {removal_version}.'
            )
            if alternative is not None:
                message += f' Use {alternative} instead.'
            warnings.warn(message, category=UserWarning, stacklevel=2)
            return func(*args, **kwargs)
        return new_func
    return _deprecated


def deprecated_keyword_argument(
        *,
        deprecated_argument: str,
        removal_version: str,
        new_argument: str = None,
        mapping: typing.Callable = None,
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

    Example:
        >>> @deprecated_keyword_argument(
        ...     deprecated_argument='foo',
        ...     new_argument='bar',
        ...     removal_version='2.0.0',
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
                argument_content = kwargs.pop(deprecated_argument)
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


def flatten_list(
        nested_list: List
) -> List:
    """Flatten an arbitrarily nested list.

    Implemented without  recursion to avoid stack overflows.
    Returns a new list, the original list is unchanged.

    Args:
        nested_list: nested list

    Returns:
        flattened list

    Example:
        >>> flatten_list([1, 2, 3, [4], [], [[[[[[[[[5]]]]]]]]]])
        [1, 2, 3, 4, 5]
        >>> flatten_list([[1, 2], 3])
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
    cmd = f'pip freeze > {outfile}'
    with subprocess.Popen(
            args=cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            shell=True,
    ) as p:
        _, err = p.communicate()
        if bool(p.returncode):
            raise RuntimeError(f'Freezing Python packages failed: {err}')


def is_uid(uid: str) -> bool:
    r"""Check if string is a unique identifier.

    Unique identifiers can be generated with :func:`audeer.uid`.

    Args:
        uid: string

    Returns:
        ``True`` if string is a unique identifier

    """
    if uid is None:
        return False
    if not isinstance(uid, str):
        return False
    try:
        uuid.UUID(uid, version=1)
    except ValueError:
        return False
    return True


def run_tasks(
        task_func: typing.Callable,
        params: typing.Sequence[
            typing.Tuple[
                typing.Sequence[typing.Any],
                typing.Dict[str, typing.Any],
            ]
        ],
        *,
        num_workers: int = None,
        multiprocessing: bool = False,
        progress_bar: bool = False,
        task_description: str = None
) -> typing.Sequence[typing.Any]:
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

    Example:
        >>> power = lambda x, n: x ** n
        >>> params = [([2, n], {}) for n in range(10)]
        >>> run_tasks(power, params, num_workers=3)
        [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]

    """
    num_tasks = max(1, len(params))
    results = [None] * num_tasks

    if num_workers == 1:  # sequential

        with audeer.progress_bar(
            params,
            total=len(params),
            desc=task_description,
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
            with audeer.progress_bar(
                    total=len(params),
                    desc=task_description,
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


@deprecated(removal_version='2.0.0', alternative='run_tasks')
def run_worker_threads(
        task_fun: Callable,
        params: Sequence[Any] = None,
        *,
        num_workers: int = None,
        progress_bar: bool = False,
        task_description: str = None
) -> Sequence[Any]:  # pragma: no cover
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

    Example:
        >>> power = lambda x, n: x ** n
        >>> params = [(2, n) for n in range(10)]
        >>> run_worker_threads(power, params, num_workers=3)
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
                    self.pbar = audeer.progress_bar(
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


def to_list(x: Any):
    """Convert to list.

    If an iterable is passed,
    that is not a string it will be converted using :class:`list`.
    Otherwise, ``x`` is converted by ``[x]``.

    Args:
        x: input to be converted to a list

    Returns:
        input as a list

    Example:
        >>> to_list('abc')
        ['abc']
        >>> to_list((1, 2, 3))
        [1, 2, 3]

    """
    if not isinstance(x, Iterable) or isinstance(x, str):
        return [x]
    else:
        return list(x)


def uid(
        *,
        from_string: str = None,
) -> str:
    r"""Generate unique identifier.

    Args:
        from_string: create a unique identifier
            by hashing the provided string.
            This will return the same identifier
            for identical strings.
            If ``None`` :func:`uuid.uuid1` is used.

    Returns:
        unique identifier containing 36 characters
        with ``-`` at position 9, 14, 19, 24

    Example:
        >>> uid(from_string='example_string')
        '626f68e6-d336-70b9-e753-ed9fad855840'

    """
    if from_string is None:
        uid = str(uuid.uuid1())
    else:
        uid = hashlib.md5()
        uid.update(from_string.encode('utf-8'))
        uid = uid.hexdigest()
        uid = f'{uid[0:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:]}'
    return uid
