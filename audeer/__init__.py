from audeer.core.config import config
from audeer.core.io import basename_wo_ext
from audeer.core.io import common_directory
from audeer.core.io import create_archive
from audeer.core.io import download_url
from audeer.core.io import extract_archive
from audeer.core.io import extract_archives
from audeer.core.io import file_extension
from audeer.core.io import list_dir_names
from audeer.core.io import list_file_names
from audeer.core.io import md5
from audeer.core.io import mkdir
from audeer.core.io import move
from audeer.core.io import move_file
from audeer.core.io import replace_file_extension
from audeer.core.io import rmdir
from audeer.core.io import script_dir
from audeer.core.io import touch
from audeer.core.path import path
from audeer.core.path import safe_path
from audeer.core.tqdm import format_display_message
from audeer.core.tqdm import progress_bar
from audeer.core.utils import deprecated
from audeer.core.utils import deprecated_default_value
from audeer.core.utils import deprecated_keyword_argument
from audeer.core.utils import flatten_list
from audeer.core.utils import freeze_requirements
from audeer.core.utils import git_repo_tags
from audeer.core.utils import git_repo_version
from audeer.core.utils import install_package
from audeer.core.utils import is_semantic_version
from audeer.core.utils import is_uid
from audeer.core.utils import run_tasks
from audeer.core.utils import run_worker_threads
from audeer.core.utils import sort_versions
from audeer.core.utils import to_list
from audeer.core.utils import uid
from audeer.core.utils import unique
from audeer.core.version import LooseVersion
from audeer.core.version import StrictVersion


# Discourage from audeer import *
__all__ = []


# Dynamically get the version of the installed module
try:
    import importlib.metadata

    __version__ = importlib.metadata.version(__name__)
except Exception:  # pragma: no cover
    importlib = None  # pragma: no cover
finally:
    del importlib
