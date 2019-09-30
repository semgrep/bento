import os
import platform
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.models import Response

from bento.metrics import get_user_uuid

BASE_URL = "https://test.massive.ret2.co"


def _get_default_shell() -> str:
    return os.environ.get("SHELL", "")


def _get_default_headers() -> Dict[str, str]:
    """
    Headers for all bento http/s requests
    """
    return {
        "X-R2C-BENTO-User-Platform": f"{platform.platform()}",
        "X-R2C-BENTO-User-Shell": f"{_get_default_shell()}",
        "Accept": "application/json",
    }


def no_auth_get(
    url: str, params: Dict[str, str] = {}, headers: Dict[str, str] = {}, **kwargs: Any
) -> Response:
    """Perform a requests.get and default headers set"""
    headers = {**_get_default_headers(), **headers}
    r = requests.get(url, headers=headers, params=params, **kwargs)
    return r


def no_auth_post(
    url: str, json: Any = {}, params: Dict[str, str] = {}, headers: Dict[str, str] = {}
) -> Response:
    """Perform a requests.post and default headers set"""
    headers = {**_get_default_headers(), **headers}
    r = requests.post(url, headers=headers, params=params, json=json)
    return r


def _get_base_url() -> str:
    return BASE_URL


def fetch_latest_version() -> Tuple[Optional[str], Optional[str]]:
    try:
        url = f"{_get_base_url()}/bento/api/v1/version"
        r = no_auth_get(url, timeout=0.25)
        response_json = r.json()
        return response_json.get("latest", None), response_json.get("uploadTime", None)
    except Exception:
        return None, None


async def post_metrics(data: List[Dict[str, Any]]) -> bool:
    try:
        url = f"{_get_base_url()}/bento/api/v1/metrics/u/{get_user_uuid()}/"
        r = no_auth_post(url, json=data)
        r.raise_for_status()
        return True
    except Exception as e:
        # TODO log user exception to some local file
        print(e)
        return False
