"""Feishu Open API client with automatic token management."""

from __future__ import annotations

import time

import requests


class FeishuClient:
    """Handles authentication with Feishu Open API."""

    def __init__(self, config: dict):
        feishu_config = config["feishu"]
        self.app_id = feishu_config["app_id"]
        self.app_secret = feishu_config["app_secret"]
        self.base_url = feishu_config["base_url"]
        self.request_timeout = feishu_config.get("request_timeout", 30)
        self.max_retries = feishu_config.get("request_retries", 3)
        self.retry_backoff = feishu_config.get("retry_backoff", 1.5)
        self._token: str | None = None
        self._token_expires = 0.0

    @property
    def token(self) -> str:
        """Get current tenant_access_token, refreshing if needed."""
        if not self._token or time.time() >= self._token_expires - 60:
            self._refresh_token()
        return self._token

    def _refresh_token(self) -> None:
        """Refresh the tenant_access_token from Feishu."""
        data = self._request_json(
            "POST",
            "/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
            include_auth=False,
        )
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data}")

        self._token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200)
        print(f"   Feishu token refreshed, expires in {data.get('expire', 7200)}s")

    def request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request and return JSON."""
        data = self._request_json(method, path, **kwargs)
        if data.get("code") != 0:
            raise RuntimeError(
                f"Feishu API error [{method} {path}]: "
                f"code={data.get('code')}, msg={data.get('msg')}"
            )
        return data

    def _request_json(self, method: str, path: str, *, include_auth: bool = True, **kwargs) -> dict:
        """Send a request, retrying transient failures."""
        url = f"{self.base_url}{path}"
        timeout = kwargs.pop("timeout", self.request_timeout)
        base_headers = dict(kwargs.pop("headers", {}))
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            headers = dict(base_headers)
            headers.setdefault("Content-Type", "application/json; charset=utf-8")
            if include_auth:
                headers["Authorization"] = f"Bearer {self.token}"
            try:
                resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                delay = self.retry_backoff * attempt
                print(
                    f"   Feishu request retry {attempt + 1}/{self.max_retries} "
                    f"for [{method} {path}] after error: {exc}"
                )
                time.sleep(delay)

        raise RuntimeError(f"Feishu request failed [{method} {path}]: {last_error}") from last_error
