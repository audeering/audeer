import audeer


# Project -----------------------------------------------------------------
project = "audeer"
author = "Hagen Wierstorf, Johannes Wagner"
version = audeer.git_repo_version()
title = "{} Documentation".format(project)


# General -----------------------------------------------------------------
master_doc = "index"
source_suffix = ".rst"
exclude_patterns = [
    "build",
    "tests",
    "Thumbs.db",
    ".DS_Store",
    "api-src",
]
pygments_style = None
extensions = [
    "sphinx.ext.napoleon",  # support for Google-style docstrings
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_apipages",
]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}
linkcheck_ignore = [
    "https://gitlab.audeering.com",
]
copybutton_prompt_text = r">>> |\.\.\. |$ "
copybutton_prompt_is_regexp = True

autodoc_default_options = {
    "undoc-members": False,
}
apipages_hidden_methods = [
    "__call__",
    "__eq__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__repr__",
    "__str__",
]


# HTML --------------------------------------------------------------------
html_theme = "sphinx_audeering_theme"
html_theme_options = {
    "display_version": True,
    "footer_links": False,
    "logo_only": False,
}
html_context = {
    "display_github": True,
}
html_title = title
