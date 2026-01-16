"""
Pydantic 스키마 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ===== 공통 =====
class APIResponse(BaseModel):
    """공통 API 응답"""
    success: bool
    message: str
    data: Any = None
    count: int = 0


class ParkType(int, Enum):
    """공원 유형"""
    NATIONAL = 1  # 국립
    PROVINCIAL = 2  # 도립
    COUNTY = 3  # 군립


class CarrierType(str, Enum):
    """통신사 유형"""
    SK = "SK"
    KT = "KT"
    LG = "LG"
    ALL = "ALL"


# ===== 전파누리 API (기지국) =====
class BaseStation(BaseModel):
    """이동통신 기지국 정보"""
    lat: Optional[float] = Field(None, alias="LAT", description="위도")
    lon: Optional[float] = Field(None, alias="LON", description="경도")
    frequency: Optional[int] = Field(None, alias="FRQ", description="주파수 (MHz)")
    power: Optional[float] = Field(None, alias="PWR", description="출력 (W)")
    antenna_form: Optional[str] = Field(None, alias="ANT_FORM", description="안테나 형태")
    antenna_gain: Optional[float] = Field(None, alias="ANT_GAIN", description="안테나 이득 (dBi)")
    sea_altitude: Optional[float] = Field(None, alias="SEA_ALT", description="해발고 (m)")
    ground_altitude: Optional[float] = Field(None, alias="GRD_ALT", description="지상고 (m)")
    carrier: Optional[str] = Field(None, alias="CUS_CD", description="통신사")
    park_name: Optional[str] = Field(None, alias="PARK_NM", description="공원명")

    class Config:
        populate_by_name = True


class BaseStationRequest(BaseModel):
    """기지국 조회 요청"""
    park_name: str = Field("ALL", description="공원명 (ALL: 전체)")
    park_type: ParkType = Field(ParkType.NATIONAL, description="공원 유형")
    carrier: CarrierType = Field(CarrierType.ALL, description="통신사")
    service: str = Field("ALL", description="서비스 유형 (2G/3G/4G/5G/ALL)")


class BaseStationResponse(APIResponse):
    """기지국 조회 응답"""
    data: List[BaseStation] = []


# ===== 산악기상정보 API =====
class MountainWeather(BaseModel):
    """산악기상 정보"""
    obs_id: Optional[str] = Field(None, alias="obsid", description="관측소번호")
    obs_name: Optional[str] = Field(None, alias="obsname", description="산 이름")
    local_area: Optional[str] = Field(None, alias="localarea", description="지역코드")
    timestamp: Optional[str] = Field(None, alias="tm", description="관측시간")
    cumulative_precipitation: Optional[float] = Field(None, alias="cprn", description="누적 강수량 (mm)")
    daily_precipitation: Optional[float] = Field(None, alias="rn", description="당일누적 강수량 (mm)")
    humidity_10m: Optional[float] = Field(None, alias="hm10m", description="10m 습도 (%)")
    humidity_2m: Optional[float] = Field(None, alias="hm2m", description="2m 습도 (%)")
    pressure: Optional[float] = Field(None, alias="pa", description="기압 (hPa)")

    class Config:
        populate_by_name = True


class MountainWeatherRequest(BaseModel):
    """산악기상 조회 요청"""
    local_area: Optional[str] = Field(None, description="지역코드 (01:서울, 02:부산...)")
    obs_id: Optional[str] = Field(None, description="관측소번호")
    obs_time: Optional[str] = Field(None, description="관측시간 (예: 202103221952)")


class MountainWeatherResponse(APIResponse):
    """산악기상 조회 응답"""
    data: List[MountainWeather] = []


# ===== 위험지역 POI API =====
class DangerInfo(BaseModel):
    """위험지역 POI 정보"""
    danger_id: Optional[str] = Field(None, description="위험지역 ID")
    danger_type: Optional[str] = Field(None, description="위험 유형")
    location_name: Optional[str] = Field(None, description="위치명")
    lat: Optional[float] = Field(None, description="위도")
    lon: Optional[float] = Field(None, description="경도")
    description: Optional[str] = Field(None, description="설명")
    mountain_name: Optional[str] = Field(None, description="산 이름")

    class Config:
        populate_by_name = True


class DangerInfoRequest(BaseModel):
    """위험지역 조회 요청"""
    mountain_name: Optional[str] = Field(None, description="산 이름")
    danger_type: Optional[str] = Field(None, description="위험 유형")


class DangerInfoResponse(APIResponse):
    """위험지역 조회 응답"""
    data: List[DangerInfo] = []


# ===== 테스트 데이터 생성 =====
class GenerateTestDataRequest(BaseModel):
    """테스트 데이터 생성 요청"""
    park_name: str = Field("지리산", description="대상 공원명")
    save_to_file: bool = Field(True, description="파일 저장 여부")


class GenerateTestDataResponse(APIResponse):
    """테스트 데이터 생성 응답"""
    base_stations_count: int = 0
    weather_data_count: int = 0
    danger_info_count: int = 0
    file_paths: List[str] = []
