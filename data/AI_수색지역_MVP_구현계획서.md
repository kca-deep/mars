# AI 수색지역 선정 MVP 구현 계획서 (v3.0 - 현행화)

> 본 문서는 산악지역 조난자 수색을 위한 AI 기반 Grid별 존재 확률 예측 시스템의 기술 구현 계획서입니다.

**변경 이력**
| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-16 | 초안 작성 |
| 2.0 | 2026-01-16 | 실제 공공데이터 반영, GeoPandas 추가, 피처 고도화 |
| 3.0 | 2026-01-16 | **현행화** - 프로덕션 현황 반영, API 3종 통합, 프로젝트 구조 정비 |

---

## 0. 프로덕션 현황 (현행화)

### 0.1 현재 상태
| 항목 | 상태 | 비고 |
|------|------|------|
| 소스 코드 | **미구현** | `src/` 폴더 없음, 신규 구현 필요 |
| 학습 모델 | 미생성 | `models/` 폴더 없음 |
| 데이터 | **수집 완료** | `data/` 폴더 내 CSV 및 API 문서 존재 |
| UI | 미구현 | Streamlit 대시보드 신규 개발 필요 |

### 0.2 보유 데이터 현황
```
data/
├── 소방청_전국 산악사고 현황_20241231.csv           # 10,134건
├── 소방청_전국 산악사고 구조활동현황_20201231.csv    # 13,189건
├── 03_산악기상정보_기술문서_v1.5(수정본).docx       # 산악기상 API 스펙
├── gateway_swagger_guide.pdf                       # 공공데이터 GW 가이드
├── 산악관련 api.md                                 # API 정보 통합 문서
└── AI_수색지역_MVP_구현계획서.md                    # 본 문서
```

### 0.3 구현 우선순위
1. **Phase 1**: 데이터 파이프라인 + API 클라이언트 구현
2. **Phase 2**: 피처 엔지니어링 + 모델 학습
3. **Phase 3**: Streamlit 대시보드 UI
4. **Phase 4**: 평가 및 최적화

---

## 1. 프로젝트 개요

### 1.1 목표
산악지역 조난자 수색 시 **100m x 100m Grid별 존재 확률을 예측**하여 우선 수색 지역(Top-K)을 추천하는 AI 모델 개발

### 1.2 기술 스택
| 구분 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.10+ |
| ML 프레임워크 | LightGBM | 4.0+ |
| 데이터 처리 | Pandas, NumPy | 2.0+, 1.24+ |
| 지리 데이터 | GeoPandas, Shapely | 0.14+, 2.0+ |
| 좌표계 변환 | PyProj | 3.6+ |
| 평가/검증 | scikit-learn | 1.3+ |
| 지리 연산 | GeoPy | 2.4+ |
| 시각화 | Folium, Plotly | 0.15+, 5.18+ |
| API 통신 | Requests, Tenacity | 2.31+, 8.2+ |
| 웹 UI | Streamlit | 1.29+ |

---

## 2. 외부 API 연동 (3종 통합)

### 2.1 API 목록 및 인증 정보

| API | 엔드포인트 | API Key | 용도 |
|-----|-----------|---------|------|
| 전파누리 (이동통신 기지국) | `https://spectrummap.kr/openapiNew.do` | `l08p79fhk49yf50219g6` | RF 커버리지 |
| 산악기상정보 | `https://apis.data.go.kr/1400377/mtweather` | `o0Z61WpQ8qc3mszVvN%2BVG4ijRUBzNkK%2Fy1AabKm6jM%2FNubQqwgisJnQANrPBQ8hvm3%2BBjiM84GyYVlKCAN9sqw%3D%3D` | 기상 데이터 |
| 위험지역 POI | `https://apis.data.go.kr/B553662/dangerInfoService` | (동일) | 위험지역 정보 |

### 2.2 전파누리 API (이동통신 기지국)

#### 요청 파라미터
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| key | API_KEY | 인증키 |
| searchId | 07 | 산악지역 이동통신 |
| SCH_CD | MOBILE | 기지국 정보 |
| PARK_CD | 1/2/3 | 국립/도립/군립 |
| QUERY | 공원명 또는 ALL | 검색 대상 |
| CUS_CD | SK/KT/LG/ALL | 통신사 |
| SERVICE_CD | 2G/3G/4G/5G/ALL | 서비스 유형 |
| pIndex | 1~ | 페이지 번호 |
| pSize | 100 | 페이지 크기 |

