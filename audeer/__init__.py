from audeer.core.config import config
from audeer.core.io import (
    basename_wo_ext,
    common_directory,
    extract_archive,
    extract_archives,
    file_extension,
    list_file_names,
    mkdir,
    safe_path,
)
from audeer.core.tqdm import (
    format_display_message,
    progress_bar,
)
from audeer.core.utils import (
    deprecated,
    flatten_list,
    freeze_requirements,
    uid,
    run_tasks,
    run_worker_threads,
    to_list,
)


# Discourage from audeer import *
__all__ = []


# Dynamically get the version of the installed module
try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution(__name__).version
except Exception:  # pragma: no cover
    pkg_resources = None  # pragma: no cover
finally:
    del pkg_resources