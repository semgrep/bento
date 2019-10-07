import os

RESOURCE_DIR = "./.bento"
CONFIG_PATH = "./.bento.yml"

GLOBAL_CONFIG_DIR = os.path.expanduser("~/.bento")
GLOBAL_CONFIG_PATH = os.path.join(GLOBAL_CONFIG_DIR, "config.yml")

BASELINE_FILE_PATH = "./.bento-whitelist.yml"

TERMS_OF_SERVICE_KEY = "terms_of_service"
TERMS_OF_SERVICE_VERSION = "0.0.1"