#### 응답 필드
```python
{
    "LAT": 37.xxxx,           # 기지국 위도
    "LON": 128.xxxx,          # 기지국 경도
    "FRQ": 2100,              # 주파수 (MHz)
    "PWR": 20,                # 출력 (W)
    "ANT_FORM": "옴니",        # 안테나 형태
    "ANT_GAIN": 15,           # 안테나 이득 (dBi)
    "SEA_ALT": 850,           # 해발고 (m)
    "GRD_ALT": 30,            # 지상고 (m)
    "CUS_CD": "KT"            # 통신사
}
```

### 2.3 산악기상정보 API

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| ServiceKey | string | Y | 공공데이터포털 인증키 (URL Encode) |
| pageNo | int | Y | 페이지 번호 |
| numOfRows | int | Y | 한 페이지 결과 수 |
| _type | string | N | 응답 형식 (xml/json) |
| localArea | string | N | 지역코드 (01:서울, 02:부산...) |
| obsid | string | N | 관측소번호 |
| tm | string | N | 관측시간 (예: 202103221952) |

#### 응답 필드
```python
{
    "obsid": "1910",              # 관측소번호
    "obsname": "홍천괘방산봉수대", # 산 이름
    "localarea": "1",             # 지역코드
    "tm": "2021-06-30 18:09",     # 관측시간
    "cprn": 10.4,                 # 누적 강수량 (mm)
    "rn": 10.5,                   # 당일누적 강수량 (mm)
    "hm10m": 67.5,                # 10m 습도 (%)
    "hm2m": 71.5,                 # 2m 습도 (%)
    "pa": 1000.7                  # 기압 (hPa)
}
```

### 2.4 위험지역 POI API

#### 엔드포인트 구조
```
Base URL: https://apis.data.go.kr/B553662/dangerInfoService
호출 방식: 공공데이터 GW 표준 (Swagger 기반)
```

#### 공통 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| serviceKey | string | Y | 공공데이터포털 인증키 |
| pageNo | int | Y | 페이지번호 |
| numOfRows | int | Y | 한 페이지 결과 수 |
| returnType | string | N | 응답 타입 (JSON/XML) |

### 2.5 통합 API 클라이언트

```python
# src/data/api_clients.py

import requests
from typing import Optional, Dict, List
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential
from abc import ABC, abstractmethod
import urllib.parse

class BaseAPIClient(ABC):
    """API 클라이언트 기본 클래스"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _request(self, url: str, params: dict) -> dict:
        """재시도 로직이 포함된 API 요청"""
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        pass


class SpectrumMapClient(BaseAPIClient):
    """전파누리 API 클라이언트 (이동통신 기지국)"""
    BASE_URL = "https://spectrummap.kr/openapiNew.do"

    def __init__(self, api_key: str = "l08p79fhk49yf50219g6"):
        self.api_key = api_key

    def fetch_data(
        self,
        park_name: str = "ALL",
        park_type: int = 1,  # 1=국립, 2=도립, 3=군립
        carrier: str = "ALL",
        service: str = "ALL"
    ) -> pd.DataFrame:
        """산악지역 이동통신 기지국 정보 조회"""
        all_data = []
        page = 1
        while True:
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
            data = self._request(self.BASE_URL, params).get("data", [])
            if not data:
                break
            all_data.extend(data)
            page += 1
        return pd.DataFrame(all_data)


class MountainWeatherClient(BaseAPIClient):
    """산악기상정보 API 클라이언트"""
    BASE_URL = "https://apis.data.go.kr/1400377/mtweather/mountListSearch"

    def __init__(self, service_key: str):
        self.service_key = service_key

    def fetch_data(
        self,
        local_area: Optional[str] = None,
        obs_id: Optional[str] = None,
        obs_time: Optional[str] = None,
        num_of_rows: int = 100
    ) -> pd.DataFrame:
        """산악기상 정보 조회"""
        all_data = []
        page = 1
        while True:
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

            result = self._request(self.BASE_URL, params)
            items = result.get("response", {}).get("body", {}).get("items", {}).get("item", [])

            if not items:
                break
            all_data.extend(items if isinstance(items, list) else [items])

            total_count = result.get("response", {}).get("body", {}).get("totalCount", 0)
            if page * num_of_rows >= total_count:
                break
            page += 1

        return pd.DataFrame(all_data)


class DangerInfoClient(BaseAPIClient):
    """위험지역 POI API 클라이언트"""
    BASE_URL = "https://apis.data.go.kr/B553662/dangerInfoService"

    def __init__(self, service_key: str):
        self.service_key = service_key

    def fetch_data(
        self,
        endpoint: str = "getDangerInfoList",
        extra_params: Optional[dict] = None,
        num_of_rows: int = 100
    ) -> pd.DataFrame:
        """위험지역 POI 정보 조회"""
        all_data = []
        page = 1
        while True:
            params = {
                "serviceKey": self.service_key,
                "pageNo": page,
                "numOfRows": num_of_rows,
                "returnType": "JSON"
            }
            if extra_params:
                params.update(extra_params)

            url = f"{self.BASE_URL}/{endpoint}"
            result = self._request(url, params)

            items = result.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            if not items:
                break
            all_data.extend(items if isinstance(items, list) else [items])

            if len(items) < num_of_rows:
                break
            page += 1

        return pd.DataFrame(all_data)
```

