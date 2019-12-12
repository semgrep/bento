import os

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

SLACK_SIGNUP_LINK = "https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA"

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
