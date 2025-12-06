#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
드론 이미지 GPS → 지번 변환 자동화 시스템
버전: v7.0 (UI 개선 + 옵션 기능 추가, EXE 대응)
개발자: 국립농산물품질관리원 경주사무소 김정연
"""

import os
import sys  # EXE 환경에서 실행 파일 위치를 알기 위해 추가
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import tempfile
import shutil
from datetime import datetime
import re
import traceback

# ───────────────── 공통 경로 함수 (EXE 대응) ─────────────────

def get_app_dir():
    """
    실행 파일(EXE) 또는 스크립트 기준으로
    현재 프로그램이 있는 폴더 경로를 반환합니다.
    - PyInstaller onefile EXE: sys.executable 기준
    - 일반 파이썬 스크립트: __file__ 기준
    """
    if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 실행 파일인 경우
        return os.path.dirname(sys.executable)
    # 일반 파이썬 스크립트 실행 시
    return os.path.dirname(os.path.abspath(__file__))

# ───────────────── 설정 로딩 ─────────────────

def load_config():
    """
    config.json 에서 vworld_api_key 를 읽어옵니다.
    형식 예:
    {
        "vworld_api_key": "발급받은_키"
    }
    """
    try:
        # EXE 또는 스크립트와 같은 폴더의 config.json을 찾도록 변경
        config_path = os.path.join(get_app_dir(), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            api_key = config.get('vworld_api_key')
            if not api_key:
                print("config.json에 'vworld_api_key' 항목이 없습니다.")
                return None
            return api_key
    except FileNotFoundError:
        print("config.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("config.json 파일 형식이 올바르지 않습니다.")
        return None
    except Exception as e:
        print(f"config.json 로드 중 오류: {e}")
        return None

# ───────────────── EXIF / GPS 처리 ─────────────────

def _to_float(x):
    """IFDRational, (num, den), 숫자 등 다양한 형태를 float으로 변환"""
    try:
        if isinstance(x, tuple) and len(x) == 2:
            num, den = x
            return float(num) / float(den) if den else 0.0
        return float(x)
    except Exception:
        return 0.0

def _dms_to_deg(dms):
    """(도, 분, 초) → 도(degree)"""
    d, m, s = dms
    return _to_float(d) + _to_float(m) / 60.0 + _to_float(s) / 3600.0

def get_gps_coordinates(image_path):
    """이미지 EXIF에서 GPS 좌표 추출 (위도, 경도) 반환. 없으면 (None, None)."""
    try:
        with Image.open(image_path) as image:
            exif = image._getexif()
        
        if exif is None:
            return None, None
        
        gps_info = None
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_info = value
                break
        
        if gps_info is None:
            return None, None
        
        gps_data = {GPSTAGS.get(t, t): gps_info[t] for t in gps_info}
        
        if 'GPSLatitude' not in gps_data or 'GPSLongitude' not in gps_data:
            return None, None
        
        lat = _dms_to_deg(gps_data['GPSLatitude'])
        lon = _dms_to_deg(gps_data['GPSLongitude'])
        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        
        if lat_ref == 'S':
            lat = -lat
        if lon_ref == 'W':
            lon = -lon
        
        return float(lat), float(lon)
    
    except Exception as e:
        print(f"GPS 좌표 추출 오류: {e}")
        return None, None

def get_exif_datetime(image_path):
    """
    EXIF 촬영 시간을 문자열로 반환.
    형식: 'YYYY-MM-DD HH:MM:SS'
    없으면 None.
    """
    try:
        with Image.open(image_path) as image:
            exif = image._getexif()
        if exif is None:
            return None
        
        datetime_value = None
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if decoded in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                datetime_value = value
                break
        
        if not datetime_value:
            return None
        
        # "YYYY:MM:DD HH:MM:SS" → "YYYY-MM-DD HH:MM:SS"
        try:
            dt = datetime.strptime(datetime_value, "%Y:%m:%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime_value
    except Exception:
        return None

# ───────────────── 지번 파싱 / VWorld API ─────────────────

def parse_jibun_structure(structure):
    sigungu = structure.get('level2', '').strip()
    emd = structure.get('level3', '').strip()
    ri = structure.get('level4L', '').strip()
    detail = structure.get('detail', '').strip()
    level5 = structure.get('level5', '').strip()
    
    parts = []
    
    if sigungu:
        parts.append(sigungu)
    
    if emd:
        parts.append(emd)
    elif ri and ('면' in ri or '읍' in ri or '동' in ri):
        parts.append(ri)
        ri = ''
    
    if ri and ri not in parts:
        if '리' in ri or '동' in ri:
            parts.append(ri)
    
    if detail:
        parts.append(detail)
    elif level5 and level5 not in parts:
        if re.match(r'\d+', level5) or '-' in level5:
            cleaned = re.sub(r'리$', '', level5)
            parts.append(cleaned)
    
    return ' '.join(parts).strip()

def get_jibun_from_coordinates(lat, lon, api_key, log_callback=None, retries=2):
    """VWorld API를 사용해 위/경도 → 지번 변환."""
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    url = "https://api.vworld.kr/req/address"
    params = {
        'service': 'address',
        'request': 'getAddress',
        'version': '2.0',
        'crs': 'epsg:4326',
        'point': f"{float(lon)},{float(lat)}",
        'format': 'json',
        'type': 'PARCEL',
        'zipcode': 'true',
        'simple': 'false',
        'key': api_key
    }
    
    for attempt in range(retries + 1):
        try:
            log(f"[DEBUG] VWorld API 호출({attempt+1}차): {params['point']}")
            response = requests.get(url, params=params, timeout=30)
            log(f"[DEBUG] 응답 코드: {response.status_code}")
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            status = data.get('response', {}).get('status', 'UNKNOWN')
            if status != 'OK':
                err = data.get('response', {}).get('error', {})
                log(f"[ERROR] VWorld 상태: {status}, 상세: {err}")
                continue
            
            results = data.get('response', {}).get('result', [])
            if not results:
                continue
            
            structure = results[0].get('structure', {})
            full_address = parse_jibun_structure(structure)
            if not full_address:
                continue
            
            log(f"[SUCCESS] 최종 지번: {full_address}")
            return full_address
        except Exception as e:
            log(f"[ERROR] VWorld 호출 예외: {e}")
    
    return None

# ───────────────── 이미지 텍스트 오버레이 ─────────────────

def add_text_to_image(image_path, overlay_text, position="bottom_center"):
    """
    이미지 하단에 반투명 박스 + 텍스트 오버레이.
    overlay_text: 여러 줄일 경우 '\n' 사용.
    position: 'bottom_center', 'bottom_left', 'bottom_right'
    """
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
        
        with Image.open(image_path) as img:
            # EXIF 회전 보정
            img = ImageOps.exif_transpose(img)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            draw = ImageDraw.Draw(img)
            
            # 기본 폰트 크기 (이미지 높이에 비례)
            base_font_size = int(img.height * 0.05)
            font_size = max(24, base_font_size)
            
            # 줄바꿈 처리
            lines = overlay_text.split("\n")
            
            # 폰트 로딩 & 글자 폭에 맞게 크기 조정
            def get_font(size):
                try:
                    return ImageFont.truetype("malgun.ttf", size)
                except:
                    try:
                        return ImageFont.truetype("arial.ttf", size)
                    except:
                        return ImageFont.load_default()
            
            font = get_font(font_size)
            max_width = 0
            line_heights = []
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                max_width = max(max_width, w)
                line_heights.append(h)
            
            # 너무 넓으면 폰트 크기 줄이기
            while max_width > img.width * 0.9 and font_size > 14:
                font_size -= 2
                font = get_font(font_size)
                max_width = 0
                line_heights = []
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                    max_width = max(max_width, w)
                    line_heights.append(h)
            
            total_text_height = sum(line_heights) + (len(lines) - 1) * int(font_size * 0.3)
            
            # 위치 계산
            margin_bottom = int(img.height * 0.03)
            x_left = int(img.width * 0.05)
            x_right = img.width - int(img.width * 0.05) - max_width
            
            if position == "bottom_left":
                x = x_left
            elif position == "bottom_right":
                x = x_right
            else:  # bottom_center
                x = (img.width - max_width) // 2
            
            y = img.height - total_text_height - margin_bottom
            
            # 반투명 배경 박스
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            padding_x = int(font_size * 0.8)
            padding_y = int(font_size * 0.5)
            
            bg_bbox = [
                x - padding_x,
                y - padding_y,
                x + max_width + padding_x,
                y + total_text_height + padding_y
            ]
            
            overlay_draw.rounded_rectangle(
                bg_bbox,
                radius=int(font_size * 0.8),
                fill=(0, 0, 0, 180)
            )
            
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # 텍스트 실제 그리기 (여러 줄)
            current_y = y
            for line, h in zip(lines, line_heights):
                draw.text((x, current_y), line, font=font, fill=(255, 255, 255))
                current_y += h + int(font_size * 0.3)
            
            img.save(temp_path, 'JPEG', quality=95)
        
        shutil.move(temp_path, image_path)
        return True
    
    except Exception as e:
        print(f"텍스트 오버레이 실패: {e}")
        return False

# ───────────────── 파일명 생성 ─────────────────

def generate_filename(jibun_text):
    """
    지번 텍스트를 기반으로 파일명 생성.
    - 한글은 그대로 두고, 파일 시스템에서 문제되는 문자만 제거.
    - 공백은 '_'로 치환.
    """
    try:
        # 파일명에서 사용할 수 없는 문자 제거: \ / : * ? " < > |
        clean_jibun = re.sub(r'[\\/:*?"<>|]', '_', jibun_text).strip()
        clean_jibun = re.sub(r'\s+', '_', clean_jibun)
        if not clean_jibun:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"processed_image_{timestamp}.JPG"
        return f"{clean_jibun}.JPG"
    except Exception:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"processed_image_{timestamp}.JPG"

# ───────────────── 전체 처리 로직 ─────────────────

def process_image(image_path, api_key, options, log_callback=None):
    """
    단일 이미지 처리:
      - GPS 추출
      - 지번 변환
      - 오버레이 텍스트 생성
      - 원본 보존/폴더/파일명 옵션 반영
    options: dict
      - keep_original (bool)
      - rename_by_jibun (bool)
      - text_position ('하단 중앙'/'하단 좌측'/'하단 우측')
      - show_coords (bool)
      - show_datetime (bool)
    """
    filename = os.path.basename(image_path)
    
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    try:
        log(f"🔍 {filename}: GPS 좌표 추출 중...")
        
        lat, lon = get_gps_coordinates(image_path)
        if lat is None or lon is None:
            log(f"❌ {filename}: GPS 좌표 추출 실패")
            return {
                'file': filename,
                'status': 'failed',
                'error': 'GPS 좌표 추출 실패',
                'coordinates': None,
                'jibun': None,
                'output_file': None
            }
        
        lat = float(lat)
        lon = float(lon)
        log(f"📍 {filename}: GPS 좌표 ({lat:.6f}, {lon:.6f})")
        
        log(f"🔄 {filename}: 지번 변환 중...")
        jibun = get_jibun_from_coordinates(lat, lon, api_key, log)
        
        if not jibun:
            log(f"❌ {filename}: 지번 변환 실패")
            return {
                'file': filename,
                'status': 'failed',
                'error': '지번 변환 실패',
                'coordinates': {'lat': lat, 'lon': lon},
                'jibun': None,
                'output_file': None
            }
        
        log(f"📍 {filename}: 지번 '{jibun}'")
        
        # 오버레이 텍스트 구성
        text_lines = [jibun]
        if options.get('show_coords', False):
            text_lines.append(f"{lat:.6f}, {lon:.6f}")
        if options.get('show_datetime', False):
            exif_time = get_exif_datetime(image_path)
            if exif_time:
                text_lines.append(f"촬영: {exif_time}")
        
        overlay_text = "\n".join(text_lines)
        
        # 출력 경로 결정
        orig_dir = os.path.dirname(image_path)
        orig_name = os.path.basename(image_path)
        
        keep_original = options.get('keep_original', True)
        rename_by_jibun = options.get('rename_by_jibun', True)
        
        if keep_original:
            out_dir = os.path.join(orig_dir, "processed_images")
        else:
            out_dir = orig_dir
        
        os.makedirs(out_dir, exist_ok=True)
        
        # 파일명 결정
        if rename_by_jibun and jibun:
            base_filename = generate_filename(jibun)
        else:
            base_filename = orig_name
        
        dest_path = os.path.join(out_dir, base_filename)
        dest_base, dest_ext = os.path.splitext(dest_path)
        
        # 중복 방지
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{dest_base}_{counter:02d}{dest_ext}"
            counter += 1
        
        # 원본 보존 여부에 따라 복사/덮어쓰기
        if keep_original or (out_dir != orig_dir or base_filename != orig_name):
            # 별도 파일에 저장
            shutil.copy2(image_path, dest_path)
        else:
            # 원본 덮어쓰기 (경로 동일)
            dest_path = image_path
        
        # 텍스트 위치 옵션 매핑
        pos_map = {
            "하단 중앙": "bottom_center",
            "하단 좌측": "bottom_left",
            "하단 우측": "bottom_right"
        }
        pos_key = options.get('text_position', "하단 중앙")
        position = pos_map.get(pos_key, "bottom_center")
        
        log(f"✏️ {filename}: 텍스트 오버레이 중...")
        overlay_success = add_text_to_image(dest_path, overlay_text, position=position)
        
        if not overlay_success:
            log(f"⚠️ {filename}: 텍스트 오버레이 실패")
            return {
                'file': filename,
                'status': 'failed',
                'error': '텍스트 오버레이 실패',
                'coordinates': {'lat': lat, 'lon': lon},
                'jibun': jibun,
                'output_file': dest_path
            }
        
        log(f"✅ {filename}: 처리 완료! → {os.path.basename(dest_path)}")
        
        return {
            'file': filename,
            'new_file': os.path.basename(dest_path),
            'status': 'success',
            'coordinates': {'lat': lat, 'lon': lon},
            'jibun': jibun,
            'output_file': dest_path
        }
    
    except Exception as e:
        log(f"❌ {filename}: 처리 실패 - {str(e)}")
        traceback.print_exc()
        return {
            'file': filename,
            'status': 'failed',
            'error': str(e),
            'coordinates': None,
            'jibun': None,
            'output_file': None
        }

# ───────────────── GUI 클래스 ─────────────────

class DroneImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("드론 GPS → 지번 변환 자동화 시스템 v7.0")
        self.root.geometry("950x750")
        self.root.configure(bg='#ffffff')
        self.root.resizable(True, True)
        self.root.minsize(850, 650)
        
        self.api_key = load_config()
        if not self.api_key:
            messagebox.showerror("오류", "API 키를 로드할 수 없습니다.\nconfig.json 파일과 vworld_api_key를 확인해주세요.")
            root.destroy()
            return
        
        self.selected_files = []
        self.processing = False
        
        # 옵션 변수들
        self.var_keep_original = tk.BooleanVar(value=True)
        self.var_rename_by_jibun = tk.BooleanVar(value=True)
        self.var_show_coords = tk.BooleanVar(value=False)
        self.var_show_datetime = tk.BooleanVar(value=False)
        self.var_text_position = tk.StringVar(value="하단 중앙")
        
        self.create_widgets()
    
    def create_widgets(self):
        # ───────── 메인 프레임 레이아웃 ─────────
        main_frame = tk.Frame(self.root, bg='#ffffff', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        
        # ───────── 상단 헤더 ─────────
        header_frame = tk.Frame(main_frame, bg='#4A90E2')
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        header_inner = tk.Frame(header_frame, bg='#4A90E2', padx=10, pady=10)
        header_inner.pack(fill=tk.X)
        
        title_label = tk.Label(
            header_inner,
            text="🚁 드론 이미지 GPS → 지번 변환 자동화",
            font=("맑은 고딕", 18, "bold"),
            bg='#4A90E2',
            fg='#ffffff'
        )
        title_label.pack(anchor="w")
        
        version_label = tk.Label(
            header_inner,
            text="v7.0  |  국립농산물품질관리원 경주사무소",
            font=("맑은 고딕", 9),
            bg='#4A90E2',
            fg='#e0e0e0'
        )
        version_label.pack(anchor="w", pady=(2, 4))
        
        subtitle_label = tk.Label(
            header_inner,
            text="드론 촬영 이미지에서 GPS 좌표를 자동 추출하여 지번으로 변환하고, "
                 "이미지 하단에 표시 및 파일명을 자동 변경합니다.",
            font=("맑은 고딕", 9),
            bg='#4A90E2',
            fg='#f1f3f5',
            justify=tk.LEFT
        )
        subtitle_label.pack(anchor="w")
        
        # ───────── 좌측: 파일 선택 + 진행 + 로그 ─────────
        left_frame = tk.Frame(main_frame, bg='#ffffff')
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_frame.rowconfigure(3, weight=1)
        
        # 파일 선택 카드
        file_card = tk.Frame(left_frame, bg='#f8f9fa')
        file_card.grid(row=0, column=0, sticky="ew", pady=(0, 15), ipady=10, ipadx=10)
        
        file_frame = tk.Frame(file_card, bg='#f8f9fa')
        file_frame.pack(fill=tk.X)
        
        self.select_button = tk.Button(
            file_frame,
            text="📂  이미지 파일 선택",
            command=self.select_files,
            font=("맑은 고딕", 11, "bold"),
            bg='#5cb85c',
            fg='white',
            padx=25,
            pady=8,
            relief=tk.FLAT,
            cursor='hand2',
            activebackground='#4cae4c'
        )
        self.select_button.pack(side=tk.LEFT)
        
        self.file_count_label = tk.Label(
            file_frame,
            text="선택된 파일: 0개",
            font=("맑은 고딕", 11),
            bg='#f8f9fa',
            fg='#495057'
        )
        self.file_count_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # 처리 버튼
        self.process_button = tk.Button(
            left_frame,
            text="▶  처리 시작",
            command=self.start_processing,
            font=("맑은 고딕", 13, "bold"),
            bg='#007bff',
            fg='white',
            padx=50,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2',
            state=tk.DISABLED,
            activebackground='#0056b3'
        )
        self.process_button.grid(row=1, column=0, pady=(0, 15), sticky="w")
        
        # 진행률 카드
        progress_card = tk.Frame(left_frame, bg='#f8f9fa')
        progress_card.grid(row=2, column=0, sticky="ew", pady=(0, 15), ipady=10, ipadx=10)
        
        progress_frame = tk.Frame(progress_card, bg='#f8f9fa')
        progress_frame.pack(fill=tk.X)
        
        self.progress_label = tk.Label(
            progress_frame,
            text="📊 진행률: 0/0",
            font=("맑은 고딕", 11, "bold"),
            bg='#f8f9fa',
            fg='#495057'
        )
        self.progress_label.pack(pady=(0, 6))
        
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#e9ecef',
            background='#28a745',
            bordercolor='#dee2e6',
            lightcolor='#28a745',
            darkcolor='#28a745',
            thickness=20
        )
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=500,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(pady=(0, 2))
        
        # 로그 영역
        log_frame = tk.Frame(left_frame, bg='#ffffff')
        log_frame.grid(row=3, column=0, sticky="nsew")
        
        log_title = tk.Label(
            log_frame,
            text="📋 처리 로그",
            font=("맑은 고딕", 12, "bold"),
            bg='#ffffff',
            fg='#212529'
        )
        log_title.pack(anchor=tk.W, pady=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=85,
            height=14,
            font=("Consolas", 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=1,
            highlightbackground='#dee2e6'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ───────── 우측: 사용 방법 + 옵션 ─────────
        right_frame = tk.Frame(main_frame, bg='#ffffff')
        right_frame.grid(row=1, column=1, sticky="nsew")
        right_frame.rowconfigure(1, weight=1)
        
        # 사용 방법 카드
        guide_card = tk.Frame(right_frame, bg='#f8f9fa')
        guide_card.grid(row=0, column=0, sticky="ew", pady=(0, 10), ipadx=10, ipady=10)
        
        guide_title = tk.Label(
            guide_card,
            text="ℹ 사용 방법",
            font=("맑은 고딕", 12, "bold"),
            bg='#f8f9fa',
            fg='#212529'
        )
        guide_title.pack(anchor="w", pady=(0, 5))
        
        guide_text = (
            "1️⃣ [이미지 파일 선택] 버튼으로 드론 촬영 JPG 파일을 선택합니다.\n"
            "2️⃣ [처리 시작] 버튼을 누르면,\n"
            "   • GPS 좌표 → 지번 변환\n"
            "   • 이미지 하단에 지번 및 선택한 정보 표시\n"
            "   • (옵션에 따라) 지번 기반 파일명으로 저장\n\n"
            "⚠ GPS 정보가 없는 JPG 파일은 자동으로 '실패'로 분류되며,\n"
            "   처리 리포트(JSON)에서 상세 내용을 확인할 수 있습니다.\n"
            "💾 프로그램 폴더에 'processing_report_YYYYMMDD_HHMMSS.json' 파일이 저장됩니다."
        )
        
        guide_label = tk.Label(
            guide_card,
            text=guide_text,
            font=("맑은 고딕", 10),
            bg='#f8f9fa',
            fg='#495057',
            justify=tk.LEFT
        )
        guide_label.pack(fill=tk.X)
        
        # 옵션 카드
        option_card = tk.Frame(right_frame, bg='#f8f9fa')
        option_card.grid(row=1, column=0, sticky="nsew", ipadx=10, ipady=10)
        
        option_title = tk.Label(
            option_card,
            text="⚙ 옵션",
            font=("맑은 고딕", 12, "bold"),
            bg='#f8f9fa',
            fg='#212529'
        )
        option_title.pack(anchor="w", pady=(0, 5))
        
        # 체크박스들
        cb1 = tk.Checkbutton(
            option_card,
            text="원본 이미지는 유지하고, processed_images 폴더에 결과 저장",
            variable=self.var_keep_original,
            font=("맑은 고딕", 9),
            bg='#f8f9fa',
            anchor="w"
        )
        cb1.pack(fill=tk.X, anchor="w")
        
        cb2 = tk.Checkbutton(
            option_card,
            text="지번으로 파일명 변경 (예: 경주시_안강읍_123-4.JPG)",
            variable=self.var_rename_by_jibun,
            font=("맑은 고딕", 9),
            bg='#f8f9fa',
            anchor="w"
        )
        cb2.pack(fill=tk.X, anchor="w")
        
        cb3 = tk.Checkbutton(
            option_card,
            text="위·경도도 함께 표시",
            variable=self.var_show_coords,
            font=("맑은 고딕", 9),
            bg='#f8f9fa',
            anchor="w"
        )
        cb3.pack(fill=tk.X, anchor="w")
        
        cb4 = tk.Checkbutton(
            option_card,
            text="EXIF 촬영 시간도 함께 표시 (가능한 경우)",
            variable=self.var_show_datetime,
            font=("맑은 고딕", 9),
            bg='#f8f9fa',
            anchor="w"
        )
        cb4.pack(fill=tk.X, anchor="w")
        
        # 텍스트 위치 선택
        pos_frame = tk.Frame(option_card, bg='#f8f9fa')
        pos_frame.pack(fill=tk.X, pady=(10, 0))
        
        pos_label = tk.Label(
            pos_frame,
            text="텍스트 위치:",
            font=("맑은 고딕", 9, "bold"),
            bg='#f8f9fa',
            fg='#212529'
        )
        pos_label.pack(side=tk.LEFT)
        
        pos_combo = ttk.Combobox(
            pos_frame,
            textvariable=self.var_text_position,
            values=["하단 중앙", "하단 좌측", "하단 우측"],
            state="readonly",
            width=10
        )
        pos_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # ───────── 하단 상태바 ─────────
        footer_frame = tk.Frame(self.root, bg='#ffffff')
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        
        separator = tk.Frame(footer_frame, height=1, bg='#dee2e6')
        separator.pack(fill=tk.X)
        
        status_frame = tk.Frame(footer_frame, bg='#ffffff')
        status_frame.pack(fill=tk.X, pady=4, padx=8)
        
        api_label = tk.Label(
            status_frame,
            text="VWorld API: 로드 완료",
            font=("맑은 고딕", 8),
            fg="#28a745",
            bg='#ffffff'
        )
        api_label.pack(side=tk.LEFT)
        
        copy_label = tk.Label(
            status_frame,
            text="Copyright © 2025 국립농산물품질관리원",
            font=("맑은 고딕", 8),
            fg="#6c757d",
            bg='#ffffff'
        )
        copy_label.pack(side=tk.RIGHT)
        
        # 초기 안내 로그
        self.log_message("🚀 프로그램이 시작되었습니다. 이미지 파일을 선택해주세요.")
        self.log_message("💡 GPS 정보가 포함된 JPG 파일만 처리 가능합니다.")
    
    def select_files(self):
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
            
            self.log_text.delete(1.0, tk.END)
            self.log_message(f"📁 {len(files)}개 파일이 선택되었습니다.")
            for i, file in enumerate(files, 1):
                filename = os.path.basename(file)
                self.log_message(f"  {i:2d}. {filename}")
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def start_processing(self):
        if self.processing:
            return
        
        if not self.selected_files:
            messagebox.showwarning("경고", "처리할 파일을 선택해주세요.")
            return
        
        self.processing = True
        self.process_button.config(state=tk.DISABLED, text="⏳ 처리 중...")
        self.select_button.config(state=tk.DISABLED)
        
        self.progress_bar['maximum'] = len(self.selected_files)
        self.progress_bar['value'] = 0
        self.progress_label.config(text=f"📊 진행률: 0/{len(self.selected_files)}")
        
        self.log_text.delete(1.0, tk.END)
        self.log_message("🚀 이미지 처리를 시작합니다...")
        self.log_message(f"📊 총 {len(self.selected_files)}개 파일 처리 예정")
        self.log_message("=" * 50)
        
        # 옵션 수집
        options = {
            'keep_original': self.var_keep_original.get(),
            'rename_by_jibun': self.var_rename_by_jibun.get(),
            'show_coords': self.var_show_coords.get(),
            'show_datetime': self.var_show_datetime.get(),
            'text_position': self.var_text_position.get()
        }
        
        results = []
        success_count = 0
        
        for i, image_path in enumerate(self.selected_files):
            result = process_image(image_path, self.api_key, options, self.log_message)
            results.append(result)
            
            if result['status'] == 'success':
                success_count += 1
            
            self.progress_bar['value'] = i + 1
            self.progress_label.config(text=f"📊 진행률: {i + 1}/{len(self.selected_files)}")
            self.root.update()
        
        self.log_message("=" * 50)
        self.log_message(f"🎉 모든 파일 처리 완료!")
        self.log_message(f"✅ 성공: {success_count}개")
        self.log_message(f"❌ 실패: {len(self.selected_files) - success_count}개")
        
        self.save_report(results)
        
        self.processing = False
        self.process_button.config(state=tk.NORMAL, text="▶ 처리 시작")
        self.select_button.config(state=tk.NORMAL)
        
        messagebox.showinfo(
            "완료", 
            f"처리가 완료되었습니다!\n\n"
            f"성공: {success_count}개\n"
            f"실패: {len(self.selected_files) - success_count}개\n\n"
            f"처리 리포트가 저장되었습니다."
        )
    
    def save_report(self, results):
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
            
            # 프로그램이 있는 폴더에 저장
            report_path = os.path.join(get_app_dir(), report_filename)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"📄 처리 리포트 저장: {report_path}")
        
        except Exception as e:
            self.log_message(f"⚠️ 리포트 저장 실패: {e}")

# ───────────────── main ─────────────────

def main():
    # EXE든 파이썬이든 항상 프로그램 폴더를 작업 폴더로 사용
    app_dir = get_app_dir()
    os.chdir(app_dir)

    root = tk.Tk()
    try:
        icon_path = os.path.join(app_dir, 'drone.ico')
        root.iconbitmap(icon_path)
    except Exception:
        pass
    app = DroneImageProcessor(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # EXE에서 오류가 나도 창이 바로 닫히지 않도록
        print("프로그램 실행 중 오류 발생:", e)
        traceback.print_exc()
        input("엔터를 누르면 종료합니다...")