---

## 3. 데이터 구조

### 3.1 공공데이터 스키마 (보유 데이터)

#### 산악사고 현황 (10,134건)
```
신고일자        : DATE (YYYY-MM-DD)
신고시각        : TIME (HH:MM)
발생지역_시     : 시/도
발생지역_군     : 시/군/구
발생지역_읍     : 읍/면/동
발생지역_리     : 리/가
사고유형        : 추락/실족/질병/탈진 등
응급처치코드    : 응급처치 유형
처리결과코드    : 병원이송/부상없음/사망 등
구조인원        : INTEGER
```

#### 산악사고 구조활동 (13,189건)
```
신고일자        : DATE
신고시각        : TIME
출동일자        : DATE
출동시각        : TIME
발생지역_시/군/읍/리 : 지역 정보
산명            : 산 이름 (설악산, 북한산 등)
사고유형        : 상세 사고 유형
응급처치코드    : 응급처치 유형
구조인원        : INTEGER
```

### 3.2 사고 통계 분석 결과

#### 사고유형별 분포 (13,189건 기준)
| 사고유형 | 건수 | 비율 |
|----------|------|------|
| 기타사고 | 5,247 | 39.8% |
| 일반추락 | 3,355 | 25.4% |
| 실족추락 | 2,857 | 21.7% |
| 질병환자 | 1,044 | 7.9% |
| 탈진/탈수 | 566 | 4.3% |
| 기타 | 120 | 0.9% |

#### 시간대별 분포
```
시간대    건수    비율
──────────────────────
06-09시   719    5.5%   ← 이른 아침
09-12시  2,464   18.7%  ← 오전 등산
12-15시  4,045   30.7%  ← 점심/오후 피크 ★
15-18시  3,732   28.3%  ← 오후 하산
18-21시  1,756   13.3%  ← 저녁
21-06시   473    3.6%   ← 야간 (위험)
```

**인사이트**:
- 12~15시 사고 집중 (30.7%) → 시간대 피처 중요
- 야간(21~06시) 사고는 적지만 위험도 높음

### 3.3 MVP 입력 데이터 스키마 (목표)

#### Episode Meta
```
episode_id      : 사건 고유 ID
episode_type    : drill / real
agency          : 담당 기관
region_code     : 지역 코드
start_time      : 수색 시작 시각
last_seen_time  : 마지막 관측 시각
last_seen_lat   : 마지막 관측 위도
last_seen_lon   : 마지막 관측 경도
```

#### Grid Definition (100m x 100m)
```
grid_id         : 격자 ID
center_lat/lon  : 격자 중심 좌표
grid_size_m     : 격자 크기 (100m)
crs             : 좌표계 (EPSG:4326)
```

#### Ground Truth
```
episode_id      : FK → episode_meta
gt_lat/lon      : 발견 위치
found_time      : 발견 시각
outcome         : found / not_found
```

---

## 4. 피처 엔지니어링 (7개 카테고리)

### 4.1 피처 목록

#### (A) 거리 기반 피처
```python
dist_to_last_seen          # Grid와 마지막 관측 위치 간 직선 거리 (m)
dist_to_last_seen_log      # 로그 변환 거리
dist_to_last_seen_weighted # 지형 가중 거리
```

#### (B) RF 신호 기반 피처
```python
max_rssi_nearby            # 주변 최대 RSSI
avg_rssi_nearby            # 주변 평균 RSSI
rssi_gradient              # RSSI 변화율 (방향 추정)
observation_count          # RF 관측 횟수
avg_snr                    # 평균 신호 대 잡음비
```

#### (C) 기지국 커버리지 피처 (전파누리 API)
```python
num_stations_in_range      # 커버 가능한 기지국 수
dominant_carrier           # 주요 통신사
avg_station_power          # 평균 기지국 출력 (W)
max_station_power          # 최대 기지국 출력
coverage_score             # 전파 도달 예상 점수
```

