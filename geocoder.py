"""
좌표 → 지번 변환 모듈
VWorld 및 Kakao API를 사용하여 GPS 좌표를 지번으로 변환합니다.
"""

import requests
import json
from typing import Optional, Dict
import time


class Geocoder:
    """GPS 좌표를 지번으로 변환하는 클래스"""
    
    def __init__(self, vworld_api_key: str, kakao_api_key: str = None):
        """
        Args:
            vworld_api_key: VWorld API 키
            kakao_api_key: Kakao API 키 (선택)
        """
        self.vworld_api_key = vworld_api_key
        self.kakao_api_key = kakao_api_key
        self.vworld_url = "https://api.vworld.kr/req/address"
        self.kakao_url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    
    def coordinate_to_jibun_vworld(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        VWorld API를 사용하여 좌표를 지번으로 변환
        
        Args:
            latitude: 위도
            longitude: 경도
            
        Returns:
            지번 정보 딕셔너리 또는 None
        """
        try:
            params = {
                'service': 'address',
                'request': 'getAddress',
                'version': '2.0',
                'crs': 'epsg:4326',
                'point': f'{longitude},{latitude}',
                'format': 'json',
                'type': 'both',  # 지번 + 도로명
                'key': self.vworld_api_key
            }
            
            response = requests.get(self.vworld_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['response']['status'] != 'OK':
                print(f"⚠️  VWorld API 오류: {data['response']['status']}")
                return None
            
            result = data['response']['result'][0]
            
            # 지번 주소 파싱
            if 'structure' in result:
                structure = result['structure']
                jibun_address = {
                    'sido': structure.get('level1', ''),
                    'sigungu': structure.get('level2', ''),
                    'emd': structure.get('level4L', ''),  # 읍면동
                    'ri': structure.get('level4LC', ''),  # 리
                    'jibun': structure.get('detail', ''),
                    'full_address': result.get('text', ''),
                    'road_address': result.get('zipcode', '')
                }
            else:
                # 구조 정보가 없는 경우 text에서 파싱
                full_text = result.get('text', '')
                jibun_address = self._parse_address_text(full_text)
            
            print(f"✅ 지번 변환 성공 (VWorld): {jibun_address['full_address']}")
            
            return jibun_address
            
        except requests.exceptions.RequestException as e:
            print(f"❌ VWorld API 요청 오류: {e}")
            return None
        except Exception as e:
            print(f"❌ VWorld 지번 변환 오류: {e}")
            return None
    
    def coordinate_to_jibun_kakao(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Kakao API를 사용하여 좌표를 지번으로 변환 (백업용)
        
        Args:
            latitude: 위도
            longitude: 경도
            
        Returns:
            지번 정보 딕셔너리 또는 None
        """
        if not self.kakao_api_key:
            print("⚠️  Kakao API 키가 설정되지 않았습니다.")
            return None
        
        try:
            headers = {
                'Authorization': f'KakaoAK {self.kakao_api_key}'
            }
            
            params = {
                'x': longitude,
                'y': latitude,
                'input_coord': 'WGS84'
            }
            
            response = requests.get(self.kakao_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data['documents']:
                print("⚠️  Kakao API: 주소를 찾을 수 없습니다.")
                return None
            
            # 지번 주소 선택
            address = None
            for doc in data['documents']:
                if doc['address_type'] == 'REGION':
                    address = doc['address']
                    break
            
            if not address:
                address = data['documents'][0]['address']
            
            jibun_address = {
                'sido': address.get('region_1depth_name', ''),
                'sigungu': address.get('region_2depth_name', ''),
                'emd': address.get('region_3depth_name', ''),
                'ri': '',
                'jibun': address.get('main_address_no', '') + 
                         ('-' + address.get('sub_address_no', '') if address.get('sub_address_no') else ''),
                'full_address': address.get('address_name', ''),
                'road_address': data['documents'][0].get('road_address', {}).get('address_name', '')
            }
            
            print(f"✅ 지번 변환 성공 (Kakao): {jibun_address['full_address']}")
            
            return jibun_address
            
        except Exception as e:
            print(f"❌ Kakao 지번 변환 오류: {e}")
            return None
    
    def coordinate_to_jibun(self, latitude: float, longitude: float, 
                           provider: str = 'vworld') -> Optional[Dict]:
        """
        GPS 좌표를 지번으로 변환 (우선순위에 따라 API 선택)
        
        Args:
            latitude: 위도
            longitude: 경도
            provider: API 제공자 ('vworld' 또는 'kakao')
            
        Returns:
            지번 정보 딕셔너리 또는 None
        """
        print(f"\n🔍 좌표 → 지번 변환 중... ({latitude:.6f}, {longitude:.6f})")
        
        if provider == 'vworld':
            # VWorld 우선 시도
            result = self.coordinate_to_jibun_vworld(latitude, longitude)
            if result:
                return result
            
            # 실패 시 Kakao로 대체
            print("⚠️  VWorld 실패, Kakao API 시도...")
            time.sleep(0.5)  # API 요청 간격
            result = self.coordinate_to_jibun_kakao(latitude, longitude)
            return result
        else:
            # Kakao 우선 시도
            result = self.coordinate_to_jibun_kakao(latitude, longitude)
            if result:
                return result
            
            # 실패 시 VWorld로 대체
            print("⚠️  Kakao 실패, VWorld API 시도...")
            time.sleep(0.5)
            result = self.coordinate_to_jibun_vworld(latitude, longitude)
            return result
    
    @staticmethod
    def _parse_address_text(text: str) -> Dict:
        """
        주소 텍스트를 파싱하여 구조화 (백업 메서드)
        
        Args:
            text: 주소 전체 텍스트
            
        Returns:
            파싱된 주소 딕셔너리
        """
        parts = text.split()
        
        return {
            'sido': parts[0] if len(parts) > 0 else '',
            'sigungu': parts[1] if len(parts) > 1 else '',
            'emd': parts[2] if len(parts) > 2 else '',
            'ri': '',
            'jibun': parts[-1] if len(parts) > 3 else '',
            'full_address': text,
            'road_address': ''
        }


# 테스트 코드
if __name__ == "__main__":
    # 테스트 좌표 (서울 시청)
    test_lat = 37.5665
    test_lon = 126.9780
    
    vworld_key = "YOUR_VWORLD_API_KEY"  # 실제 API 키로 교체
    kakao_key = "YOUR_KAKAO_API_KEY"    # 실제 API 키로 교체
    
    geocoder = Geocoder(vworld_key, kakao_key)
    
    jibun = geocoder.coordinate_to_jibun(test_lat, test_lon)
    
    if jibun:
        print("\n🎉 지번 변환 성공!")
        print(f"시도: {jibun['sido']}")
        print(f"시군구: {jibun['sigungu']}")
        print(f"읍면동: {jibun['emd']}")
        print(f"지번: {jibun['jibun']}")
        print(f"전체 주소: {jibun['full_address']}")
    else:
        print("\n❌ 지번 변환 실패")
