"""
SGIS (통계지리정보서비스) 지오코딩 API 클라이언트
- 주소 → 좌표 변환 (geocodewgs84)
- 좌표 → 주소 변환 (rgeocodewgs84)
"""
import httpx
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GeocodingResult:
    """지오코딩 결과"""
    address: str
    x: Optional[float] = None  # 경도 (lon)
    y: Optional[float] = None  # 위도 (lat)
    sido_nm: Optional[str] = None
    sgg_nm: Optional[str] = None
    emdong_nm: Optional[str] = None
    full_addr: Optional[str] = None
    matching: Optional[int] = None  # 0=완전매칭, 1=불완전매칭
    success: bool = False
    error: Optional[str] = None


class SGISClient:
    """SGIS API 클라이언트"""

    BASE_URL = "https://sgisapi.mods.go.kr/OpenAPI3"

    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        self.timeout = 30.0

    async def _get_access_token(self) -> str:
        """액세스 토큰 발급 (4시간 유효)"""
        # 토큰이 유효하면 재사용
        if self._access_token and time.time() < self._token_expires - 300:  # 5분 여유
            return self._access_token

        url = f"{self.BASE_URL}/auth/authentication.json"
        params = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get("errCd") == 0:
                self._access_token = result["result"]["accessToken"]
                # 4시간 유효
                self._token_expires = time.time() + (4 * 60 * 60)
                logger.info("SGIS 액세스 토큰 발급 완료")
                return self._access_token
            else:
                raise Exception(f"SGIS 인증 실패: {result.get('errMsg')}")

    async def geocode(self, address: str) -> GeocodingResult:
        """주소 → 좌표 변환 (WGS84)"""
        try:
            token = await self._get_access_token()

            url = f"{self.BASE_URL}/addr/geocodewgs84.json"
            params = {
                "accessToken": token,
                "address": address,
                "resultcount": 1
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("errCd") == 0 and result.get("result"):
                    data = result["result"]

                    if data.get("resultdata"):
                        item = data["resultdata"][0]
                        return GeocodingResult(
                            address=address,
                            x=float(item.get("x", 0)),  # 경도
                            y=float(item.get("y", 0)),  # 위도
                            sido_nm=item.get("sido_nm"),
                            sgg_nm=item.get("sgg_nm"),
                            emdong_nm=item.get("emdong_nm"),
                            full_addr=item.get("full_addr"),
                            matching=data.get("matching"),
                            success=True
                        )
                    else:
                        return GeocodingResult(
                            address=address,
                            success=False,
                            error="결과 없음"
                        )
                else:
                    return GeocodingResult(
                        address=address,
                        success=False,
                        error=result.get("errMsg", "알 수 없는 오류")
                    )

        except Exception as e:
            logger.error(f"지오코딩 오류 ({address}): {e}")
            return GeocodingResult(
                address=address,
                success=False,
                error=str(e)
            )

    async def reverse_geocode(
        self,
        x: float,
        y: float,
        addr_type: int = 20  # 20=행정동
    ) -> Dict[str, Any]:
        """좌표 → 주소 변환 (WGS84)"""
        try:
            token = await self._get_access_token()

            url = f"{self.BASE_URL}/addr/rgeocodewgs84.json"
            params = {
                "accessToken": token,
                "x_coor": x,
                "y_coor": y,
                "addr_type": addr_type
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("errCd") == 0 and result.get("result"):
                    return {
                        "success": True,
                        "data": result["result"][0] if result["result"] else {}
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("errMsg", "알 수 없는 오류")
                    }

        except Exception as e:
            logger.error(f"리버스 지오코딩 오류 ({x}, {y}): {e}")
            return {"success": False, "error": str(e)}

    async def batch_geocode(
        self,
        addresses: List[str],
        delay: float = 0.1,  # API 호출 간격 (초)
        progress_callback: Optional[callable] = None
    ) -> List[GeocodingResult]:
        """주소 목록 일괄 지오코딩"""
        results = []
        total = len(addresses)

        for i, addr in enumerate(addresses):
            result = await self.geocode(addr)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, addr, result.success)

            # API 호출 제한 방지
            if i < total - 1:
                await asyncio.sleep(delay)

        return results


async def geocode_accident_data(
    consumer_key: str,
    consumer_secret: str,
    input_file: str,
    output_file: str
) -> Dict[str, Any]:
    """소방청 사고 데이터 지오코딩 및 Excel 저장"""
    import pandas as pd

    # 클라이언트 초기화
    client = SGISClient(consumer_key, consumer_secret)

    # 데이터 로드
    logger.info(f"데이터 로딩: {input_file}")
    df = pd.read_excel(input_file)

    # 고유 주소 추출
    df['full_addr'] = (
        df['발생장소_시'].fillna('') + ' ' +
        df['발생장소_구'].fillna('') + ' ' +
        df['발생장소_동'].fillna('')
    ).str.strip()

    unique_addresses = df['full_addr'].unique().tolist()
    logger.info(f"고유 주소 수: {len(unique_addresses)}")

    # 진행 상황 출력
    def progress(current, total, addr, success):
        status = "OK" if success else "FAIL"
        if current % 50 == 0 or current == total:
            logger.info(f"진행: {current}/{total} ({100*current/total:.1f}%)")

    # 일괄 지오코딩
    logger.info("지오코딩 시작...")
    results = await client.batch_geocode(
        unique_addresses,
        delay=0.1,
        progress_callback=progress
    )

    # 결과를 DataFrame으로 변환
    geocode_df = pd.DataFrame([
        {
            'original_addr': r.address,
            'lon': r.x,
            'lat': r.y,
            'sido_nm': r.sido_nm,
            'sgg_nm': r.sgg_nm,
            'emdong_nm': r.emdong_nm,
            'full_addr_result': r.full_addr,
            'matching': '완전' if r.matching == 0 else '불완전' if r.matching == 1 else None,
            'success': r.success,
            'error': r.error
        }
        for r in results
    ])

    # 원본 데이터와 조인
    df_merged = df.merge(
        geocode_df,
        left_on='full_addr',
        right_on='original_addr',
        how='left'
    )

    # Excel 저장
    logger.info(f"결과 저장: {output_file}")
    df_merged.to_excel(output_file, index=False, engine='openpyxl')

    # 통계
    success_count = geocode_df['success'].sum()
    fail_count = len(geocode_df) - success_count

    stats = {
        "total_records": len(df),
        "unique_addresses": len(unique_addresses),
        "geocode_success": int(success_count),
        "geocode_fail": int(fail_count),
        "success_rate": f"{100 * success_count / len(unique_addresses):.1f}%",
        "output_file": output_file
    }

    logger.info(f"완료: {stats}")
    return stats


# 테스트용 메인 함수
if __name__ == "__main__":
    import sys

    async def test():
        # 테스트용 키 (실제 키로 교체 필요)
        consumer_key = "YOUR_CONSUMER_KEY"
        consumer_secret = "YOUR_CONSUMER_SECRET"

        client = SGISClient(consumer_key, consumer_secret)

        # 단일 주소 테스트
        result = await client.geocode("서울특별시 강남구 역삼동")
        print(f"결과: {result}")

    asyncio.run(test())