#### (D) 지형 피처
```python
elevation_m                # 고도 (m)
slope_deg                  # 경사도 (도)
landcover_encoded          # 토지피복 (FOREST/GRASS/URBAN/WATER)
forest_density             # 산림 밀도 (0~1)
elevation_diff_from_last   # 마지막 관측 대비 고도차
```

#### (E) 시간 피처
```python
time_since_last_seen_min   # 마지막 관측 후 경과 시간 (분)
hour_of_day                # 시간대 (0~23)
is_peak_hour               # 피크 시간대 여부 (12~15시)
is_night                   # 야간 여부 (21~06시)
day_of_week                # 요일
is_weekend                 # 주말 여부
```

#### (F) 기상 피처 (산악기상정보 API)
```python
precipitation_mm           # 강수량 (mm)
cumulative_rain_mm         # 누적 강수량 (mm)
humidity_2m                # 2m 습도 (%)
humidity_10m               # 10m 습도 (%)
pressure_hpa               # 기압 (hPa)
weather_risk_score         # 기상 위험도 종합 점수
is_rainy                   # 강우 여부
high_humidity              # 고습도 여부 (>80%)
```

#### (G) 위험지역 피처 (위험지역 POI API)
```python
near_danger_zone           # 위험지역 인접 여부
danger_zone_distance       # 가장 가까운 위험지역까지 거리
danger_zone_type           # 위험 유형 (낙석, 급경사 등)
historical_accident_count  # 과거 사고 건수 (통계 기반)
```

### 4.2 피처 엔지니어링 코드

```python
# src/features/feature_engineering.py

import pandas as pd
import numpy as np
import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import Point
from typing import Optional

class FeatureEngineer:
    def __init__(
        self,
        grid_df: pd.DataFrame,
        terrain_df: pd.DataFrame,
        station_df: pd.DataFrame,
        weather_df: Optional[pd.DataFrame] = None,
        danger_df: Optional[pd.DataFrame] = None
    ):
        self.grid_df = grid_df
        self.terrain_df = terrain_df
        self.station_df = station_df
        self.weather_df = weather_df
        self.danger_df = danger_df

        # GeoDataFrame 변환
        self.grid_gdf = gpd.GeoDataFrame(
            grid_df,
            geometry=gpd.points_from_xy(grid_df['center_lon'], grid_df['center_lat']),
            crs="EPSG:4326"
        )

    def calculate_distance_features(self, episode_meta: pd.Series) -> pd.DataFrame:
        """거리 기반 피처 계산"""
        last_pos = (episode_meta['last_seen_lat'], episode_meta['last_seen_lon'])

        distances = []
        for _, grid in self.grid_df.iterrows():
            grid_pos = (grid['center_lat'], grid['center_lon'])
            dist = geodesic(last_pos, grid_pos).meters
            distances.append({
                'grid_id': grid['grid_id'],
                'dist_to_last_seen': dist,
                'dist_to_last_seen_log': np.log1p(dist)
            })

        return pd.DataFrame(distances)

    def calculate_coverage_features(self, coverage_radius_m: float = 2000) -> pd.DataFrame:
        """기지국 커버리지 피처 계산 (전파누리 API 기반)"""
        coverage_features = []

        for _, grid in self.grid_df.iterrows():
            grid_pos = (grid['center_lat'], grid['center_lon'])

            stations_in_range = []
            for _, station in self.station_df.iterrows():
                station_pos = (station['LAT'], station['LON'])
                if geodesic(grid_pos, station_pos).meters <= coverage_radius_m:
                    stations_in_range.append(station)

            if stations_in_range:
                stations_df = pd.DataFrame(stations_in_range)
                coverage_features.append({
                    'grid_id': grid['grid_id'],
                    'num_stations_in_range': len(stations_in_range),
                    'avg_station_power': stations_df['PWR'].mean(),
                    'max_station_power': stations_df['PWR'].max(),
                    'coverage_score': len(stations_in_range) * stations_df['PWR'].mean()
                })
            else:
                coverage_features.append({
                    'grid_id': grid['grid_id'],
                    'num_stations_in_range': 0,
                    'avg_station_power': 0,
                    'max_station_power': 0,
                    'coverage_score': 0
                })

        return pd.DataFrame(coverage_features)

    def calculate_weather_features(self, timestamp: str) -> pd.DataFrame:
        """기상 피처 계산 (산악기상정보 API 기반)"""
        if self.weather_df is None or self.weather_df.empty:
            # 기본값 반환
            return pd.DataFrame({
                'grid_id': self.grid_df['grid_id'],
                'precipitation_mm': 0,
                'humidity_2m': 50,
                'pressure_hpa': 1013,
                'weather_risk_score': 0.5
            })

        weather_features = []
        for _, grid in self.grid_df.iterrows():
            # 가장 가까운 관측소 데이터 사용 (단순화)
            weather = self.weather_df.iloc[0] if len(self.weather_df) > 0 else {}

            precip = float(weather.get('rn', 0) or 0)
            humidity = float(weather.get('hm2m', 50) or 50)
            pressure = float(weather.get('pa', 1013) or 1013)

            # 기상 위험도 점수 계산
            risk_score = 0.3 * (precip / 50) + 0.4 * (humidity / 100) + 0.3 * ((1013 - pressure) / 50)
            risk_score = max(0, min(1, risk_score))

            weather_features.append({
                'grid_id': grid['grid_id'],
                'precipitation_mm': precip,
                'humidity_2m': humidity,
                'pressure_hpa': pressure,
                'weather_risk_score': risk_score,
                'is_rainy': 1 if precip > 0 else 0,
                'high_humidity': 1 if humidity > 80 else 0
            })

        return pd.DataFrame(weather_features)

    def calculate_time_features(self, episode_meta: pd.Series) -> pd.DataFrame:
        """시간 피처 계산"""
        from datetime import datetime

        last_seen = pd.to_datetime(episode_meta['last_seen_time'])
        current = pd.to_datetime(episode_meta.get('start_time', datetime.now()))

        time_diff_min = (current - last_seen).total_seconds() / 60
        hour = last_seen.hour
        day_of_week = last_seen.dayofweek

        return pd.DataFrame({
            'grid_id': self.grid_df['grid_id'],
            'time_since_last_seen_min': time_diff_min,
            'hour_of_day': hour,
            'is_peak_hour': 1 if 12 <= hour < 15 else 0,
            'is_night': 1 if hour >= 21 or hour < 6 else 0,
            'day_of_week': day_of_week,
            'is_weekend': 1 if day_of_week >= 5 else 0
        })

    def build_feature_matrix(self, episode_meta: pd.Series) -> pd.DataFrame:
        """전체 피처 매트릭스 생성"""
        # 기본 Grid 정보
        feature_df = self.grid_df[['grid_id', 'center_lat', 'center_lon']].copy()

        # 각 피처 그룹 계산 및 병합
        feature_df = feature_df.merge(
            self.terrain_df, on='grid_id', how='left'
        )
        feature_df = feature_df.merge(
            self.calculate_distance_features(episode_meta), on='grid_id', how='left'
        )
        feature_df = feature_df.merge(
            self.calculate_coverage_features(), on='grid_id', how='left'
        )
        feature_df = feature_df.merge(
            self.calculate_weather_features(episode_meta.get('last_seen_time', '')),
            on='grid_id', how='left'
        )
        feature_df = feature_df.merge(
            self.calculate_time_features(episode_meta), on='grid_id', how='left'
        )

        # 토지피복 원핫 인코딩
        if 'landcover' in feature_df.columns:
            feature_df = pd.get_dummies(feature_df, columns=['landcover'], prefix='lc')

        return feature_df
```

