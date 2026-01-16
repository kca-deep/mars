# AI 수색지역 선정 MVP 구현 계획서 (v4.0 - 현행화)

> 본 문서는 산악지역 조난자 수색을 위한 AI 기반 Grid별 존재 확률 예측 시스템의 기술 구현 계획서입니다.

**변경 이력**
| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-16 | 초안 작성 |
| 2.0 | 2026-01-16 | 실제 공공데이터 반영, GeoPandas 추가, 피처 고도화 |
| 3.0 | 2026-01-16 | 현행화 - 프로덕션 현황 반영, API 3종 통합, 프로젝트 구조 정비 |
| 4.0 | 2026-01-16 | **Phase 1 완료** - API 클라이언트 구현, 지오코딩 완료, 지도 API 선정 |

---

## 0. 프로덕션 현황 (현행화)

### 0.1 현재 상태
| 항목 | 상태 | 비고 |
|------|------|------|
| API 클라이언트 | **✅ 완료** | 전파누리, 산악기상, 위험지역, SGIS 지오코딩 |
| 데이터 전처리 | **✅ 완료** | 지오코딩 98.9% 성공 (2,595개 주소) |
| 학습 모델 | 미생성 | Phase 2에서 진행 |
| UI | 미구현 | Streamlit + Pydeck 선정 |

### 0.2 보유 데이터 현황
```
data/
├── 소방청_전국 산악사고 현황_20241231.xlsx           # 10,134건 (2024년)
├── 소방청_전국 산악사고 구조활동현황_20201231.xlsx    # 13,189건 (2020년)
├── 03_산악기상정보_기술문서_v1.5(수정본).docx       # 산악기상 API 스펙
├── gateway_swagger_guide.pdf                       # 공공데이터 GW 가이드
├── 산악관련 api.md                                 # API 정보 통합 문서
├── AI_수색지역_MVP_구현계획서.md                    # 본 문서
└── generated/
    ├── 산악사고_지오코딩_20260116_165113.xlsx       # ✅ 좌표 포함 (2024)
    ├── 구조활동현황_지오코딩_20260116_171152.xlsx   # ✅ 좌표 포함 (2020)
    └── 주소_좌표_매핑_통합_20260116_171152.xlsx     # ✅ 주소-좌표 캐시
```

### 0.3 지오코딩 결과 요약
| 데이터 | 레코드 | 고유주소 | 성공 | 성공률 |
|--------|--------|----------|------|--------|
| 산악사고현황 (2024) | 10,134 | 1,845 | 1,841 | 99.8% |
| 구조활동현황 (2020) | 13,189 | 750 (신규) | 725 | 96.7% |
| **통합** | **23,323** | **2,595** | **2,566** | **98.9%** |

### 0.4 구현 우선순위
1. **Phase 1**: 데이터 파이프라인 + API 클라이언트 ✅ **완료**
2. **Phase 2**: 피처 엔지니어링 + 모델 학습 ← **현재 단계**
3. **Phase 3**: Streamlit 대시보드 UI
4. **Phase 4**: 평가 및 최적화

---

## 1. 프로젝트 개요

### 1.1 목표
산악지역 조난자 수색 시 **H3 Grid별 존재 확률을 예측**하여 우선 수색 지역(Top-K)을 추천하는 AI 모델 개발

### 1.2 기술 스택
| 구분 | 기술 | 버전 | 상태 |
|------|------|------|------|
| 언어 | Python | 3.10+ | ✅ |
| ML 프레임워크 | LightGBM | 4.0+ | 예정 |
| 데이터 처리 | Pandas, NumPy | 2.0+, 1.24+ | ✅ |
| 지리 데이터 | GeoPandas, H3 | 0.14+, 4.0+ | 예정 |
| 좌표계 변환 | PyProj | 3.6+ | 예정 |
| 지오코딩 | SGIS API | - | ✅ |
| API 통신 | httpx, Tenacity | 0.27+, 8.2+ | ✅ |
| **지도 시각화** | **Pydeck (Deck.gl)** | 0.8+ | **선정** |
| 웹 UI | Streamlit | 1.29+ | 예정 |

---

## 2. 외부 API 연동 (4종 통합)

### 2.1 API 목록 및 상태

