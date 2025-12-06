#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
드론 이미지 GPS → 지번 변환 자동화 시스템 (Drone GPS to Jibun Converter)
=============================================================================

프로그램명: Drone GPS to Jibun Converter
버전: v6.1
작성일: 2025-01-13
개발자: 국립농산물품질관리원 경주사무소 김정연  
Copyright (c) 2025 국립농산물품질관리원/김정연. All rights reserved. 

본 프로그램은 저작권법에 의해 보호받습니다.
무단 복제, 배포, 수정을 금지합니다.

라이선스:
- 본 프로그램은 공익목적으로 개발되었습니다.
- 타 공공기관에서 사용 시 개발자에게 사전 통보 바랍니다.
- 상업적 사용은 개발자의 서면 허가가 필요합니다.

문의: kimjy69@naver.com 
=============================================================================

주요 기능:
- 드론 이미지에서 GPS 좌표 자동 추출 (EXIF 데이터)
- VWorld API를 통한 GPS → 지번 자동 변환
- 이미지 하단에 지번 텍스트 오버레이
- 파일명을 지번으로 자동 변경 (타임스탬프 포함)
- 다중 이미지 일괄 처리
- 처리 결과 JSON 리포트 자동 생성

기술 스택:
- Python 3.8+
- Pillow (이미지 처리)
- requests (HTTP 통신)
- tkinter (GUI)

변경 이력:
- v6.1 (2025-01-13): 저작권 표시 추가, 라이선스 명시
- v6.0 (2025-01-12): 백업 폴더 제거, 파일명 자동 변경 기능 추가
- v5.0 (2025-01-11): 텍스트 오버레이 임시 파일 방식으로 재작성
- v4.0 (2025-01-10): 텍스트 크기 80px로 증가
- v3.0 (2025-01-09): 진행률 표시 개선
- v2.0 (2025-01-08): GUI 인터페이스 추가
- v1.0 (2025-01-07): 초기 버전 (단일 이미지 처리)

=============================================================================
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import tempfile
import shutil
from datetime import datetime
import re