---

## 5. 모델 학습

### 5.1 LightGBM 설정 (MCP 문서 기반)

```python
# src/models/train.py

import lightgbm as lgb
from sklearn.model_selection import GroupKFold
import numpy as np
import pandas as pd
from typing import Optional, Dict, List

class SearchAreaModel:
    def __init__(self):
        self.model = None
        self.feature_names = None
        self.params = {
            "boosting_type": "gbdt",
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "is_unbalance": True,  # 불균형 데이터 처리
            "seed": 42
        }

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        num_boost_round: int = 100
    ):
        """모델 학습"""
        self.feature_names = X_train.columns.tolist()

        train_data = lgb.Dataset(X_train, label=y_train)
        valid_sets = [train_data]

        callbacks = [
            lgb.log_evaluation(period=20),
            lgb.early_stopping(stopping_rounds=10)
        ]

        if X_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)

        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            callbacks=callbacks
        )

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Grid별 존재 확률 예측"""
        return self.model.predict(X)

    def get_top_k_grids(
        self,
        X: pd.DataFrame,
        grid_ids: List[str],
        k: int = 10
    ) -> pd.DataFrame:
        """상위 K개 우선 수색 지역 반환"""
        probs = self.predict_proba(X)

        result = pd.DataFrame({
            'grid_id': grid_ids,
            'probability': probs
        })
        result = result.sort_values('probability', ascending=False)

        return result.head(k)

    def get_feature_importance(self) -> pd.DataFrame:
        """피처 중요도 반환"""
        importance = self.model.feature_importance(importance_type='gain')

        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
        n_splits: int = 5
    ) -> Dict[str, float]:
        """GroupKFold 교차 검증 (Episode 단위 분리)"""
        gkf = GroupKFold(n_splits=n_splits)

        metrics = {'recall@10': [], 'recall@20': [], 'mrr': []}

        for train_idx, val_idx in gkf.split(X, y, groups):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            self.train(X_train, y_train)
            probs = self.predict_proba(X_val)

            # Recall@K 계산
            sorted_idx = np.argsort(probs)[::-1]
            y_val_sorted = y_val.iloc[sorted_idx].values

            total_positive = y_val.sum()
            if total_positive > 0:
                metrics['recall@10'].append(y_val_sorted[:10].sum() / total_positive)
                metrics['recall@20'].append(y_val_sorted[:20].sum() / total_positive)

            # MRR 계산
            positive_ranks = np.where(y_val_sorted == 1)[0] + 1
            mrr = (1 / positive_ranks[0]) if len(positive_ranks) > 0 else 0
            metrics['mrr'].append(mrr)

        return {k: np.mean(v) for k, v in metrics.items()}
```

