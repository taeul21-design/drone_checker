#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
드론 이미지 GPS 추출 + 지번 변환 + 텍스트 오버레이 통합 테스트
"""

import json
import requests
import os
import shutil
import time
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
from image_annotator import ImageAnnotator

def print_header():
    """헤더 출력"""
    print("=" * 80)
    print("🚁 드론 이미지 GPS 추출 + 지번 변환 + 텍스트 오버레이 통합 테스트")
    print("=" * 80)
    print("기능: GPS 추출 → 지번 변환 → 이미지에 텍스트 표시 → 자동 저장")
    print("=" * 80)
    print()

def load_config():
    """config.json에서 설정 로드"""
    print("📋 1단계: 설정 파일 로드")
    print("-" * 80)
    
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        print(f"❌ {config_file} 파일이 없습니다!")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_key = config.get('vworld_api_key', '')
        
        if not api_key:
            print("❌ config.json에 vworld_api_key가 없습니다!")
            return None
        
        print(f"✅ VWorld API 키 로드 성공!")
        print(f"🔑 API 키: {api_key[:10]}...{api_key[-10:]}")
        
        # 추가 설정 확인
        backup_original = config.get('backup_original', True)
        add_text_overlay = config.get('add_text_overlay', True)
        include_jimok = config.get('include_jimok', False)
        default_jimok = config.get('default_jimok', '')
        
        print(f"⚙️ 원본 백업: {'예' if backup_original else '아니오'}")
        print(f"⚙️ 텍스트 오버레이: {'예' if add_text_overlay else '아니오'}")
        print(f"⚙️ 지목 표시: {'예' if include_jimok else '아니오'}")
        if include_jimok and default_jimok:
            print(f"⚙️ 기본 지목: {default_jimok}")
        print()
        
        return config
        
    except Exception as e:
        print(f"❌ config.json 읽기 실패: {e}")
        return None

def get_image_path():
    """사용자로부터 이미지 경로 입력받기"""
    print("📋 2단계: 드론 이미지 선택")
    print("-" * 80)
    print("테스트할 드론 이미지 파일의 전체 경로를 입력하세요.")
    print()
    
    while True:
        image_path = input("📸 이미지 경로 입력: ").strip().strip('"')
        
        if not image_path:
            print("⚠️ 경로를 입력해주세요!")
            continue
        
        if not os.path.exists(image_path):
            print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
            continue
        
        valid_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG']
        if not any(image_path.lower().endswith(ext.lower()) for ext in valid_extensions):
            print(f"❌ 지원하지 않는 파일 형식입니다.")
            continue
        
        print(f"✅ 이미지 파일 확인 완료!")
        print(f"📁 파일명: {os.path.basename(image_path)}")
        print(f"📊 파일 크기: {os.path.getsize(image_path) / 1024 / 1024:.2f} MB")
        print()
        
        return image_path

def extract_gps_from_exif(image_path):
    """이미지에서 GPS 좌표 추출"""
    print("📋 3단계: GPS 좌표 추출")
    print("-" * 80)
    
    try:
        with Image.open(image_path) as image:
            exif_data = image._getexif()
            
            if not exif_data:
                print("❌ EXIF 데이터가 없습니다!")
                return None, None
            
            print("✅ EXIF 데이터 발견!")
            
            # GPS 정보 추출
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
            
            # 필수 GPS 데이터 확인
            required_keys = ['GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude', 'GPSLongitudeRef']
            if not all(key in gps_info for key in required_keys):
                print("❌ GPS 데이터가 불완전합니다!")
                return None, None
            
            # DMS → Decimal 변환
            lat_dms = gps_info['GPSLatitude']
            lat_ref = gps_info['GPSLatitudeRef']
            lat = dms_to_decimal(lat_dms)
            if lat_ref == 'S':
                lat = -lat
            
            lon_dms = gps_info['GPSLongitude']
            lon_ref = gps_info['GPSLongitudeRef']
            lon = dms_to_decimal(lon_dms)
            if lon_ref == 'W':
                lon = -lon
            
            print(f"✅ GPS 좌표 추출 성공!")
            print(f"📍 위도: {lat:.8f}°")
            print(f"📍 경도: {lon:.8f}°")
            print()
            
            return lat, lon
            
    except Exception as e:
        print(f"❌ GPS 추출 오류: {e}")
        return None, None

def dms_to_decimal(dms):
    """DMS → Decimal 변환"""
    d = float(dms[0])
    m = float(dms[1])
    s = float(dms[2])
    return d + (m / 60.0) + (s / 3600.0)

def convert_to_address(lat, lon, api_key):
    """GPS 좌표를 주소로 변환"""
    print("📋 4단계: 좌표 → 지번 변환")
    print("-" * 80)
    
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
    
    print(f"🌐 VWorld API 호출 중...")
    
    try:
        response = requests.get(url, timeout=30)
        result = response.json()
        
        if result['response']['status'] == 'OK':
            print("✅ 지번 변환 성공!")
            
            structure = result['response']['result'][0]['structure']
            
            address_info = {
                'success': True,
                'sido': structure.get('level1', '').strip(),
                'sigungu': structure.get('level2', '').strip(),
                'eupmeondong': structure.get('level4L', '').strip(),
                'jibun': structure.get('level5', '').strip(),
                'full_address': result['response']['result'][0].get('text', '')
            }
            
            print(f"📍 주소: {address_info['full_address']}")
            print()
            
            return address_info
        else:
            print("❌ 지번 변환 실패!")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ API 호출 오류: {e}")
        return {'success': False}

def backup_original_image(image_path):
    """원본 이미지를 backup 폴더에 복사"""
    print("📋 5단계: 원본 이미지 백업")
    print("-" * 80)
    
    # backup 폴더 생성
    backup_folder = os.path.join(os.path.dirname(image_path), 'backup')
    os.makedirs(backup_folder, exist_ok=True)
    
    # 백업 파일 경로
    backup_path = os.path.join(backup_folder, os.path.basename(image_path))
    
    # 이미 백업 파일이 있으면 타임스탬프 추가
    if os.path.exists(backup_path):
        name, ext = os.path.splitext(os.path.basename(image_path))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_folder, f"{name}_{timestamp}{ext}")
    
    # 복사
    try:
        shutil.copy2(image_path, backup_path)
        print(f"✅ 원본 백업 완료!")
        print(f"📁 백업 위치: {backup_path}")
        print()
        return backup_path
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        print()
        return None

def add_text_to_image(image_path, address_info, config):
    """이미지에 텍스트 오버레이 추가"""
    print("📋 6단계: 이미지에 텍스트 표시")
    print("-" * 80)
    
    # Annotator 생성
    annotator = ImageAnnotator(config)
    
    # 텍스트 포맷
    include_jimok = config.get('include_jimok', False)
    default_jimok = config.get('default_jimok', '')
    
    text = annotator.format_address_text(
        address_info,
        include_jimok=include_jimok,
        jimok=default_jimok
    )
    
    print(f"📝 표시할 텍스트: '{text}'")
    print(f"🎨 디자인: 반투명 흰 배경 + 검은 텍스트")
    print()
    
    # 텍스트 오버레이 추가 (원본 파일에 덮어쓰기)
    start_time = time.time()
    
    try:
        annotator.add_text_overlay(image_path, text, image_path)
        
        elapsed_time = time.time() - start_time
        
        print(f"✅ 텍스트 오버레이 추가 완료!")
        print(f"⏱️ 처리 시간: {elapsed_time:.2f}초")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 텍스트 추가 실패: {e}")
        print()
        return False

def print_final_summary(image_path, lat, lon, address_info, total_time):
    """최종 결과 요약"""
    print("=" * 80)
    print("🎉 처리 완료! 최종 결과")
    print("=" * 80)
    
    print("📸 처리된 이미지:")
    print(f"   - 파일명: {os.path.basename(image_path)}")
    print(f"   - 전체 경로: {image_path}")
    print()
    
    print("📍 GPS 좌표:")
    print(f"   - 위도: {lat:.8f}°")
    print(f"   - 경도: {lon:.8f}°")
    print()
    
    print("🏠 주소 정보:")
    print(f"   - {address_info['full_address']}")
    print()
    
    print("⏱️ 성능 분석:")
    print(f"   - 총 처리 시간: {total_time:.2f}초")
    print(f"   - 평균 처리 속도: 1장 / {total_time:.2f}초")
    print(f"   - 100장 예상 시간: {total_time * 100 / 60:.1f}분")
    print()
    
    print("✅ 모든 작업 완료!")
    print("=" * 80)

def main():
    """메인 함수"""
    start_time = time.time()
    
    try:
        # 헤더 출력
        print_header()
        
        # 1단계: 설정 로드
        config = load_config()
        if not config:
            return
        
        api_key = config['vworld_api_key']
        backup_original = config.get('backup_original', True)
        add_overlay = config.get('add_text_overlay', True)
        
        # 2단계: 이미지 경로 입력
        image_path = get_image_path()
        
        # 3단계: GPS 추출
        lat, lon = extract_gps_from_exif(image_path)
        if lat is None or lon is None:
            return
        
        # 4단계: 지번 변환
        address_info = convert_to_address(lat, lon, api_key)
        if not address_info['success']:
            return
        
        # 5단계: 원본 백업 (옵션)
        if backup_original:
            backup_original_image(image_path)
        else:
            print("📋 5단계: 원본 백업 건너뛰기 (설정에서 비활성화됨)")
            print("-" * 80)
            print()
        
        # 6단계: 텍스트 오버레이 추가 (옵션)
        if add_overlay:
            success = add_text_to_image(image_path, address_info, config)
            if not success:
                return
        else:
            print("📋 6단계: 텍스트 오버레이 건너뛰기 (설정에서 비활성화됨)")
            print("-" * 80)
            print()
        
        # 총 처리 시간
        total_time = time.time() - start_time
        
        # 최종 요약
        print_final_summary(image_path, lat, lon, address_info, total_time)
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    main()
