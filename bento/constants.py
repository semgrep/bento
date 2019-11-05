import os

import click

RESOURCE_DIR = ".bento"
CONFIG_PATH = ".bento.yml"
LOCAL_RUN_CACHE = f"{RESOURCE_DIR}/cache"

GLOBAL_CONFIG_DIR = os.path.expanduser("~/.bento")
GLOBAL_CONFIG_PATH = os.path.join(GLOBAL_CONFIG_DIR, "config.yml")

DEFAULT_LOG_PATH = os.path.join(GLOBAL_CONFIG_DIR, "last.log")

BASELINE_FILE_PATH = ".bento-whitelist.yml"

TERMS_OF_SERVICE_KEY = "terms_of_service"
TERMS_OF_SERVICE_VERSION = "0.3.0"

BENTO_TEMPLATE_HASH = "3a04e0f0cd9243d20b1e33da7ac13115"

QA_TEST_EMAIL_ADDRESS = "test@returntocorp.com"

### messages ###

UPGRADE_WARNING_OUTPUT = f"""
╭─────────────────────────────────────────────╮
│  🎉 A new version of Bento is available 🎉  │
│  Try it out by running:                     │
│                                             │
│       {click.style("pip3 install --upgrade bento-cli", fg="blue")}      │
│                                             │
╰─────────────────────────────────────────────╯
"""

TERMS_OF_SERVICE_MESSAGE = f"""│ We’re constantly looking for ways to make Bento better! To that end, we
│ collect statistics about your usage and results to improve the tool over time. Bento runs
│ on your local machine and never sends your code anywhere or to anyone. Learn
│ more at https://github.com/returntocorp/bento/blob/master/PRIVACY.md.
"""

TERMS_OF_SERVICE_ERROR = f"""
Bento did NOT install. Bento beta users must agree to the terms of service to continue. Please reach out to us at support@r2c.dev with questions or concerns.
"""
