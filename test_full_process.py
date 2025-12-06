#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
드론 이미지 GPS 추출 및 지번 변환 통합 테스트
"""

import json
import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

def get_exif_data(image_path):
    """이미지에서 EXIF 데이터 추출"""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if not exif_data:
            print("❌ EXIF 데이터가 없습니다!")
            return None
        
        print("✅ EXIF 데이터 발견!")
        return exif_data
    except Exception as e:
        print(f"❌ 이미지 읽기 오류: {e}")
        return None

def get_gps_from_exif(exif_data):
    """EXIF에서 GPS 좌표 추출"""
    gps_info = {}
    
    for tag, value in exif_data.items():
        tag_name = TAGS.get(tag, tag)
        
        if tag_name == "GPSInfo":
            for gps_tag in value:
                gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                gps_info[gps_tag_name] = value[gps_tag]
    
    if not gps_info:
        print("❌ GPS 정보가 없습니다!")
        return None, None
    
    print("✅ GPS 정보 발견!")
    
    # 위도 변환
    lat_dms = gps_info.get('GPSLatitude')
    lat_ref = gps_info.get('GPSLatitudeRef')
    
    # 경도 변환
    lon_dms = gps_info.get('GPSLongitude')
    lon_ref = gps_info.get('GPSLongitudeRef')
    
    if not all([lat_dms, lat_ref, lon_dms, lon_ref]):
        print("❌ GPS 좌표가 불완전합니다!")
        return None, None
    
    # DMS → Decimal 변환
    lat = convert_to_degrees(lat_dms)
    if lat_ref == 'S':
        lat = -lat
    
    lon = convert_to_degrees(lon_dms)
    if lon_ref == 'W':
        lon = -lon
    
    print(f"📍 GPS 좌표: 위도 {lat:.6f}, 경도 {lon:.6f}")
    return lat, lon

def convert_to_degrees(dms):
    """DMS (Degree, Minute, Second) → Decimal Degree 변환"""
    d = float(dms[0])
    m = float(dms[1])
    s = float(dms[2])
    return d + (m / 60.0) + (s / 3600.0)

def get_address_from_coords(lat, lon, api_key):
    """좌표 → 지번 변환"""
    url = (
        f"https://api.vworld.kr/req/address"
        f"?service=address"
        f"&request=getAddress"
        f"&version=2.0"
        f"&crs=epsg:4326"
        f"&point={lon},{lat}"
        f"&type=both"
        f"&zipcode=true"
        f"&simple=false"
        f"&key={api_key}"
    )
    
    print("🌐 VWorld API 호출 중...")
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result['response']['status'] == 'OK':
            print("✅ 지번 변환 성공!")
            structure = result['response']['result'][0]['structure']
            
            sido = structure.get('level1', '')
            sigungu = structure.get('level2', '')
            dong = structure.get('level4L', '')
            jibun = structure.get('level5', '')
            
            full_address = f"{sido} {sigungu} {dong} {jibun}".strip()
            print(f"📍 주소: {full_address}")
            
            return {
                'full': full_address,
                'sido': sido,
                'sigungu': sigungu,
                'dong': dong,
                'jibun': jibun
            }
        else:
            print("❌ 지번 변환 실패!")
            print(f"오류: {result['response']['error']}")
            return None
            
    except Exception as e:
        print(f"❌ API 호출 오류: {e}")
        return None

def main():
    print("=" * 70)
    print("드론 이미지 GPS 추출 및 지번 변환 통합 테스트")
    print("=" * 70)
    print()
    
    # 1. config.json에서 API 키 읽기
    print("📋 1단계: API 키 로드")
    print("-" * 70)
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('vworld_api_key', '')
        print(f"✅ API 키 로드 성공: {api_key[:10]}...{api_key[-10:]}")
    except Exception as e:
        print(f"❌ config.json 읽기 실패: {e}")
        return
    
    print()
    
    # 2. 드론 이미지 경로 입력
    print("📋 2단계: 드론 이미지 선택")
    print("-" * 70)
    print("테스트할 드론 이미지 파일 경로를 입력하세요.")
    print("예시: C:\\drone_images\\DJI_0001.JPG")
    print()
    
    image_path = input("이미지 경로: ").strip().strip('"')
    
    if not os.path.exists(image_path):
        print(f"❌ 파일이 없습니다: {image_path}")
        return
    
    print(f"✅ 파일 발견: {image_path}")
    print()
    
    # 3. EXIF 데이터 추출
    print("📋 3단계: EXIF 데이터 추출")
    print("-" * 70)
    
    exif_data = get_exif_data(image_path)
    if not exif_data:
        return
    
    print()
    
    # 4. GPS 좌표 추출
    print("📋 4단계: GPS 좌표 추출")
    print("-" * 70)
    
    lat, lon = get_gps_from_exif(exif_data)
    if lat is None or lon is None:
        return
    
    print()
    
    # 5. 지번 변환
    print("📋 5단계: 지번 변환")
    print("-" * 70)
    
    address = get_address_from_coords(lat, lon, api_key)
    if not address:
        return
    
    print()
    
    # 6. 최종 결과
    print("=" * 70)
    print("🎉 테스트 완료! 최종 결과")
    print("=" * 70)
    print(f"📸 원본 파일: {os.path.basename(image_path)}")
    print(f"📍 GPS 좌표: 위도 {lat:.6f}, 경도 {lon:.6f}")
    print(f"🏠 주소: {address['full']}")
    print()
    
    # 7. 제안된 파일명
    filename = f"{address['sido']}_{address['sigungu']}_{address['dong']}_{address['jibun']}.jpg"
    filename = filename.replace(' ', '_').replace('/', '-')
    
    print(f"💾 제안된 파일명: {filename}")
    print()
    
    print("=" * 70)
    print("✅ 모든 테스트 통과! 시스템이 정상 작동합니다!")
    print("=" * 70)

if __name__ == "__main__":
    main()