def load_config():
    """설정 파일에서 API 키를 로드합니다."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('vworld_api_key')
    except FileNotFoundError:
        print("config.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("config.json 파일 형식이 올바르지 않습니다.")
        return None

def get_gps_coordinates(image_path):
    """이미지에서 GPS 좌표를 추출합니다."""
    try:
        with Image.open(image_path) as image:
            exif = image._getexif()
  
        if exif is not None:
            for tag, value in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
  
                    if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                        lat = gps_data['GPSLatitude']
                        lon = gps_data['GPSLongitude']
                        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
                        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
  
                        # DMS to Decimal conversion
                        lat_decimal = lat[0] + lat[1]/60 + lat[2]/3600
                        lon_decimal = lon[0] + lon[1]/60 + lon[2]/3600
  
                        if lat_ref == 'S':
                            lat_decimal = -lat_decimal
                        if lon_ref == 'W':
                            lon_decimal = -lon_decimal
  
                        return lat_decimal, lon_decimal
  
        return None, None
  
    except Exception as e:
        print(f"GPS 좌표 추출 중 오류 발생: {e}")
        return None, None

def get_jibun_from_coordinates(lat, lon, api_key):
    """좌표를 지번으로 변환합니다."""
    try:
        url = "http://api.vworld.kr/req/address"
        params = {
            'service': 'address',
            'request': 'getAddress',
            'version': '2.0',
            'crs': 'epsg:4326',
            'point': f"{lon},{lat}",
            'format': 'json',
            'type': 'PARCEL',
            'zipcode': 'true',
            'simple': 'false',
            'key': api_key
        }
  
        response = requests.get(url, params=params, timeout=10)
  
        if response.status_code == 200:
            data = response.json()
            if data['response']['status'] == 'OK':
                result = data['response']['result'][0]
                structure = result['structure']
  
                # 지번 정보 추출
                sido = structure.get('level1', '')
                sigungu = structure.get('level2', '')
                emd = structure.get('level3', '')
                ri = structure.get('level4L', '')  # 리
                jibun = structure.get('detail', '')  # 지번
  
                # 지번 정보 조합
                if ri:
                    full_address = f"{sido} {sigungu} {emd} {ri} {jibun}"
                else:
                    full_address = f"{sido} {sigungu} {emd} {jibun}"
  
                return full_address.strip()
  
        return None
  
    except Exception as e:
        print(f"지번 변환 중 오류 발생: {e}")
        return None

def add_text_to_image(image_path, jibun_text):
    """이미지 하단에 지번 텍스트를 추가합니다."""
    try:
        # 임시 파일 생성
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
  
        with Image.open(image_path) as img:
            # RGB로 변환 (JPEG 저장을 위해)
            if img.mode != 'RGB':
                img = img.convert('RGB')
  
            # 이미지 복사본 생성
            draw = ImageDraw.Draw(img)
  
            # 폰트 설정 (이미지 높이의 6%로 폰트 크기 계산, 최소 80px)
            font_size = max(80, int(img.height * 0.06))
  
            try:
                # Windows 기본 폰트 시도
                font = ImageFont.truetype("malgun.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
  
            # 텍스트 배경 설정
            text_bbox = draw.textbbox((0, 0), jibun_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
  
            # 텍스트 위치 (이미지 하단 중앙)
            x = (img.width - text_width) // 2
            y = img.height - text_height - 30
  
            # 반투명 배경 그리기
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
  
            # 배경 사각형 (패딩 추가)
            padding = 20
            bg_bbox = [
                x - padding,
                y - padding,
                x + text_width + padding,
                y + text_height + padding
            ]
  
            overlay_draw.rounded_rectangle(
                bg_bbox,
                radius=15,
                fill=(0, 0, 0, 180)  # 반투명 검정
            )
  
            # 원본 이미지에 오버레이 합성
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
  
            # 텍스트 그리기
            draw.text((x, y), jibun_text, font=font, fill=(255, 255, 255))
  
            # 임시 파일에 저장
            img.save(temp_path, 'JPEG', quality=95)
  
        # 원본 파일을 임시 파일로 교체
        shutil.move(temp_path, image_path)
  
        return True
  
    except Exception as e:
        # 임시 파일 정리
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        print(f"텍스트 오버레이 중 오류 발생: {e}")
        return False

def generate_filename(jibun_text):
    """지번 정보를 바탕으로 파일명을 생성합니다."""
    try:
        # 지번에서 특수문자 제거 및 공백을 언더스코어로 변경
        clean_jibun = re.sub(r'[^\w\s-]', '', jibun_text).strip()
        clean_jibun = re.sub(r'[\s]+', '_', clean_jibun)
  
        # 현재 시간 (타임스탬프)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  
        # 파일명 생성 (지번_타임스탬프)
        filename = f"{clean_jibun}_{timestamp}.JPG"
  
        return filename
  
    except Exception as e:
        print(f"파일명 생성 중 오류: {e}")
        # 오류 시 기본 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"processed_image_{timestamp}.JPG"

def process_image(image_path, api_key, log_callback=None):
    """개별 이미지를 처리합니다."""
    filename = os.path.basename(image_path)
  
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
  
    try:
        log(f"🔍 {filename}: GPS 좌표 추출 중...")
  
        # 1. GPS 좌표 추출
        lat, lon = get_gps_coordinates(image_path)
        if lat is None or lon is None:
            log(f"❌ {filename}: GPS 좌표 추출 실패")
            return {
                'file': filename,
                'status': 'failed',
                'error': 'GPS 좌표 추출 실패',
                'coordinates': None,
                'jibun': None
            }
  
        log(f"📍 {filename}: GPS 좌표 ({lat:.6f}, {lon:.6f})")
  
        # 2. 지번 변환
        log(f"🔄 {filename}: 지번 변환 중...")
        jibun = get_jibun_from_coordinates(lat, lon, api_key)
        if jibun is None:
            log(f"❌ {filename}: 지번 변환 실패")
            return {
                'file': filename,
                'status': 'failed',
                'error': '지번 변환 실패',
                'coordinates': {'lat': lat, 'lon': lon},
                'jibun': None
            }
  
        log(f"📍 {filename}: 지번 '{jibun}'")
  
        # 3. 텍스트 오버레이
        log(f"✏️ {filename}: 텍스트 오버레이 중...")
        overlay_success = add_text_to_image(image_path, jibun)
        if not overlay_success:
            log(f"⚠️ {filename}: 텍스트 오버레이 실패 (지번 변환은 성공)")
  
        # 4. 파일명 변경
        log(f"📝 {filename}: 파일명 변경 중...")
        new_filename = generate_filename(jibun)
        old_path = image_path
        new_path = os.path.join(os.path.dirname(old_path), new_filename)
  
        # 동일한 파일명이 있으면 번호 추가
        counter = 1
        original_new_path = new_path
        while os.path.exists(new_path):
            base_name, ext = os.path.splitext(original_new_path)
            new_path = f"{base_name}_{counter:02d}{ext}"
            counter += 1
  
        os.rename(old_path, new_path)
        log(f"✅ {filename}: 처리 완료! → {os.path.basename(new_path)}")
  
        return {
            'file': filename,
            'new_file': os.path.basename(new_path),
            'status': 'success',
            'coordinates': {'lat': lat, 'lon': lon},
            'jibun': jibun
        }
  
    except Exception as e:
        log(f"❌ {filename}: 처리 실패 - {str(e)}")
        return {
            'file': filename,
            'status': 'failed',
            'error': str(e),
            'coordinates': None,
            'jibun': None
        }

class DroneImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("드론 GPS → 지번 변환 자동화 시스템 v6.1 (Copyright © 2025)")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f8ff')
  
        # API 키 로드
        self.api_key = load_config()
        if not self.api_key:
            messagebox.showerror("오류", "API 키를 로드할 수 없습니다.\nconfig.json 파일을 확인해주세요.")
            return
  
        self.selected_files = []
        self.processing = False
  
        self.create_widgets()
  
    def create_widgets(self):
        """GUI 위젯을 생성합니다."""
        # 메인 프레임
        main_frame = tk.Frame(self.root, bg='#f0f8ff', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
  
        # 제목
        title_label = tk.Label(
            main_frame,
            text="🚁 드론 이미지 GPS → 지번 변환 자동화",
            font=("맑은 고딕", 16, "bold"),
            bg='#f0f8ff',
            fg='#2c3e50'
        )
        title_label.pack(pady=(0, 10))
  
        # 부제목
        subtitle_label = tk.Label(
            main_frame,
            text="드론 촬영 이미지에서 GPS 좌표를 추출하여 지번으로 변환하고 이미지에 표시합니다",
            font=("맑은 고딕", 10),
            bg='#f0f8ff',
            fg='#7f8c8d'
        )
        subtitle_label.pack(pady=(0, 20))
  
        # 파일 선택 프레임
        file_frame = tk.Frame(main_frame, bg='#f0f8ff')
        file_frame.pack(fill=tk.X, pady=(0, 15))
  
        self.select_button = tk.Button(
            file_frame,
            text="📂 이미지 파일 선택",
            command=self.select_files,
            font=("맑은 고딕", 11, "bold"),
            bg='#3498db',
            fg='white',
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.select_button.pack(side=tk.LEFT)
  
        self.file_count_label = tk.Label(
            file_frame,
            text="선택된 파일: 0개",
            font=("맑은 고딕", 10),
            bg='#f0f8ff',
            fg='#7f8c8d'
        )
        self.file_count_label.pack(side=tk.LEFT, padx=(15, 0))
  
        # 처리 시작 버튼
        self.process_button = tk.Button(
            main_frame,
            text="▶ 처리 시작",
            command=self.start_processing,
            font=("맑은 고딕", 12, "bold"),
            bg='#27ae60',
            fg='white',
            padx=30,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.process_button.pack(pady=(0, 15))
  
        # 진행률 프레임
        progress_frame = tk.Frame(main_frame, bg='#f0f8ff')
        progress_frame.pack(fill=tk.X, pady=(0, 15))
  
        self.progress_label = tk.Label(
            progress_frame,
            text="진행률: 0/0",
            font=("맑은 고딕", 10),
            bg='#f0f8ff',
            fg='#34495e'
        )
        self.progress_label.pack()
  
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400,
        )
        self.progress_bar.pack(pady=(5, 0))
  
        # 로그 영역
        log_frame = tk.Frame(main_frame, bg='#f0f8ff')
        log_frame.pack(fill=tk.BOTH, expand=True)
  
        log_title = tk.Label(
            log_frame,
            text="📋 처리 로그",
            font=("맑은 고딕", 11, "bold"),
            bg='#f0f8ff',
            fg='#2c3e50'
        )
        log_title.pack(anchor=tk.W, pady=(0, 5))
  
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=80,
            height=15,
            font=("Consolas", 9),
            bg='#2c3e50',
            fg='#ecf0f1',
            insertbackground='white'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
  
        # 하단 저작권 표시
        copyright_label = tk.Label(
            self.root,
            text="Copyright © 2025 국립농산물품질관리원. All rights reserved.", 
            font=("맑은 고딕", 8),
            fg="gray",
            bg='#f0f8ff'
        )
        copyright_label.pack(pady=5)
  
        # 초기 메시지
        self.log_message("🚀 프로그램이 시작되었습니다. 이미지 파일을 선택해주세요.")
        self.log_message("💡 GPS 정보가 포함된 JPG 파일만 처리 가능합니다.")
  
    def select_files(self):
        """이미지 파일을 선택합니다."""
        files = filedialog.askopenfilenames(
            title="처리할 드론 이미지를 선택하세요",
            filetypes=[
                ("이미지 파일", "*.jpg *.jpeg *.JPG *.JPEG"),
                ("모든 파일", "*.*")
            ]
        )
  
        if files:
            self.selected_files = list(files)
            self.file_count_label.config(text=f"선택된 파일: {len(files)}개")
            self.process_button.config(state=tk.NORMAL)
  
            self.log_message(f"📁 {len(files)}개 파일이 선택되었습니다.")
            for i, file in enumerate(files, 1):
                filename = os.path.basename(file)
                self.log_message(f"  {i:2d}. {filename}")
  
    def log_message(self, message):
        """로그 메시지를 추가합니다."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
  
    def start_processing(self):
        """이미지 처리를 시작합니다."""
        if self.processing:
            return
  
        if not self.selected_files:
            messagebox.showwarning("경고", "처리할 파일을 선택해주세요.")
            return
  
        self.processing = True
        self.process_button.config(state=tk.DISABLED, text="⏳ 처리 중...")
        self.select_button.config(state=tk.DISABLED)
  
        # 진행률 초기화
        self.progress_bar['maximum'] = len(self.selected_files)
        self.progress_bar['value'] = 0
        self.progress_label.config(text=f"진행률: 0/{len(self.selected_files)}")
  
        # 로그 초기화
        self.log_text.delete(1.0, tk.END)
        self.log_message("🚀 이미지 처리를 시작합니다...")
        self.log_message(f"📊 총 {len(self.selected_files)}개 파일 처리 예정")
        self.log_message("=" * 50)
  
        # 처리 시작
        results = []
        success_count = 0
  
        for i, image_path in enumerate(self.selected_files):
            result = process_image(image_path, self.api_key, self.log_message)
            results.append(result)
  
            if result['status'] == 'success':
                success_count += 1
  
            # 진행률 업데이트
            self.progress_bar['value'] = i + 1
            self.progress_label.config(text=f"진행률: {i + 1}/{len(self.selected_files)}")
            self.root.update()
  
        # 처리 완료
        self.log_message("=" * 50)
        self.log_message(f"🎉 모든 파일 처리 완료!")
        self.log_message(f"✅ 성공: {success_count}개")
        self.log_message(f"❌ 실패: {len(self.selected_files) - success_count}개")
  
        # 결과 리포트 저장
        self.save_report(results)
  
        # UI 상태 복원
        self.processing = False
        self.process_button.config(state=tk.NORMAL, text="▶ 처리 시작")
        self.select_button.config(state=tk.NORMAL)
  
        # 완료 메시지
        messagebox.showinfo(
            "완료", 
            f"처리가 완료되었습니다!\n\n"
            f"성공: {success_count}개\n"
            f"실패: {len(self.selected_files) - success_count}개\n\n"
            f"처리 리포트가 저장되었습니다."
        )
  
    def save_report(self, results):
        """처리 결과 리포트를 저장합니다."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"processing_report_{timestamp}.json"
  
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'total_files': len(results),
                'success_count': len([r for r in results if r['status'] == 'success']),
                'failed_count': len([r for r in results if r['status'] == 'failed']),
                'results': results
            }
  
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
  
            self.log_message(f"📄 처리 리포트 저장: {report_filename}")
  
        except Exception as e:
            self.log_message(f"⚠️ 리포트 저장 실패: {e}")

def main():
    """메인 함수입니다."""
    # 윈도우 생성
    root = tk.Tk()
  
    # 프로그램 아이콘 설정 (옵션)
    try:
        root.iconbitmap('drone.ico')  # 아이콘 파일이 있는 경우
    except:
        pass  # 아이콘 파일이 없어도 무시
  
    # 애플리케이션 생성
    app = DroneImageProcessor(root)
  
    # GUI 실행
    root.mainloop()

if __name__ == "__main__":
    main()