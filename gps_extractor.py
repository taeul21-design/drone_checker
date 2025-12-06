"""
GPS EXIF 데이터 추출 모듈
드론 이미지에서 GPS 좌표를 추출합니다.
"""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread
from typing import Dict, Optional, Tuple
from datetime import datetime


class GPSExtractor:
    """드론 이미지에서 GPS 좌표를 추출하는 클래스"""
    
    @staticmethod
    def dms_to_decimal(dms: Tuple, ref: str) -> float:
        """
        DMS (Degrees, Minutes, Seconds) 형식을 Decimal 형식으로 변환
        
        Args:
            dms: (도, 분, 초) 튜플
            ref: 방향 (N/S/E/W)
            
        Returns:
            Decimal 좌표
        """
        try:
            degrees = float(dms[0])
            minutes = float(dms[1])
            seconds = float(dms[2])
            
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            # 남위(S) 또는 서경(W)인 경우 음수로 변환
            if ref in ['S', 'W']:
                decimal = -decimal
                
            return decimal
        except Exception as e:
            raise ValueError(f"DMS 변환 오류: {e}")
    
    @staticmethod
    def extract_gps_from_image(image_path: str) -> Optional[Dict]:
        """
        이미지에서 GPS EXIF 데이터 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            GPS 정보 딕셔너리 또는 None
        """
        try:
            # Pillow로 EXIF 데이터 읽기
            image = Image.open(image_path)
            exif_data = image._getexif()
            
            if not exif_data:
                print(f"⚠️  EXIF 데이터 없음: {image_path}")
                return None
            
            # GPS 정보 추출
            gps_info = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'GPSInfo':
                    for gps_tag in value:
                        sub_tag = GPSTAGS.get(gps_tag, gps_tag)
                        gps_info[sub_tag] = value[gps_tag]
            
            if not gps_info:
                print(f"⚠️  GPS 정보 없음: {image_path}")
                return None
            
            # 위도/경도 추출
            lat = gps_info.get('GPSLatitude')
            lat_ref = gps_info.get('GPSLatitudeRef')
            lon = gps_info.get('GPSLongitude')
            lon_ref = gps_info.get('GPSLongitudeRef')
            altitude = gps_info.get('GPSAltitude', 0)
            
            if not all([lat, lat_ref, lon, lon_ref]):
                print(f"⚠️  GPS 좌표 불완전: {image_path}")
                return None
            
            # Decimal 형식으로 변환
            latitude = GPSExtractor.dms_to_decimal(lat, lat_ref)
            longitude = GPSExtractor.dms_to_decimal(lon, lon_ref)
            
            # 촬영 날짜/시간 추출
            datetime_original = exif_data.get(36867)  # DateTimeOriginal
            if datetime_original:
                try:
                    dt = datetime.strptime(datetime_original, '%Y:%m:%d %H:%M:%S')
                    date_str = dt.strftime('%Y%m%d')
                    time_str = dt.strftime('%H%M%S')
                except:
                    date_str = datetime.now().strftime('%Y%m%d')
                    time_str = datetime.now().strftime('%H%M%S')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
                time_str = datetime.now().strftime('%H%M%S')
            
            result = {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'date': date_str,
                'time': time_str,
                'datetime_original': datetime_original
            }
            
            print(f"✅ GPS 추출 성공: {image_path}")
            print(f"   📍 위도: {latitude:.6f}, 경도: {longitude:.6f}")
            
            return result
            
        except Exception as e:
            print(f"❌ GPS 추출 오류: {image_path} - {e}")
            return None
    
    @staticmethod
    def extract_gps_alternative(image_path: str) -> Optional[Dict]:
        """
        exifread 라이브러리를 사용한 대체 GPS 추출 방법
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            GPS 정보 딕셔너리 또는 None
        """
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            
            if not tags:
                return None
            
            # GPS 좌표 추출
            gps_lat = tags.get('GPS GPSLatitude')
            gps_lat_ref = tags.get('GPS GPSLatitudeRef')
            gps_lon = tags.get('GPS GPSLongitude')
            gps_lon_ref = tags.get('GPS GPSLongitudeRef')
            
            if not all([gps_lat, gps_lat_ref, gps_lon, gps_lon_ref]):
                return None
            
            # Ratio 값을 float로 변환
            lat_values = [float(x.num) / float(x.den) for x in gps_lat.values]
            lon_values = [float(x.num) / float(x.den) for x in gps_lon.values]
            
            latitude = GPSExtractor.dms_to_decimal(lat_values, str(gps_lat_ref))
            longitude = GPSExtractor.dms_to_decimal(lon_values, str(gps_lon_ref))
            
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')
            
            return {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': 0,
                'date': date_str,
                'time': time_str
            }
            
        except Exception as e:
            print(f"❌ exifread GPS 추출 오류: {e}")
            return None


# 테스트 코드
if __name__ == "__main__":
    test_image = "test_drone_image.jpg"  # 테스트 이미지 경로
    
    extractor = GPSExtractor()
    gps_data = extractor.extract_gps_from_image(test_image)
    
    if gps_data:
        print("\n🎉 GPS 추출 성공!")
        print(f"위도: {gps_data['latitude']}")
        print(f"경도: {gps_data['longitude']}")
        print(f"고도: {gps_data['altitude']}")
        print(f"날짜: {gps_data['date']}")
        print(f"시간: {gps_data['time']}")
    else:
        print("\n❌ GPS 추출 실패")
