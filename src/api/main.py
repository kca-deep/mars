"""
FastAPI 메인 애플리케이션
- 외부 API 연동 테스트
- 테스트 데이터 생성
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from datetime import datetime
from typing import Optional
import pandas as pd

from src.data.api_clients import (
    SpectrumMapClient,
    MountainWeatherClient,
    DangerInfoClient
)
from src.data.mock_data import MockDataGenerator
from src.api.schemas import (
    APIResponse,
    BaseStationRequest, BaseStationResponse, BaseStation,
    MountainWeatherRequest, MountainWeatherResponse, MountainWeather,
    DangerInfoRequest, DangerInfoResponse, DangerInfo,
    GenerateTestDataRequest, GenerateTestDataResponse,
    ParkType, CarrierType
)
from config.settings import get_settings

settings = get_settings()

# API 클라이언트 인스턴스
spectrum_client: Optional[SpectrumMapClient] = None
weather_client: Optional[MountainWeatherClient] = None
danger_client: Optional[DangerInfoClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    global spectrum_client, weather_client, danger_client

    # 클라이언트 초기화
    spectrum_client = SpectrumMapClient(api_key=settings.SPECTRUM_MAP_API_KEY)
    weather_client = MountainWeatherClient(service_key=settings.PUBLIC_DATA_API_KEY)
    danger_client = DangerInfoClient(service_key=settings.PUBLIC_DATA_API_KEY)

    print("API 클라이언트 초기화 완료")
    yield
    print("애플리케이션 종료")


app = FastAPI(
    title="AI 수색지역 선정 MVP - API 테스트",
    description="산악지역 외부 API 연동 및 테스트 데이터 생성",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 헬스체크 =====
@app.get("/", response_model=APIResponse)
async def root():
    """API 헬스체크"""
    return APIResponse(
        success=True,
        message="AI 수색지역 선정 MVP API 서버 가동 중",
        data={"version": "1.0.0", "timestamp": datetime.now().isoformat()}
    )


@app.get("/health", response_model=APIResponse)
async def health_check():
    """상세 헬스체크"""
    return APIResponse(
        success=True,
        message="OK",
        data={
            "spectrum_client": spectrum_client is not None,
            "weather_client": weather_client is not None,
            "danger_client": danger_client is not None
        }
    )


# ===== 전파누리 API (기지국) =====
@app.get("/api/v1/stations", response_model=BaseStationResponse)
async def get_base_stations(
    park_name: str = "ALL",
    park_type: int = 1,
    carrier: str = "ALL",
    service: str = "ALL"
):
    """
    이동통신 기지국 정보 조회 (전파누리 API)

    - park_name: 공원명 (ALL: 전체, 지리산, 설악산 등)
    - park_type: 1=국립, 2=도립, 3=군립
    - carrier: SK/KT/LG/ALL
    - service: 2G/3G/4G/5G/ALL
    """
    try:
        data = await spectrum_client.fetch_data(
            park_name=park_name,
            park_type=park_type,
            carrier=carrier,
            service=service,
            max_pages=3
        )

        stations = [BaseStation(**item) for item in data]

        return BaseStationResponse(
            success=True,
            message=f"기지국 정보 {len(stations)}건 조회 완료",
            data=stations,
            count=len(stations)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전파누리 API 오류: {str(e)}")


@app.get("/api/v1/stations/{park_name}", response_model=BaseStationResponse)
async def get_stations_by_park(park_name: str):
    """특정 공원의 기지국 정보 조회"""
    try:
        data = await spectrum_client.get_stations_by_park(park_name)
        stations = [BaseStation(**item) for item in data]

        return BaseStationResponse(
            success=True,
            message=f"{park_name} 기지국 정보 {len(stations)}건 조회 완료",
            data=stations,
            count=len(stations)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전파누리 API 오류: {str(e)}")


# ===== 산악기상정보 API =====
@app.get("/api/v1/weather", response_model=MountainWeatherResponse)
async def get_mountain_weather(
    local_area: Optional[str] = None,
    obs_id: Optional[str] = None,
    obs_time: Optional[str] = None
):
    """
    산악기상 정보 조회

    - local_area: 지역코드 (01:서울, 02:부산, 03:대구, 04:인천...)
    - obs_id: 관측소번호
    - obs_time: 관측시간 (예: 202103221952)
    """
    try:
        data = await weather_client.fetch_data(
            local_area=local_area,
            obs_id=obs_id,
            obs_time=obs_time
        )

        weather_list = [MountainWeather(**item) for item in data]

        return MountainWeatherResponse(
            success=True,
            message=f"산악기상 정보 {len(weather_list)}건 조회 완료",
            data=weather_list,
            count=len(weather_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"산악기상 API 오류: {str(e)}")


@app.get("/api/v1/weather/area/{area_code}", response_model=MountainWeatherResponse)
async def get_weather_by_area(area_code: str):
    """지역별 산악기상 정보 조회"""
    try:
        data = await weather_client.get_weather_by_area(area_code)
        weather_list = [MountainWeather(**item) for item in data]

        return MountainWeatherResponse(
            success=True,
            message=f"지역코드 {area_code} 산악기상 정보 {len(weather_list)}건 조회 완료",
            data=weather_list,
            count=len(weather_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"산악기상 API 오류: {str(e)}")


# ===== 위험지역 POI API =====
@app.get("/api/v1/danger", response_model=DangerInfoResponse)
async def get_danger_info():
    """위험지역 POI 정보 조회"""
    try:
        data = await danger_client.fetch_data()
        danger_list = [DangerInfo(**item) for item in data]

        return DangerInfoResponse(
            success=True,
            message=f"위험지역 정보 {len(danger_list)}건 조회 완료",
            data=danger_list,
            count=len(danger_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"위험지역 API 오류: {str(e)}")


# ===== 테스트 데이터 생성 =====
async def save_test_data(
    park_name: str,
    stations: list,
    weather: list,
    danger: list
) -> list:
    """테스트 데이터를 파일로 저장 (백그라운드 태스크)"""
    base_path = Path(__file__).parent.parent.parent / "data" / "generated"
    base_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_paths = []

    # 기지국 데이터 저장
    if stations:
        stations_file = base_path / f"stations_{park_name}_{timestamp}.json"
        with open(stations_file, "w", encoding="utf-8") as f:
            json.dump(stations, f, ensure_ascii=False, indent=2)
        file_paths.append(str(stations_file))

        # CSV로도 저장
        stations_csv = base_path / f"stations_{park_name}_{timestamp}.csv"
        df = pd.DataFrame(stations)
        df.to_csv(stations_csv, index=False, encoding="utf-8-sig")
        file_paths.append(str(stations_csv))

    # 기상 데이터 저장
    if weather:
        weather_file = base_path / f"weather_{timestamp}.json"
        with open(weather_file, "w", encoding="utf-8") as f:
            json.dump(weather, f, ensure_ascii=False, indent=2)
        file_paths.append(str(weather_file))

        weather_csv = base_path / f"weather_{timestamp}.csv"
        df = pd.DataFrame(weather)
        df.to_csv(weather_csv, index=False, encoding="utf-8-sig")
        file_paths.append(str(weather_csv))

    # 위험지역 데이터 저장
    if danger:
        danger_file = base_path / f"danger_{timestamp}.json"
        with open(danger_file, "w", encoding="utf-8") as f:
            json.dump(danger, f, ensure_ascii=False, indent=2)
        file_paths.append(str(danger_file))

        danger_csv = base_path / f"danger_{timestamp}.csv"
        df = pd.DataFrame(danger)
        df.to_csv(danger_csv, index=False, encoding="utf-8-sig")
        file_paths.append(str(danger_csv))

    return file_paths


@app.post("/api/v1/generate-test-data", response_model=GenerateTestDataResponse)
async def generate_test_data(
    request: GenerateTestDataRequest,
    background_tasks: BackgroundTasks
):
    """
    테스트 데이터 생성 및 저장

    3개 외부 API를 호출하여 테스트 데이터를 수집하고 파일로 저장합니다.
    """
    try:
        # 1. 기지국 데이터 수집
        print(f"기지국 데이터 수집 중... (공원: {request.park_name})")
        stations_data = await spectrum_client.fetch_data(
            park_name=request.park_name,
            max_pages=2
        )

        # 2. 산악기상 데이터 수집
        print("산악기상 데이터 수집 중...")
        weather_data = await weather_client.fetch_data(max_pages=2)

        # 3. 위험지역 데이터 수집
        print("위험지역 데이터 수집 중...")
        danger_data = await danger_client.fetch_data(max_pages=2)

        file_paths = []

        # 4. 파일 저장
        if request.save_to_file:
            file_paths = await save_test_data(
                park_name=request.park_name,
                stations=stations_data,
                weather=weather_data,
                danger=danger_data
            )

        return GenerateTestDataResponse(
            success=True,
            message="테스트 데이터 생성 완료",
            base_stations_count=len(stations_data),
            weather_data_count=len(weather_data),
            danger_info_count=len(danger_data),
            file_paths=file_paths,
            data={
                "park_name": request.park_name,
                "stations_sample": stations_data[:3] if stations_data else [],
                "weather_sample": weather_data[:3] if weather_data else [],
                "danger_sample": danger_data[:3] if danger_data else []
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 데이터 생성 오류: {str(e)}")


@app.get("/api/v1/generate-test-data/{park_name}", response_model=GenerateTestDataResponse)
async def generate_test_data_get(park_name: str):
    """GET 방식으로 테스트 데이터 생성 (간편 호출)"""
    request = GenerateTestDataRequest(park_name=park_name, save_to_file=True)
    return await generate_test_data(request, BackgroundTasks())


# ===== 전체 API 테스트 =====
@app.get("/api/v1/test-all", response_model=APIResponse)
async def test_all_apis():
    """모든 외부 API 연결 테스트"""
    results = {
        "spectrum_map": {"status": "pending", "message": ""},
        "mountain_weather": {"status": "pending", "message": ""},
        "danger_info": {"status": "pending", "message": ""}
    }

    # 전파누리 API 테스트
    try:
        data = await spectrum_client.fetch_data(park_name="지리산", max_pages=1)
        results["spectrum_map"] = {
            "status": "success",
            "message": f"{len(data)}건 조회",
            "sample": data[0] if data else None
        }
    except Exception as e:
        results["spectrum_map"] = {"status": "error", "message": str(e)}

    # 산악기상 API 테스트
    try:
        data = await weather_client.fetch_data(max_pages=1)
        results["mountain_weather"] = {
            "status": "success",
            "message": f"{len(data)}건 조회",
            "sample": data[0] if data else None
        }
    except Exception as e:
        results["mountain_weather"] = {"status": "error", "message": str(e)}

    # 위험지역 API 테스트
    try:
        data = await danger_client.fetch_data(max_pages=1)
        results["danger_info"] = {
            "status": "success",
            "message": f"{len(data)}건 조회",
            "sample": data[0] if data else None
        }
    except Exception as e:
        results["danger_info"] = {"status": "error", "message": str(e)}

    all_success = all(r["status"] == "success" for r in results.values())

    return APIResponse(
        success=all_success,
        message="API 테스트 완료" if all_success else "일부 API 연결 실패",
        data=results
    )


# ===== Mock 데이터 생성 =====
@app.post("/api/v1/mock/generate", response_model=APIResponse)
async def generate_mock_data(
    park_name: str = "지리산",
    save_to_file: bool = True
):
    """
    Mock 테스트 데이터 생성 (외부 API 차단 시 사용)

    실제 API 대신 현실적인 테스트 데이터를 생성합니다.
    """
    try:
        generator = MockDataGenerator(seed=42)
        data = generator.generate_all_test_data(park_name)

        file_paths = []

        if save_to_file:
            base_path = Path(__file__).parent.parent.parent / "data" / "generated"
            base_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # JSON 저장
            for key in ["base_stations", "mountain_weather", "danger_info", "grids", "episodes", "ground_truths"]:
                file_path = base_path / f"mock_{key}_{park_name}_{timestamp}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data[key], f, ensure_ascii=False, indent=2)
                file_paths.append(str(file_path))

                # CSV 저장
                csv_path = base_path / f"mock_{key}_{park_name}_{timestamp}.csv"
                df = pd.DataFrame(data[key])
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                file_paths.append(str(csv_path))

        return APIResponse(
            success=True,
            message=f"Mock 데이터 생성 완료 ({park_name})",
            data={
                "metadata": data["metadata"],
                "samples": {
                    "base_station": data["base_stations"][0] if data["base_stations"] else None,
                    "weather": data["mountain_weather"][0] if data["mountain_weather"] else None,
                    "danger": data["danger_info"][0] if data["danger_info"] else None,
                    "grid": data["grids"][0] if data["grids"] else None,
                    "episode": data["episodes"][0] if data["episodes"] else None
                },
                "file_paths": file_paths
            },
            count=sum(data["metadata"]["counts"].values())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mock 데이터 생성 오류: {str(e)}")


@app.get("/api/v1/mock/stations/{park_name}", response_model=BaseStationResponse)
async def get_mock_stations(park_name: str, count: int = 50):
    """Mock 기지국 데이터 조회"""
    generator = MockDataGenerator()
    data = generator.generate_base_stations(park_name, count)
    stations = [BaseStation(**item) for item in data]

    return BaseStationResponse(
        success=True,
        message=f"Mock 기지국 데이터 {len(stations)}건 생성",
        data=stations,
        count=len(stations)
    )


@app.get("/api/v1/mock/weather", response_model=MountainWeatherResponse)
async def get_mock_weather(count: int = 30, local_area: Optional[str] = None):
    """Mock 기상 데이터 조회"""
    generator = MockDataGenerator()
    data = generator.generate_mountain_weather(count, local_area)
    weather_list = [MountainWeather(**item) for item in data]

    return MountainWeatherResponse(
        success=True,
        message=f"Mock 기상 데이터 {len(weather_list)}건 생성",
        data=weather_list,
        count=len(weather_list)
    )


@app.get("/api/v1/mock/danger", response_model=DangerInfoResponse)
async def get_mock_danger(count: int = 40):
    """Mock 위험지역 데이터 조회"""
    generator = MockDataGenerator()
    data = generator.generate_danger_info(count)
    danger_list = [DangerInfo(**item) for item in data]

    return DangerInfoResponse(
        success=True,
        message=f"Mock 위험지역 데이터 {len(danger_list)}건 생성",
        data=danger_list,
        count=len(danger_list)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