### 5.2 라벨 생성

```python
# src/models/label_generator.py

import pandas as pd
from geopy.distance import geodesic

def generate_labels(
    grid_df: pd.DataFrame,
    ground_truth: pd.Series,
    positive_radius_m: float = 150
) -> pd.DataFrame:
    """Ground Truth 기반 라벨 생성 (발견 지점 반경 내 Grid = 1)"""
    gt_pos = (ground_truth['gt_lat'], ground_truth['gt_lon'])

    labels = []
    for _, grid in grid_df.iterrows():
        grid_pos = (grid['center_lat'], grid['center_lon'])
        dist = geodesic(gt_pos, grid_pos).meters

        label = 1 if dist <= positive_radius_m else 0
        labels.append({
            'grid_id': grid['grid_id'],
            'label': label,
            'dist_to_gt': dist
        })

    return pd.DataFrame(labels)
```

---

## 6. 평가 체계

### 6.1 평가 지표

```python
# src/evaluation/metrics.py

import numpy as np

def recall_at_k(y_true: np.ndarray, y_pred_proba: np.ndarray, k: int) -> float:
    """상위 K개 예측 내 정답 비율"""
    sorted_idx = np.argsort(y_pred_proba)[::-1][:k]
    return y_true[sorted_idx].sum() / y_true.sum() if y_true.sum() > 0 else 0

def mrr(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    """Mean Reciprocal Rank"""
    sorted_idx = np.argsort(y_pred_proba)[::-1]
    y_sorted = y_true[sorted_idx]
    positive_ranks = np.where(y_sorted == 1)[0] + 1
    return (1 / positive_ranks[0]) if len(positive_ranks) > 0 else 0

def search_area_reduction_at_k(total_grids: int, k: int, recall_at_k_value: float) -> float:
    """수색 면적 축소율"""
    if recall_at_k_value == 0:
        return 0
    reduced_area = k / recall_at_k_value
    return 1 - (reduced_area / total_grids)

def evaluate_model(y_true: np.ndarray, y_pred_proba: np.ndarray, total_grids: int) -> dict:
    """종합 평가"""
    r10 = recall_at_k(y_true, y_pred_proba, 10)
    r20 = recall_at_k(y_true, y_pred_proba, 20)

    return {
        'recall@10': r10,
        'recall@20': r20,
        'mrr': mrr(y_true, y_pred_proba),
        'area_reduction@10': search_area_reduction_at_k(total_grids, 10, r10),
        'area_reduction@20': search_area_reduction_at_k(total_grids, 20, r20)
    }
```

### 6.2 성공 기준 (Go/No-Go)

| 지표 | 베이스라인 예상 | MVP 목표 | Go 조건 |
|------|----------------|----------|---------|
| Recall@10 | ~0.3 | ≥0.5 | +20%p 이상 |
| Recall@20 | ~0.5 | ≥0.7 | +20%p 이상 |
| MRR | ~0.2 | ≥0.4 | +0.2 이상 |
| 면적 축소율@10 | 기준 | ≥30% | 달성 시 Go |

---

## 7. Streamlit 대시보드 (MCP 문서 기반)

