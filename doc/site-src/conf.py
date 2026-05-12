import os
import sys

project = 'dealii-X'
author = 'dealii-X team'
extensions = [
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'progress.md',
    'repository_layout.md',
]

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
# Use the original logo files placed in `_static/` (do not modify)
html_logo = '_static/DealiiX_logo__officials_colors_white_rgb.svg'
# Favicon: prefer the provided .ico; fallback to svg if not present
html_favicon = '_static/favicon.ico'

# Theme options and custom CSS
html_theme_options = {
    'navigation_depth': 2,
}

# Allow markdown parsing via myst
myst_enable_extensions = [
    'amsmath',
    'deflist',
    'html_admonition',
]

# Add custom CSS for dealii-X palette


def setup(app):
    app.add_css_file('dealiix.css')
    app.add_js_file('footer_inject.js')
