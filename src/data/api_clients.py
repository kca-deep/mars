"""
외부 API 클라이언트 (3종 통합)
- 전파누리 API (이동통신 기지국)
- 산악기상정보 API
- 위험지역 POI API
"""
import httpx
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAPIClient(ABC):
    """API 클라이언트 기본 클래스 (비동기)"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, url: str, params: dict) -> dict:
        """재시도 로직이 포함된 비동기 API 요청"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Requesting: {url}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    @abstractmethod
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        pass


class SpectrumMapClient(BaseAPIClient):
    """전파누리 API 클라이언트 (이동통신 기지국)"""

    def __init__(self, api_key: str, base_url: str = "https://spectrummap.kr/openapiNew.do"):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url

    async def fetch_data(
        self,
        park_name: str = "ALL",
        park_type: int = 1,  # 1=국립, 2=도립, 3=군립
        carrier: str = "ALL",
        service: str = "ALL",
        max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """산악지역 이동통신 기지국 정보 조회"""
        all_data = []
        page = 1

        while page <= max_pages:
            params = {
                "key": self.api_key,
                "searchId": "07",
                "type": "json",
                "SCH_CD": "MOBILE",
                "PARK_CD": park_type,
                "QUERY": park_name,
                "CUS_CD": carrier,
                "SERVICE_CD": service,
                "pIndex": page,
                "pSize": 100
            }

            try:
                result = await self._request(self.base_url, params)
                data = result.get("data", [])
                if not data:
                    break
                all_data.extend(data)
                logger.info(f"전파누리 API - Page {page}: {len(data)} records fetched")
                page += 1
            except Exception as e:
                logger.error(f"전파누리 API 오류: {e}")
                break

        return all_data

    async def get_stations_by_park(self, park_name: str) -> List[Dict[str, Any]]:
        """특정 공원의 기지국 정보 조회"""
        return await self.fetch_data(park_name=park_name)


class MountainWeatherClient(BaseAPIClient):
    """산악기상정보 API 클라이언트"""

    def __init__(self, service_key: str, base_url: str = "https://apis.data.go.kr/1400377/mtweather/mountListSearch"):
        super().__init__()
        self.service_key = service_key
        self.base_url = base_url

    async def fetch_data(
        self,
        local_area: Optional[str] = None,
        obs_id: Optional[str] = None,
        obs_time: Optional[str] = None,
        num_of_rows: int = 100,
        max_pages: int = 3
    ) -> List[Dict[str, Any]]:
        """산악기상 정보 조회"""
        all_data = []
        page = 1

        while page <= max_pages:
            params = {
                "ServiceKey": self.service_key,
                "pageNo": page,
                "numOfRows": num_of_rows,
                "_type": "json"
            }
            if local_area:
                params["localArea"] = local_area
            if obs_id:
                params["obsid"] = obs_id
            if obs_time:
                params["tm"] = obs_time

            try:
                result = await self._request(self.base_url, params)
                body = result.get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])

                if not items:
                    break

                # 단일 항목인 경우 리스트로 변환
                if isinstance(items, dict):
                    items = [items]

                all_data.extend(items)
                logger.info(f"산악기상 API - Page {page}: {len(items)} records fetched")

                total_count = body.get("totalCount", 0)
                if page * num_of_rows >= total_count:
                    break
                page += 1

            except Exception as e:
                logger.error(f"산악기상 API 오류: {e}")
                break

        return all_data

    async def get_weather_by_area(self, area_code: str) -> List[Dict[str, Any]]:
        """지역별 산악기상 정보 조회"""
        return await self.fetch_data(local_area=area_code)


class DangerInfoClient(BaseAPIClient):
    """위험지역 POI API 클라이언트"""

    def __init__(self, service_key: str, base_url: str = "https://apis.data.go.kr/B553662/dangerInfoService"):
        super().__init__()
        self.service_key = service_key
        self.base_url = base_url

    async def fetch_data(
        self,
        endpoint: str = "getDangerInfoList",
        extra_params: Optional[dict] = None,
        num_of_rows: int = 100,
        max_pages: int = 3
    ) -> List[Dict[str, Any]]:
        """위험지역 POI 정보 조회"""
        all_data = []
        page = 1

        while page <= max_pages:
            params = {
                "serviceKey": self.service_key,
                "pageNo": page,
                "numOfRows": num_of_rows,
                "returnType": "JSON"
            }
            if extra_params:
                params.update(extra_params)

            url = f"{self.base_url}/{endpoint}"

            try:
                result = await self._request(url, params)
                body = result.get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])

                if not items:
                    break

                if isinstance(items, dict):
                    items = [items]

                all_data.extend(items)
                logger.info(f"위험지역 API - Page {page}: {len(items)} records fetched")

                if len(items) < num_of_rows:
                    break
                page += 1

            except Exception as e:
                logger.error(f"위험지역 API 오류: {e}")
                break

        return all_data


# 팩토리 함수
def create_spectrum_client(api_key: str) -> SpectrumMapClient:
    return SpectrumMapClient(api_key=api_key)


def create_weather_client(service_key: str) -> MountainWeatherClient:
    return MountainWeatherClient(service_key=service_key)


def create_danger_client(service_key: str) -> DangerInfoClient:
    return DangerInfoClient(service_key=service_key)
