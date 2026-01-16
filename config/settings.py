"""
API 설정 및 키 관리
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 전파누리 API
    SPECTRUM_MAP_API_KEY: str = "l08p79fhk49yf50219g6"
    SPECTRUM_MAP_BASE_URL: str = "https://spectrummap.kr/openapiNew.do"

    # 공공데이터포털 API (산악기상정보, 위험지역 POI 공용) - URL 디코딩된 키
    PUBLIC_DATA_API_KEY: str = "o0Z61WpQ8qc3mszVvN+VG4ijRUBzNkK/y1AabKm6jM/NubQqwgisJnQANrPBQ8hvm3+BjiM84GyYVlKCAN9sqw=="

    # SGIS 지오코딩 API
    SGIS_CONSUMER_KEY: str = "4c2bd9960b8244fe885b"  # 서비스 ID
    SGIS_CONSUMER_SECRET: str = "4ef7f08f127e4dfcb7f6"  # 보안키

    # 산악기상정보 API
    MOUNTAIN_WEATHER_BASE_URL: str = "https://apis.data.go.kr/1400377/mtweather/mountListSearch"

    # 위험지역 POI API
    DANGER_INFO_BASE_URL: str = "https://apis.data.go.kr/B553662/dangerInfoService"

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