| API | 엔드포인트 | 상태 | 용도 |
|-----|-----------|------|------|
| 전파누리 (기지국) | `spectrummap.kr` | ✅ 완료 | RF 커버리지 |
| 산악기상정보 | `apis.data.go.kr` | ✅ 완료 | 기상 데이터 |
| 위험지역 POI | `apis.data.go.kr` | ✅ 완료 | 위험지역 정보 |
| **SGIS 지오코딩** | `sgisapi.mods.go.kr` | ✅ 완료 | 주소→좌표 변환 |

### 2.2 SGIS 지오코딩 API (신규)

#### 인증 정보
| 항목 | 값 |
|------|-----|
| Consumer Key (서비스 ID) | `4c2bd9960b8244fe885b` |
| Consumer Secret (보안키) | `4ef7f08f127e4dfcb7f6` |
| Base URL | `https://sgisapi.mods.go.kr/OpenAPI3` |

#### 주요 기능
```python
# src/data/sgis_client.py
class SGISClient:
    async def geocode(address: str) -> GeocodingResult:
        """주소 → WGS84 좌표 변환"""

    async def reverse_geocode(x: float, y: float) -> Dict:
        """좌표 → 주소 변환"""

    async def batch_geocode(addresses: List[str]) -> List[GeocodingResult]:
        """일괄 지오코딩 (rate limiting 포함)"""
```

### 2.3 전파누리 API (이동통신 기지국)

#### 요청 파라미터
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| key | `l08p79fhk49yf50219g6` | 인증키 |
| searchId | 07 | 산악지역 이동통신 |
| SCH_CD | MOBILE | 기지국 정보 |
| PARK_CD | 1/2/3 | 국립/도립/군립 |

#### 응답 필드
```python
{
    "LAT": 37.xxxx,           # 기지국 위도
    "LON": 128.xxxx,          # 기지국 경도
    "FRQ": 2100.5,            # 주파수 (MHz) - float 타입
    "PWR": 20,                # 출력 (W)
    "SEA_ALT": 850,           # 해발고 (m)
    "CUS_CD": "KT"            # 통신사
}
```

### 2.4 산악기상정보 API

#### 응답 필드
```python
{
    "obsid": "1910",              # 관측소번호
    "obsname": "홍천괘방산봉수대", # 산 이름
    "tm": "2021-06-30 18:09",     # 관측시간
    "cprn": 10.4,                 # 누적 강수량 (mm)
    "rn": 10.5,                   # 당일누적 강수량 (mm)
    "hm10m": 67.5,                # 10m 습도 (%)
    "pa": 1000.7                  # 기압 (hPa)
}
```

### 2.5 위험지역 POI API

> **참고**: XML 응답을 JSON으로 자동 변환 (xmltodict 사용)

#### 응답 필드
```python
{
    "poiId": "POI-001",           # POI ID
    "frtrlId": "TRAIL-001",       # 등산로 ID
    "frtrlNm": "북한산 백운대코스", # 등산로명
    "lat": 37.xxxx,               # 위도
    "lot": 127.xxxx,              # 경도
    "aslAltide": 850,             # 해발고도 (m)
    "plcNm": "급경사 구간"         # 장소명
}
```

---

## 3. 공간 데이터 처리 (H3 그리드)

### 3.1 H3 그리드 시스템

H3는 Uber가 개발한 **육각형 기반 지리 인덱싱 시스템**입니다.

#### 좌표 → H3 인덱스 변환
```python
import h3

lat, lon = 37.5665, 126.9780  # 좌표
resolution = 8  # 해상도

h3_index = h3.latlng_to_cell(lat, lon, resolution)
# 결과: "8830e1d6c3fffff"
```

#### 해상도별 셀 크기
| 해상도 | 셀 면적 | 변 길이 | 용도 |
|--------|---------|---------|------|
| 7 | ~5.16 km² | ~1.2 km | 광역 분석 |
| **8** | **~0.74 km²** | **~460 m** | **산악 수색 적합** |
| 9 | ~0.10 km² | ~174 m | 정밀 분석 |

#### 육각형의 장점
```
정사각형: 중심→이웃 거리 불균등 (대각선이 더 멀다)
육각형:   중심→이웃 거리 모두 동일 (6개 이웃이 등거리)
```

### 3.2 공간 조인 방식

```python
# 효율적인 H3 기반 조인
accidents["h3"] = accidents.apply(
    lambda r: h3.latlng_to_cell(r.lat, r.lon, 8), axis=1
)
stations["h3"] = stations.apply(
    lambda r: h3.latlng_to_cell(r.lat, r.lon, 8), axis=1
)

# 같은 셀 내 데이터 매칭 (단순 조인)
merged = accidents.merge(stations, on="h3")
```

