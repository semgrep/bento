import os
from pathlib import Path

from click.termui import style

GLOBAL_CONFIG_DIR = os.path.expanduser("~/.bento")
GLOBAL_CONFIG_PATH = os.path.join(GLOBAL_CONFIG_DIR, "config.yml")

DEFAULT_LOG_PATH = os.path.join(GLOBAL_CONFIG_DIR, "last.log")

TERMS_OF_SERVICE_KEY = "terms_of_service"
TERMS_OF_SERVICE_VERSION = "0.3.0"

BENTO_TEMPLATE_HASH = "3a04e0f0cd9243d20b1e33da7ac13115"

GREP_CONFIG_PATH = ".bento-grep.yml"

BENTO_EMAIL_VAR = "BENTO_EMAIL"
QA_TEST_EMAIL_ADDRESS = "test@returntocorp.com"
SUPPORT_EMAIL_ADDRESS = "support@r2c.dev"

ARGS_TO_EXCLUDE_FROM_METRICS = {"check": ["paths"]}

### messages ###

UPGRADE_WARNING_OUTPUT = f"""
╭─────────────────────────────────────────────╮
│  🎉 A new version of Bento is available 🎉  │
│  Try it out by running:                     │
│                                             │
│       {style("pip3 install --upgrade bento-cli", fg="blue")}      │
│                                             │
╰─────────────────────────────────────────────╯
"""

### Content ###

REGISTRATION_CONTENT_PATH = (
    Path(os.path.dirname(__file__)) / "resources" / "register-content.yml"
)

INIT_CONTENT_PATH = Path(os.path.dirname(__file__)) / "resources" / "init-content.yml"
