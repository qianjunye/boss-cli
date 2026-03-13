"""API client for Boss Zhipin."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from boss_cli.auth import Credential
from boss_cli.constants import (
    BASE_URL,
    CITY_CODES,
    HEADERS,
    JOB_CARD_URL,
    JOB_DETAIL_URL,
    JOB_RECOMMEND_URL,
    JOB_SEARCH_URL,
)

logger = logging.getLogger(__name__)


class BossClient:
    """Async HTTP client wrapper for Boss Zhipin APIs."""

    def __init__(self, credential: Credential | None = None):
        self.credential = credential
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BossClient:
        headers = dict(HEADERS)
        cookies = {}
        if self.credential:
            cookies = self.credential.cookies
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            cookies=cookies,
            follow_redirects=True,
            timeout=httpx.Timeout(30),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with BossClient() as client:'")
        return self._client

    def _check_response(self, data: dict[str, Any], action: str) -> dict[str, Any]:
        """Validate API response and return zpData."""
        code = data.get("code", -1)
        if code == 37:
            raise RuntimeError(
                f"{action}: 环境异常 (__zp_stoken__ 已过期)。"
                "请清除 cookie 后重新登录: boss logout && boss login"
            )
        if code != 0:
            raise RuntimeError(f"{action}: {data.get('message', 'Unknown error')} (code={code})")
        return data.get("zpData", {})

    async def search_jobs(
        self,
        query: str,
        city: str = "101010100",  # Beijing
        page: int = 1,
        page_size: int = 15,
        experience: str | None = None,
        degree: str | None = None,
        salary: str | None = None,
        industry: str | None = None,
        scale: str | None = None,
        stage: str | None = None,
    ) -> dict[str, Any]:
        """Search jobs on Boss Zhipin.

        Args:
            query: Search keyword
            city: City code (default: Beijing 101010100)
            page: Page number
            page_size: Results per page
            experience: Experience filter code
            degree: Degree filter code
            salary: Salary filter code
            industry: Company industry filter
            scale: Company scale filter
            stage: Funding stage filter

        Returns:
            Parsed JSON response with job listings
        """
        params: dict[str, Any] = {
            "query": query,
            "city": city,
            "page": page,
            "pageSize": page_size,
        }
        if experience:
            params["experience"] = experience
        if degree:
            params["degree"] = degree
        if salary:
            params["salary"] = salary
        if industry:
            params["industry"] = industry
        if scale:
            params["scale"] = scale
        if stage:
            params["stage"] = stage

        resp = await self.client.get(JOB_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "搜索职位")

    async def get_recommend_jobs(self, page: int = 1) -> dict[str, Any]:
        """Get personalized job recommendations.

        Args:
            page: Page number

        Returns:
            Parsed JSON response with recommended jobs
        """
        resp = await self.client.get(JOB_RECOMMEND_URL, params={"page": page})
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "推荐职位")

    async def get_job_card(self, security_id: str, lid: str) -> dict[str, Any]:
        """Get job card info (used for hover preview).

        Args:
            security_id: Job security ID from search results
            lid: Lid parameter from search results

        Returns:
            Parsed JSON response with job card details
        """
        resp = await self.client.get(
            JOB_CARD_URL,
            params={"securityId": security_id, "lid": lid},
        )
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "职位卡片")

    async def get_job_detail(self, security_id: str, lid: str = "") -> dict[str, Any]:
        """Get detailed information for a specific job.

        Args:
            security_id: Job security ID from search results
            lid: Lid parameter from search results

        Returns:
            Parsed JSON response with full job details
        """
        params: dict[str, str] = {"securityId": security_id}
        if lid:
            params["lid"] = lid
        resp = await self.client.get(JOB_DETAIL_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._check_response(data, "职位详情")


# ── City resolution ─────────────────────────────────────────────────

def resolve_city(name: str) -> str:
    """Resolve city name to code, passthrough if already a code."""
    if name.isdigit() and len(name) >= 6:
        return name
    return CITY_CODES.get(name, CITY_CODES["全国"])


def list_cities() -> dict[str, str]:
    """Return all supported city name -> code mappings."""
    return dict(CITY_CODES)