### 3.3 이웃 셀 확장 (k-ring)

```python
# 중심 셀 + 반경 k 이내 이웃 셀
neighbors = h3.grid_disk(center_h3, k=1)  # 7개 셀
neighbors = h3.grid_disk(center_h3, k=2)  # 19개 셀
```

---

## 4. 지도 시각화 (Streamlit + Pydeck)

### 4.1 기술 선정 배경

| 기준 | Kakao Maps | Leaflet | **Pydeck** |
|------|------------|---------|------------|
| Streamlit 연동 | 가능 | Folium | **내장 지원** |
| H3 그리드 | 직접 구현 | 직접 구현 | **네이티브** |
| Python 전용 | X | Folium | **O** |
| 구현 난이도 | 중 | 중 | **쉬움** |

### 4.2 Pydeck 핵심 기능

```python
import streamlit as st
import pydeck as pdk

# H3 그리드 레이어
h3_layer = pdk.Layer(
    "H3HexagonLayer",
    data=df,
    get_hexagon="h3_index",
    get_fill_color="[255, (1-probability)*255, 0, 150]",
    pickable=True
)

# 사고 위치 마커
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=accidents_df,
    get_position=["lon", "lat"],
    get_radius=100,
    get_fill_color=[255, 0, 0, 160]
)

# 지도 표시
st.pydeck_chart(pdk.Deck(
    layers=[h3_layer, scatter_layer],
    initial_view_state=pdk.ViewState(
        latitude=36.5, longitude=127.5, zoom=7
    )
))
```

### 4.3 향후 확장 (Next.js 전환)

| 현재 (MVP) | 전환 후 (Production) |
|------------|---------------------|
| Streamlit | Next.js + React |
| Pydeck (Python) | Deck.gl (JavaScript) |
| 단일 사용자 | 다중 사용자 |
| 빠른 프로토타입 | 커스터마이징 |

**전환 공수**: 약 2~3주 추가 (Pydeck ↔ Deck.gl 거의 1:1 대응)

---

## 5. 데이터 구조

### 5.1 학습 데이터 현황

| 파일 | 레코드 | 좌표 | 용도 |
|------|--------|------|------|
| 산악사고_지오코딩.xlsx | 10,134 | ✅ | 2024년 학습 |
| 구조활동현황_지오코딩.xlsx | 13,189 | ✅ | 2020년 학습 |
| **통합** | **23,323** | ✅ | 전체 학습 |

### 5.2 외부 API 피처 데이터

| API | 데이터 | 주요 필드 |
|-----|--------|-----------|
| 전파누리 | 기지국 위치 | lat, lon, FRQ, PWR |
| 위험지역 | 등산로 위험지점 | lat, lon, 장소유형, 고도 |
| 산악기상 | 기상 관측 | 강수량, 습도, 기압 |

### 5.3 통합 피처 구성