### 7.1 UI 구성
```
┌─────────────────────────────────────────────────────────────┐
│  AI 수색지역 선정 시스템                                      │
├─────────────────────────────────────────────────────────────┤
│  [사이드바]                  │  [메인 영역]                  │
│  ┌───────────────┐         │  ┌─────────────────────────┐  │
│  │ 에피소드 선택   │         │  │                         │  │
│  │ ┌───────────┐ │         │  │      Heatmap           │  │
│  │ │ Dropdown  │ │         │  │      (Folium 지도)      │  │
│  │ └───────────┘ │         │  │                         │  │
│  │               │         │  └─────────────────────────┘  │
│  │ 설정          │         │                               │
│  │ Top-K: [10]   │         │  ┌─────────────────────────┐  │
│  │ 반경: [500]m  │         │  │  Top-K 수색 우선지역     │  │
│  │               │         │  │  (테이블 + 차트)         │  │
│  │ [예측 실행]   │         │  └─────────────────────────┘  │
│  │               │         │                               │
│  │ 모델 정보     │         │  ┌─────────────────────────┐  │
│  │ - Recall@10   │         │  │  피처 중요도             │  │
│  │ - MRR         │         │  │  (Bar Chart)            │  │
│  └───────────────┘         │  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Streamlit 앱 코드

```python
# src/app/streamlit_app.py

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import plotly.express as px
from pathlib import Path
import sys

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

# 페이지 설정
st.set_page_config(
    page_title="AI 수색지역 선정 시스템",
    page_icon="🔍",
    layout="wide"
)

@st.cache_data
def load_sample_data():
    """샘플 데이터 로딩 (실제 구현 시 DataLoader 사용)"""
    # Grid 데이터 샘플
    np.random.seed(42)
    grid_df = pd.DataFrame({
        'grid_id': [f'GRID-100M-{i:04d}' for i in range(100)],
        'center_lat': 37.5 + np.random.randn(100) * 0.01,
        'center_lon': 127.0 + np.random.randn(100) * 0.01
    })
    return {'grid_df': grid_df}

def create_heatmap(predictions: pd.DataFrame, center: list, gt: dict = None):
    """Folium Heatmap 생성"""
    m = folium.Map(location=center, zoom_start=14)

    # Heatmap 레이어
    heat_data = [
        [row['center_lat'], row['center_lon'], row['probability']]
        for _, row in predictions.iterrows()
    ]
    HeatMap(heat_data, radius=15, blur=10).add_to(m)

    # 마지막 관측 위치
    folium.Marker(
        center,
        popup="마지막 관측 위치",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)

    # Top-10 마커
    top_10 = predictions.head(10)
    for idx, row in top_10.iterrows():
        folium.CircleMarker(
            [row['center_lat'], row['center_lon']],
            radius=10,
            color='red',
            fill=True,
            popup=f"순위: {idx+1}, 확률: {row['probability']:.2%}"
        ).add_to(m)

    # Ground Truth
    if gt:
        folium.Marker(
            [gt['lat'], gt['lon']],
            popup="실제 발견 위치",
            icon=folium.Icon(color='green', icon='ok-sign')
        ).add_to(m)

    return m

def main():
    st.title("AI 수색지역 선정 시스템")
    st.markdown("산악지역 조난자 수색을 위한 AI 기반 우선 수색 지역 추천")

    # 데이터 로딩
    data = load_sample_data()

    # 사이드바
    with st.sidebar:
        st.header("설정")

        # 파라미터 설정
        top_k = st.slider("Top-K (추천 지역 수)", 5, 30, 10)

        st.divider()

        # 예측 실행 버튼
        run_prediction = st.button("예측 실행", type="primary", use_container_width=True)

        st.divider()

        # 모델 성능
        st.header("모델 성능 (목표)")
        col1, col2 = st.columns(2)
        col1.metric("Recall@10", "≥0.50")
        col2.metric("MRR", "≥0.40")

    # 메인 영역
    if run_prediction:
        # 예측 실행 (데모용)
        predictions = data['grid_df'].copy()
        np.random.seed(42)
        predictions['probability'] = np.random.beta(2, 5, len(predictions))
        predictions = predictions.sort_values('probability', ascending=False).reset_index(drop=True)

        center = [predictions['center_lat'].mean(), predictions['center_lon'].mean()]

        # 레이아웃
        col_map, col_info = st.columns([2, 1])

        with col_map:
            st.subheader("수색 우선순위 Heatmap")
            heatmap = create_heatmap(predictions, center)
            st_folium(heatmap, width=700, height=500)

        with col_info:
            st.subheader(f"Top-{top_k} 수색 우선지역")
            top_k_df = predictions.head(top_k)[['grid_id', 'probability']].copy()
            top_k_df['probability'] = top_k_df['probability'].apply(lambda x: f"{x:.2%}")
            top_k_df.index = range(1, len(top_k_df) + 1)
            st.dataframe(top_k_df, use_container_width=True)

        # 피처 중요도 (데모)
        st.divider()
        st.subheader("피처 중요도")
        feature_imp = pd.DataFrame({
            'feature': ['dist_to_last_seen', 'coverage_score', 'elevation_m',
                       'weather_risk_score', 'is_peak_hour', 'num_stations'],
            'importance': [0.35, 0.22, 0.18, 0.12, 0.08, 0.05]
        })
        fig = px.bar(feature_imp, x='importance', y='feature', orientation='h',
                    color='importance', color_continuous_scale='Reds')
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
```

### 7.3 실행 방법
```bash
# 의존성 설치
pip install streamlit streamlit-folium plotly folium

