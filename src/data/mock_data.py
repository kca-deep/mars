"""
Mock 데이터 생성기
- 외부 API가 차단되거나 테스트 환경에서 사용
"""
import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json


class MockDataGenerator:
    """테스트용 Mock 데이터 생성기"""

    # 주요 산악공원 정보
    PARKS = {
        "지리산": {"lat": 35.3373, "lon": 127.7307, "area_code": "11"},
        "설악산": {"lat": 38.1194, "lon": 128.4656, "area_code": "06"},
        "북한산": {"lat": 37.6597, "lon": 126.9778, "area_code": "01"},
        "한라산": {"lat": 33.3617, "lon": 126.5292, "area_code": "16"},
        "덕유산": {"lat": 35.8673, "lon": 127.7469, "area_code": "11"},
        "오대산": {"lat": 37.7986, "lon": 128.5431, "area_code": "06"},
        "소백산": {"lat": 36.9573, "lon": 128.4867, "area_code": "07"},
        "가야산": {"lat": 35.8219, "lon": 128.1189, "area_code": "10"},
        "내장산": {"lat": 35.4833, "lon": 126.8917, "area_code": "12"},
        "무등산": {"lat": 35.1344, "lon": 126.9886, "area_code": "13"},
    }

    CARRIERS = ["SK", "KT", "LG"]
    SERVICES = ["LTE", "5G", "3G"]
    ANTENNA_FORMS = ["옴니", "지향성", "섹터"]
    DANGER_TYPES = ["낙석위험", "급경사", "낙뢰위험", "실족위험", "고도위험", "계곡위험"]
    ACCIDENT_TYPES = ["일반추락", "실족추락", "질병환자", "탈진/탈수", "기타사고"]

    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)

    def generate_base_stations(
        self,
        park_name: str = "지리산",
        count: int = 50
    ) -> List[Dict[str, Any]]:
        """이동통신 기지국 Mock 데이터 생성"""
        if park_name == "ALL":
            parks = list(self.PARKS.keys())
        else:
            parks = [park_name] if park_name in self.PARKS else ["지리산"]

        stations = []
        for i in range(count):
            park = random.choice(parks)
            park_info = self.PARKS[park]

            # 공원 중심으로부터 랜덤 위치 생성
            lat_offset = np.random.normal(0, 0.05)
            lon_offset = np.random.normal(0, 0.05)

            station = {
                "LAT": round(park_info["lat"] + lat_offset, 6),
                "LON": round(park_info["lon"] + lon_offset, 6),
                "FRQ": random.choice([700, 850, 1800, 2100, 2600, 3500]),
                "PWR": round(random.uniform(5, 40), 1),
                "ANT_FORM": random.choice(self.ANTENNA_FORMS),
                "ANT_GAIN": round(random.uniform(10, 20), 1),
                "SEA_ALT": round(random.uniform(200, 1500), 1),
                "GRD_ALT": round(random.uniform(10, 50), 1),
                "CUS_CD": random.choice(self.CARRIERS),
                "SERVICE_CD": random.choice(self.SERVICES),
                "PARK_NM": park,
                "STATION_ID": f"BS-{park[:2]}-{i+1:04d}"
            }
            stations.append(station)

        return stations

    def generate_mountain_weather(
        self,
        count: int = 30,
        local_area: str = None
    ) -> List[Dict[str, Any]]:
        """산악기상 Mock 데이터 생성"""
        weather_data = []
        base_time = datetime.now() - timedelta(hours=count)

        # 관측소 목록 생성
        obs_stations = [
            {"obsid": f"OBS{i:04d}", "obsname": park, "localarea": info["area_code"]}
            for i, (park, info) in enumerate(self.PARKS.items())
        ]

        if local_area:
            obs_stations = [s for s in obs_stations if s["localarea"] == local_area]

        for i in range(count):
            station = random.choice(obs_stations)
            timestamp = base_time + timedelta(hours=i)

            weather = {
                "obsid": station["obsid"],
                "obsname": station["obsname"],
                "localarea": station["localarea"],
                "tm": timestamp.strftime("%Y-%m-%d %H:%M"),
                "cprn": round(random.uniform(0, 50), 1),  # 누적 강수량
                "rn": round(random.uniform(0, 20), 1),     # 당일 강수량
                "hm10m": round(random.uniform(40, 95), 1),  # 10m 습도
                "hm2m": round(random.uniform(45, 98), 1),   # 2m 습도
                "pa": round(random.uniform(950, 1030), 1),  # 기압
                "ta": round(random.uniform(-10, 30), 1),    # 기온 (추가)
                "ws": round(random.uniform(0, 15), 1),      # 풍속 (추가)
            }
            weather_data.append(weather)

        return weather_data

    def generate_danger_info(
        self,
        count: int = 40
    ) -> List[Dict[str, Any]]:
        """위험지역 POI Mock 데이터 생성"""
        danger_data = []

        for i in range(count):
            park = random.choice(list(self.PARKS.keys()))
            park_info = self.PARKS[park]

            lat_offset = np.random.normal(0, 0.03)
            lon_offset = np.random.normal(0, 0.03)

            danger = {
                "danger_id": f"DNG-{i+1:05d}",
                "danger_type": random.choice(self.DANGER_TYPES),
                "location_name": f"{park} {random.choice(['북릉', '남릉', '동릉', '서릉', '정상부근', '계곡', '능선'])}",
                "lat": round(park_info["lat"] + lat_offset, 6),
                "lon": round(park_info["lon"] + lon_offset, 6),
                "mountain_name": park,
                "altitude": round(random.uniform(300, 1800), 1),
                "severity": random.choice(["높음", "중간", "낮음"]),
                "description": f"{random.choice(self.DANGER_TYPES)} 주의 구간",
                "registered_date": (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
            }
            danger_data.append(danger)

        return danger_data

    def generate_grid_data(
        self,
        park_name: str = "지리산",
        grid_size_m: int = 100,
        grid_count: int = 500
    ) -> List[Dict[str, Any]]:
        """100m x 100m Grid Mock 데이터 생성"""
        park_info = self.PARKS.get(park_name, self.PARKS["지리산"])

        # 약 0.001도 = 100m (위도 기준)
        degree_per_100m = 0.0009

        grids = []
        grid_per_side = int(np.sqrt(grid_count))

        for i in range(grid_per_side):
            for j in range(grid_per_side):
                lat = park_info["lat"] - (grid_per_side / 2 - i) * degree_per_100m
                lon = park_info["lon"] - (grid_per_side / 2 - j) * degree_per_100m

                grid = {
                    "grid_id": f"GRID-{park_name[:2]}-{i:03d}-{j:03d}",
                    "center_lat": round(lat, 6),
                    "center_lon": round(lon, 6),
                    "grid_size_m": grid_size_m,
                    "elevation_m": round(random.uniform(200, 1800), 1),
                    "slope_deg": round(random.uniform(0, 60), 1),
                    "landcover": random.choice(["FOREST", "GRASS", "ROCK", "WATER"]),
                    "forest_density": round(random.uniform(0, 1), 2),
                    "crs": "EPSG:4326"
                }
                grids.append(grid)

        return grids

    def generate_episode_data(
        self,
        count: int = 10,
        park_name: str = "지리산"
    ) -> List[Dict[str, Any]]:
        """수색 에피소드 Mock 데이터 생성"""
        park_info = self.PARKS.get(park_name, self.PARKS["지리산"])
        episodes = []

        for i in range(count):
            base_time = datetime.now() - timedelta(days=random.randint(1, 365))
            lat_offset = np.random.normal(0, 0.02)
            lon_offset = np.random.normal(0, 0.02)

            episode = {
                "episode_id": f"EP-{park_name[:2]}-{base_time.strftime('%Y%m%d')}-{i+1:03d}",
                "episode_type": random.choice(["drill", "real"]),
                "agency": random.choice(["소방청", "경찰청", "산림청", "해양경찰"]),
                "region_code": f"KR-{random.randint(11, 50):02d}",
                "park_name": park_name,
                "start_time": base_time.isoformat(),
                "end_time": (base_time + timedelta(hours=random.randint(2, 48))).isoformat(),
                "last_seen_time": (base_time - timedelta(hours=random.randint(1, 12))).isoformat(),
                "last_seen_lat": round(park_info["lat"] + lat_offset, 6),
                "last_seen_lon": round(park_info["lon"] + lon_offset, 6),
                "subject_age": random.randint(20, 70),
                "subject_gender": random.choice(["M", "F"]),
                "accident_type": random.choice(self.ACCIDENT_TYPES)
            }
            episodes.append(episode)

        return episodes

    def generate_ground_truth(
        self,
        episodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ground Truth Mock 데이터 생성"""
        ground_truths = []

        for episode in episodes:
            # 마지막 관측 위치 근처에서 발견
            lat_offset = np.random.normal(0, 0.005)  # 약 500m 범위
            lon_offset = np.random.normal(0, 0.005)

            gt = {
                "episode_id": episode["episode_id"],
                "gt_type": random.choice(["found_point", "found_polygon"]),
                "gt_lat": round(episode["last_seen_lat"] + lat_offset, 6),
                "gt_lon": round(episode["last_seen_lon"] + lon_offset, 6),
                "found_time": episode["end_time"],
                "outcome": random.choice(["found", "found", "found", "not_found"]),  # 75% 발견
                "gt_confidence": round(random.uniform(0.7, 1.0), 2),
                "search_duration_hours": random.randint(2, 48)
            }
            ground_truths.append(gt)

        return ground_truths

    def generate_all_test_data(
        self,
        park_name: str = "지리산"
    ) -> Dict[str, Any]:
        """전체 테스트 데이터 셋 생성"""
        stations = self.generate_base_stations(park_name, count=50)
        weather = self.generate_mountain_weather(count=30)
        danger = self.generate_danger_info(count=40)
        grids = self.generate_grid_data(park_name, grid_count=400)
        episodes = self.generate_episode_data(count=10, park_name=park_name)
        ground_truths = self.generate_ground_truth(episodes)

        return {
            "base_stations": stations,
            "mountain_weather": weather,
            "danger_info": danger,
            "grids": grids,
            "episodes": episodes,
            "ground_truths": ground_truths,
            "metadata": {
                "park_name": park_name,
                "generated_at": datetime.now().isoformat(),
                "counts": {
                    "base_stations": len(stations),
                    "weather": len(weather),
                    "danger": len(danger),
                    "grids": len(grids),
                    "episodes": len(episodes),
                    "ground_truths": len(ground_truths)
                }
            }
        }


# 단독 실행 시 테스트
if __name__ == "__main__":
    generator = MockDataGenerator(seed=42)

    # 전체 데이터 생성
    data = generator.generate_all_test_data("지리산")

    print(f"Generated test data:")
    for key, value in data["metadata"]["counts"].items():
        print(f"  - {key}: {value} records")

    # 샘플 출력
    print("\nSample base station:")
    print(json.dumps(data["base_stations"][0], indent=2, ensure_ascii=False))

    print("\nSample weather:")
    print(json.dumps(data["mountain_weather"][0], indent=2, ensure_ascii=False))