```
┌─────────────────────────────────────────────────────────────┐
│                    학습 데이터셋 구조                         │
├─────────────────────────────────────────────────────────────┤
│  Target (Y): 사고 발생 여부 / 발견 위치                       │
├─────────────────────────────────────────────────────────────┤
│  Features (X):                                              │
│  ├── 사고 데이터: 시간, 계절, 요일, 사고유형                   │
│  ├── 공간 피처: lat, lon, H3 grid index                     │
│  ├── 기지국 피처: 반경 내 기지국 수, 평균 신호세기             │
│  ├── 위험지역 피처: 반경 내 위험지점 수, 거리                  │
│  └── 기상 피처: 온도, 강수, 풍속 (API 연동)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 피처 엔지니어링 (7개 카테고리)

### 6.1 피처 목록

#### (A) 거리 기반 피처
```python
dist_to_last_seen          # Grid와 마지막 관측 위치 간 직선 거리 (m)
dist_to_last_seen_log      # 로그 변환 거리
```

#### (B) 기지국 커버리지 피처 (전파누리 API)
```python
num_stations_in_range      # 커버 가능한 기지국 수
avg_station_power          # 평균 기지국 출력 (W)
coverage_score             # 전파 도달 예상 점수
```

#### (C) 위험지역 피처 (위험지역 POI API)
```python
near_danger_zone           # 위험지역 인접 여부
danger_zone_distance       # 가장 가까운 위험지역까지 거리
historical_accident_count  # 과거 사고 건수 (H3 셀 기준)
```

#### (D) 시간 피처
```python
hour_of_day                # 시간대 (0~23)
is_peak_hour               # 피크 시간대 여부 (12~15시)
is_night                   # 야간 여부 (21~06시)
is_weekend                 # 주말 여부
```

#### (E) 기상 피처 (산악기상정보 API)
```python
precipitation_mm           # 강수량 (mm)
humidity_2m                # 2m 습도 (%)
weather_risk_score         # 기상 위험도 종합 점수
```

---

## 7. 모델 학습

### 7.1 LightGBM 설정

```python
params = {
    "boosting_type": "gbdt",
    "objective": "binary",
    "metric": ["binary_logloss", "auc"],
    "num_leaves": 31,
    "learning_rate": 0.05,
    "is_unbalance": True,
    "seed": 42
}
```

### 7.2 평가 지표

| 지표 | MVP 목표 | 설명 |
|------|----------|------|
| Recall@10 | ≥0.5 | 상위 10개 내 정답 비율 |
| Recall@20 | ≥0.7 | 상위 20개 내 정답 비율 |
| MRR | ≥0.4 | Mean Reciprocal Rank |

---

## 8. 프로젝트 구조 (현행화)

```
mars/
├── src/
│   ├── api/
│   │   └── schemas.py              # ✅ Pydantic 스키마
│   └── data/
│       ├── api_clients.py          # ✅ 3종 API 클라이언트
│       └── sgis_client.py          # ✅ SGIS 지오코딩 클라이언트
├── config/
│   └── settings.py                 # ✅ API 키 설정
├── data/
│   ├── 소방청_*.xlsx               # ✅ 원본 데이터
│   └── generated/
│       ├── 산악사고_지오코딩_*.xlsx # ✅ 지오코딩 완료
│       ├── 구조활동현황_지오코딩_*.xlsx # ✅ 지오코딩 완료
│       └── 주소_좌표_매핑_통합_*.xlsx   # ✅ 매핑 테이블
├── docs/
│   └── data_preprocessing_analysis.md # ✅ 전처리 분석
├── notebooks/                       # 예정
├── models/                          # 예정
├── requirements.txt                 # ✅
├── CLAUDE.md                        # ✅
└── README.md                        # ✅
```

---

## 9. 의존성 패키지

```txt
# requirements.txt (현재)
pandas>=2.0.0
numpy>=1.24.0
httpx>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
tenacity>=8.2.0
xmltodict>=0.13.0
openpyxl>=3.1.0

# 추가 예정 (Phase 2)
lightgbm>=4.0.0
scikit-learn>=1.3.0
h3>=4.0.0
geopandas>=0.14.0
pydeck>=0.8.0
streamlit>=1.29.0
```

---

## 10. 구현 로드맵

### Phase 1: 데이터 파이프라인 ✅ **완료**
- [x] API 클라이언트 구현 (전파누리, 산악기상, 위험지역)
- [x] SGIS 지오코딩 클라이언트 구현
- [x] 소방청 데이터 지오코딩 (23,323건)
- [x] 주소-좌표 매핑 테이블 생성
- [x] 지도 API 선정 (Streamlit + Pydeck)

### Phase 2: 피처 엔지니어링 ← **현재 단계**
- [ ] H3 그리드 시스템 구현
- [ ] 사고 데이터 + API 데이터 공간 조인
- [ ] 7개 카테고리 피처 계산
- [ ] 피처 매트릭스 생성

### Phase 3: 모델 학습
- [ ] LightGBM 학습 파이프라인
- [ ] GroupKFold 교차 검증
- [ ] 하이퍼파라미터 튜닝

### Phase 4: UI 및 평가
- [ ] Streamlit + Pydeck 대시보드
- [ ] 평가 지표 리포트
- [ ] 통합 테스트

---

## 11. 다음 단계 (MVP 이후)

1. **Next.js 전환**: Streamlit → Next.js + React (Deck.gl)
2. **실시간 연동**: RF 관측 실시간 스트리밍
3. **데이터 확대**: 실제 구조 사례 데이터 확보
4. **드론 연계**: 드론 이동국 통합
5. **운영 배포**: API 서버 배포

---

*작성일: 2026-01-16*
*버전: 4.0 (Phase 1 완료)*
