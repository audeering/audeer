from audeer.core.config import config
from audeer.core.io import (
    basename_wo_ext,
    common_directory,
    create_archive,
    download_url,
    extract_archive,
    extract_archives,
    file_extension,
    list_dir_names,
    list_file_names,
    mkdir,
    move_file,
    replace_file_extension,
    rmdir,
    touch,
)
from audeer.core.path import (
    path,
    safe_path,
)
from audeer.core.tqdm import (
    format_display_message,
    progress_bar,
)
from audeer.core.utils import (
    deprecated,
    deprecated_default_value,
    deprecated_keyword_argument,
    flatten_list,
    freeze_requirements,
    git_repo_tags,
    git_repo_version,
    install_package,
    is_semantic_version,
    is_uid,
    run_tasks,
    run_worker_threads,
    sort_versions,
    to_list,
    uid,
)
from audeer.core.version import (
    LooseVersion,
    StrictVersion,
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