# 앱 실행
streamlit run src/app/streamlit_app.py

# 브라우저 접속
# http://localhost:8501
```

---

## 8. 프로젝트 구조 (현행화)

```
mars/
├── src/                            # ★ 신규 생성 필요
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── api_clients.py          # 3종 API 통합 클라이언트
│   │   ├── data_loader.py          # 데이터 로딩
│   │   └── preprocessor.py         # 전처리
│   ├── features/
│   │   ├── __init__.py
│   │   └── feature_engineering.py  # 피처 엔지니어링
│   ├── models/
│   │   ├── __init__.py
│   │   ├── baseline.py             # 베이스라인 모델
│   │   ├── train.py                # LightGBM 학습
│   │   └── label_generator.py      # 라벨 생성
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── metrics.py              # 평가 지표
│   ├── visualization/
│   │   ├── __init__.py
│   │   └── heatmap.py              # Heatmap 시각화
│   └── app/
│       ├── __init__.py
│       └── streamlit_app.py        # Streamlit 대시보드
├── notebooks/                       # ★ 신규 생성 필요
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_evaluation.ipynb
├── data/                            # ✅ 존재
│   ├── 소방청_전국 산악사고 현황_20241231.csv
│   ├── 소방청_전국 산악사고 구조활동현황_20201231.csv
│   ├── 03_산악기상정보_기술문서_v1.5(수정본).docx
│   ├── gateway_swagger_guide.pdf
│   ├── 산악관련 api.md
│   └── AI_수색지역_MVP_구현계획서.md
├── models/                          # ★ 신규 생성 필요
├── config/
│   └── config.yaml                  # API 키 등 설정
├── tests/
├── requirements.txt
├── CLAUDE.md                        # ✅ 존재
└── README.md
```

---

## 9. 의존성 패키지

```txt
# requirements.txt

# Core
pandas>=2.0.0
numpy>=1.24.0

# ML
lightgbm>=4.0.0
scikit-learn>=1.3.0

# Geo
geopandas>=0.14.0
geopy>=2.4.0
shapely>=2.0.0
folium>=0.15.0
pyproj>=3.6.0

# API & Utils
requests>=2.31.0
pyyaml>=6.0
python-dotenv>=1.0.0
tenacity>=8.2.0

# Visualization
matplotlib>=3.7.0
plotly>=5.18.0

# Web UI
streamlit>=1.29.0
streamlit-folium>=0.15.0

# Data
openpyxl>=3.1.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
```

---

## 10. 구현 로드맵

### Phase 1: 데이터 파이프라인 (1주차)
- [ ] `src/` 디렉토리 구조 생성
- [ ] API 클라이언트 구현 및 테스트
- [ ] CSV 데이터 로더 구현
- [ ] 전처리 파이프라인 구축

### Phase 2: 피처 엔지니어링 (2주차)
- [ ] Grid 생성 로직 구현
- [ ] 7개 카테고리 피처 계산 함수 구현
- [ ] 피처 매트릭스 생성 검증

### Phase 3: 모델 학습 (3주차)
- [ ] 베이스라인 모델 구현
- [ ] LightGBM 학습 파이프라인 구현
- [ ] GroupKFold 교차 검증 실행
- [ ] 하이퍼파라미터 튜닝

### Phase 4: UI 및 평가 (4주차)
- [ ] Streamlit 대시보드 구현
- [ ] 평가 지표 구현 및 리포트 생성
- [ ] 통합 테스트 및 문서화

---

## 11. 다음 단계 (MVP 이후)

1. **데이터 확대**: 실제 구조 사례 데이터 확보
2. **실시간 연동**: RF 관측 실시간 스트리밍
3. **드론 연계**: 드론 이동국 통합
4. **랭킹 모델**: LambdaMART 등 Learning-to-Rank 적용
5. **운영 시스템**: API 서버 배포

---

*작성일: 2026-01-16*
*버전: 3.0 (현행화)*
