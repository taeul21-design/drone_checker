
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
드론 이미지 GPS → 지번 변환 GUI 메인 프로그램 v6
작성일: 2025년 1월
기능: 이미지 하단 지번 표시 + 파일명 자동 변경
"""

import json
import requests
import os
import sys
import shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS, GPSTAGS
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading

class DroneImageProcessor:
    """드론 이미지 처리 메인 클래스"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("드론 이미지 GPS → 지번 변환 v6 (완전판)")
        self.root.geometry("900x700")
        
        # 설정 로드
        self.config = self.load_config()
        if not self.config:
            messagebox.showerror("설정 오류", "config.json 파일을 찾을 수 없습니다!")
            self.root.destroy()
            return
        
        self.api_key = self.config.get('vworld_api_key', '')
        
        # 파일 목록
        self.image_files = []
        self.processing = False
        
        # GUI 구성
        self.setup_ui()
        
        # 시작 로그
        self.log_message("=" * 80)
        self.log_message("🚁 드론 이미지 GPS → 지번 변환 프로그램 v6 (완전판)")
        self.log_message("✨ 기능: 이미지 하단 지번 표시 + 파일명 자동 변경")
        self.log_message("=" * 80)
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def setup_ui(self):
        """GUI 구성"""
        # 상단: 제목
        title_frame = tk.Frame(self.root, bg="#2c3e50", pady=15)
        title_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text="🚁 드론 이미지 GPS → 지번 변환",
            font=("맑은 고딕", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="✨ v6 완전판 | 이미지 지번 표시 + 파일명 자동 변경",
            font=("맑은 고딕", 10),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        subtitle_label.pack()
        
        # 버튼 영역
        button_frame = tk.Frame(self.root, pady=10)
        button_frame.pack(fill=tk.X, padx=20)
        
        self.select_button = tk.Button(
            button_frame,
            text="📂 이미지 파일 선택",
            command=self.select_files,
            font=("맑은 고딕", 11),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=10,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.select_button.pack(side=tk.LEFT, padx=5)
        
        self.process_button = tk.Button(
            button_frame,
            text="▶ 처리 시작",
            command=self.start_processing,
            font=("맑은 고딕", 11),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            relief=tk.RAISED,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(
            button_frame,
            text="🔄 초기화",
            command=self.clear_all,
            font=("맑은 고딕", 11),
            bg="#e74c3c",
            fg="white",
            padx=20,
            pady=10,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 파일 목록 영역
        file_frame = tk.LabelFrame(
            self.root,
            text="📋 선택된 파일 목록",
            font=("맑은 고딕", 10, "bold"),
            padx=10,
            pady=10
        )
        file_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=5)
        
        self.file_listbox = tk.Listbox(
            file_frame,
            height=5,
            font=("맑은 고딕", 9),
            selectmode=tk.SINGLE
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        file_scrollbar = tk.Scrollbar(file_frame, command=self.file_listbox.yview)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)
        
        # 진행률 영역
        progress_frame = tk.LabelFrame(
            self.root,
            text="📊 진행 상황",
            font=("맑은 고딕", 10, "bold"),
            padx=10,
            pady=10
        )
        progress_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.progress_label = tk.Label(
            progress_frame,
            text="대기 중...",
            font=("맑은 고딕", 9)
        )
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(pady=5)
        
        # 로그 영역
        log_frame = tk.LabelFrame(
            self.root,
            text="📝 처리 로그",
            font=("맑은 고딕", 10, "bold"),
            padx=10,
            pady=10
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 통계 영역
        stats_frame = tk.Frame(self.root, pady=5)
        stats_frame.pack(fill=tk.X, padx=20)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="통계: 선택 0개 | 성공 0개 | 실패 0개",
            font=("맑은 고딕", 9),
            fg="#7f8c8d"
        )
        self.stats_label.pack()
    
    def select_files(self):
        """이미지 파일 선택"""
        files = filedialog.askopenfilenames(
            title="드론 이미지 선택",
            filetypes=[
                ("이미지 파일", "*.jpg *.jpeg *.JPG *.JPEG"),
                ("모든 파일", "*.*")
            ]
        )
        
        if files:
            # 중복 제거 및 백업 폴더 제외
            unique_files = []
            for file in files:
                abs_path = os.path.abspath(file)
                
                # 백업 폴더 파일 제외
                if 'backup_' in abs_path:
                    self.log_message(f"⚠️ 백업 파일 제외: {os.path.basename(file)}")
                    continue
                
                # 중복 제거
                if abs_path not in unique_files:
                    unique_files.append(abs_path)
                else:
                    self.log_message(f"⚠️ 중복 파일 제외: {os.path.basename(file)}")
            
            self.image_files = unique_files
            self.file_listbox.delete(0, tk.END)
            
            for file in self.image_files:
                self.file_listbox.insert(tk.END, os.path.basename(file))
            
            self.process_button.config(state=tk.NORMAL)
            self.log_message(f"✅ {len(self.image_files)}개의 이미지 파일 선택됨 (중복/백업 제외)")
            self.update_stats()
    
    def start_processing(self):
        """처리 시작 (별도 스레드)"""
        if self.processing:
            messagebox.showwarning("경고", "이미 처리 중입니다!")
            return
        
        if not self.image_files:
            messagebox.showwarning("경고", "이미지 파일을 먼저 선택하세요!")
            return
        
        # 확인 메시지
        result = messagebox.askyesno(
            "처리 시작",
            f"{len(self.image_files)}개의 이미지를 처리합니다.\n\n"
            "✨ 텍스트 오버레이: 활성화 (이미지 하단에 지번 표시)\n"
            "📝 파일명 변경: 지번으로 자동 변경\n"
            "   예) DJI_0001.JPG → 경상북도_경주시_산내면_내일리_167-4.JPG\n"
            "⚠️ 원본 파일이 직접 수정됩니다 (백업 없음)\n\n"
            "계속하시겠습니까?"
        )
        
        if not result:
            return
        
        # UI 비활성화
        self.processing = True
        self.select_button.config(state=tk.DISABLED)
        self.process_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        
        # 별도 스레드에서 처리
        thread = threading.Thread(target=self.process_images)
        thread.daemon = True
        thread.start()
    
    def process_images(self):
        """이미지 일괄 처리 - v6: 이미지 지번 표시 + 파일명 변경"""
        total = len(self.image_files)
        success_count = 0
        fail_count = 0
        
        self.log_message("\n" + "=" * 80)
        self.log_message("🚀 일괄 처리 시작 (이미지 지번 표시 + 파일명 변경)")
        self.log_message("=" * 80)
        
        # 결과 저장용
        results = []
        
        for idx, image_path in enumerate(self.image_files, 1):
            filename = os.path.basename(image_path)
            
            self.log_message(f"\n[{idx}/{total}] 처리 중: {filename}")
            self.update_progress(idx, total, f"처리 중: {filename}")
            
            try:
                # 1. GPS 좌표 추출
                lat, lon = self.extract_gps(image_path)
                
                if lat is None or lon is None:
                    self.log_message(f"  ❌ GPS 좌표 추출 실패")
                    fail_count += 1
                    results.append({
                        'filename': filename,
                        'status': 'FAIL',
                        'reason': 'GPS_NOT_FOUND'
                    })
                    continue
                
                self.log_message(f"  📍 GPS: {lat:.6f}, {lon:.6f}")
                
                # 2. 지번 변환
                address_info = self.convert_to_address(lat, lon)
                
                if not address_info['success']:
                    self.log_message(f"  ❌ 지번 변환 실패")
                    fail_count += 1
                    results.append({
                        'filename': filename,
                        'status': 'FAIL',
                        'reason': 'ADDRESS_CONVERSION_FAILED',
                        'gps': f"{lat:.6f},{lon:.6f}"
                    })
                    continue
                
                full_address = address_info['full_address']
                self.log_message(f"  🏠 주소: {full_address}")
                
                # 3. 🎨 텍스트 오버레이 적용 (원본 파일에 바로!)
                self.log_message(f"  🎨 텍스트 오버레이 적용 중...")
                overlay_success = self.add_text_overlay(image_path, full_address)
                
                if not overlay_success:
                    self.log_message(f"  ⚠️ 텍스트 오버레이 적용 실패")
                    fail_count += 1
                    results.append({
                        'filename': filename,
                        'status': 'FAIL',
                        'reason': 'OVERLAY_FAILED'
                    })
                    continue
                
                self.log_message(f"  ✅ 텍스트 오버레이 적용 완료!")
                
                # 4. 📝 파일명 변경 (지번으로)
                new_filename = self.generate_filename(address_info, filename)
                new_path = os.path.join(os.path.dirname(image_path), new_filename)
                
                # 파일명 중복 처리
                if os.path.exists(new_path) and new_path != image_path:
                    base, ext = os.path.splitext(new_filename)
                    counter = 1
                    while os.path.exists(new_path):
                        new_filename = f"{base}_{counter}{ext}"
                        new_path = os.path.join(os.path.dirname(image_path), new_filename)
                        counter += 1
                
                # 파일명 변경
                if new_path != image_path:
                    os.rename(image_path, new_path)
                    self.log_message(f"  📝 파일명 변경: {filename} → {new_filename}")
                else:
                    self.log_message(f"  📝 파일명 유지: {filename}")
                
                success_count += 1
                results.append({
                    'filename': filename,
                    'new_filename': new_filename,
                    'status': 'SUCCESS',
                    'address': full_address,
                    'gps': f"{lat:.6f},{lon:.6f}",
                    'overlay_applied': True
                })
                
                self.log_message(f"  ✅ 처리 완료!")
                
            except Exception as e:
                self.log_message(f"  ❌ 오류 발생: {e}")
                import traceback
                self.log_message(f"  📋 상세 오류: {traceback.format_exc()}")
                fail_count += 1
                results.append({
                    'filename': filename,
                    'status': 'ERROR',
                    'reason': str(e)
                })
        
        # 처리 완료
        self.log_message("\n" + "=" * 80)
        self.log_message("🎉 일괄 처리 완료!")
        self.log_message("=" * 80)
        self.log_message(f"📊 전체: {total}개")
        self.log_message(f"✅ 성공: {success_count}개 (이미지에 지번 표시 + 파일명 변경)")
        self.log_message(f"❌ 실패: {fail_count}개")
        self.log_message(f"💡 처리된 이미지는 지번이 포함된 파일명으로 저장되었습니다.")
        
        # 결과 리포트 저장
        self.save_report_simple(results)
        
        # UI 활성화
        self.processing = False
        self.root.after(0, self.enable_buttons)
        self.root.after(0, self.update_stats, success_count, fail_count)
        
        # 완료 메시지
        self.root.after(0, lambda: messagebox.showinfo(
            "처리 완료",
            f"처리 완료!\n\n"
            f"✅ 성공: {success_count}개\n"
            f"❌ 실패: {fail_count}개\n\n"
            f"✨ 이미지 하단에 지번 표시됨\n"
            f"📝 파일명이 지번으로 변경됨\n"
            f"📋 처리 리포트: processing_report.json"
        ))
    
    def extract_gps(self, image_path):
        """GPS 좌표 추출"""
        try:
            with Image.open(image_path) as image:
                exif_data = image._getexif()
                
                if not exif_data:
                    return None, None
                
                gps_info = {}
                for tag, value in exif_data.items():
                    if TAGS.get(tag) == "GPSInfo":
                        for gps_tag in value:
                            gps_info[GPSTAGS.get(gps_tag, gps_tag)] = value[gps_tag]
                        break
                
                if not gps_info:
                    return None, None
                
                # GPS 좌표 변환
                lat = self.dms_to_decimal(gps_info['GPSLatitude'])
                if gps_info['GPSLatitudeRef'] == 'S':
                    lat = -lat
                
                lon = self.dms_to_decimal(gps_info['GPSLongitude'])
                if gps_info['GPSLongitudeRef'] == 'W':
                    lon = -lon
                
                return lat, lon
                
        except:
            return None, None
    
    def dms_to_decimal(self, dms):
        """DMS → Decimal 변환"""
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
        return degrees + (minutes / 60.0) + (seconds / 3600.0)
    
    def convert_to_address(self, lat, lon):
        """좌표 → 주소 변환"""
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
            f"&key={self.api_key}"
        )
        
        try:
            response = requests.get(url, timeout=30)
            result = response.json()
            
            if result['response']['status'] == 'OK':
                address_data = result['response']['result'][0]
                structure = address_data.get('structure', {})
                
                return {
                    'success': True,
                    'full_address': address_data.get('text', ''),
                    'sido': structure.get('level1', ''),
                    'sigungu': structure.get('level2', ''),
                    'eupmeondong': structure.get('level4L', ''),
                    'jibun': structure.get('level5', '')
                }
            else:
                return {'success': False}
        except:
            return {'success': False}
    
    def add_text_overlay(self, image_path, text):
        """
        이미지 하단에 텍스트 오버레이 추가
        ✨ v5 성공 코드: EXIF 간소화, 임시 파일 방식
        """
        temp_path = None
        try:
            # 1. 이미지 열기
            self.log_message(f"    ► 이미지 열기: {os.path.basename(image_path)}")
            img = Image.open(image_path)
            
            # 2. RGB 모드로 변환
            if img.mode != 'RGB':
                img = img.convert('RGB')
                self.log_message(f"    ✓ RGB 모드로 변환")
            
            # 3. 이미지 크기
            img_width, img_height = img.size
            self.log_message(f"    ✓ 이미지 크기: {img_width}x{img_height}")
            
            # 4. 오버레이 높이 (이미지 높이의 6%)
            overlay_height = max(int(img_height * 0.06), 150)
            
            # 5. 폰트 크기 계산
            font_size = max(int(overlay_height * 0.7), 80)
            self.log_message(f"    ✓ 오버레이 높이: {overlay_height}px, 폰트 크기: {font_size}px")
            
            # 6. 폰트 로드
            font = None
            font_paths = [
                "C:\\Windows\\Fonts\\malgun.ttf",
                "C:\\Windows\\Fonts\\gulim.ttc",
                "C:\\Windows\\Fonts\\batang.ttc",
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    self.log_message(f"    ✓ 폰트 로드 성공: {os.path.basename(font_path)}")
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
                self.log_message(f"    ⚠ 기본 폰트 사용")
            
            # 7. Drawing 객체 생성
            draw = ImageDraw.Draw(img)
            
            # 8. 흰색 배경 박스 그리기
            overlay_box = [0, img_height - overlay_height, img_width, img_height]
            draw.rectangle(overlay_box, fill=(255, 255, 255))
            self.log_message(f"    ✓ 배경 박스 그리기 완료")
            
            # 9. 텍스트 위치 계산 (중앙 정렬)
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except:
                text_width, text_height = draw.textsize(text, font=font)
            
            text_x = (img_width - text_width) // 2
            text_y = img_height - overlay_height + (overlay_height - text_height) // 2
            
            # 10. 텍스트 그리기
            draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))
            self.log_message(f"    ✓ 텍스트 그리기: '{text}' at ({text_x}, {text_y})")
            
            # 11. 임시 파일 생성
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', dir=os.path.dirname(image_path))
            os.close(temp_fd)
            
            # 12. 임시 파일에 저장 (EXIF 없이!)
            img.save(temp_path, format='JPEG', quality=95)
            self.log_message(f"    ✓ 임시 파일 저장 완료")
            
            # 13. 이미지 닫기
            img.close()
            
            # 14. 파일 교체 대기
            import time
            time.sleep(0.2)
            
            # 15. 원본 삭제
            if os.path.exists(image_path):
                os.remove(image_path)
            
            # 16. 임시 파일을 원본으로 이동
            shutil.move(temp_path, image_path)
            self.log_message(f"    ✓ 원본 파일 교체 완료!")
            
            return True
            
        except Exception as e:
            self.log_message(f"    ❌ 오버레이 오류: {e}")
            import traceback
            self.log_message(f"    📋 상세 오류:\n{traceback.format_exc()}")
            
            # 임시 파일 정리
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return False
    
    def generate_filename(self, address_info, original_filename):
        """파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _, ext = os.path.splitext(original_filename)
        
        # 주소 정보 정리
        sido = self.clean_text(address_info.get('sido', ''))
        sigungu = self.clean_text(address_info.get('sigungu', ''))
        eupmeondong = self.clean_text(address_info.get('eupmeondong', ''))
        jibun = self.clean_text(address_info.get('jibun', ''))
        
        # 파일명 생성
        if all([sido, sigungu, eupmeondong, jibun]):
            return f"{sido}_{sigungu}_{eupmeondong}_{jibun}_{timestamp}{ext}"
        elif all([sigungu, eupmeondong, jibun]):
            return f"{sigungu}_{eupmeondong}_{jibun}_{timestamp}{ext}"
        elif all([sigungu, jibun]):
            return f"{sigungu}_{jibun}_{timestamp}{ext}"
        else:
            return f"GPS_{timestamp}{ext}"
    
    def clean_text(self, text):
        """파일명용 텍스트 정리"""
        if not text:
            return ""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            text = text.replace(char, '')
        text = text.replace(' ', '_')
        while '__' in text:
            text = text.replace('__', '_')
        return text.strip('_')
    
    def save_report_simple(self, results):
        """처리 리포트 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"processing_report_{timestamp}.json"
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'version': 'v6',
                'mode': 'overlay_and_rename',
                'description': '이미지 하단에 지번 표시 + 파일명 자동 변경',
                'total': len(results),
                'success': len([r for r in results if r['status'] == 'SUCCESS']),
                'fail': len([r for r in results if r['status'] != 'SUCCESS']),
                'results': results
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"📄 리포트 저장: {report_file}")
            
        except Exception as e:
            self.log_message(f"⚠️ 리포트 저장 실패: {e}")
    
    def log_message(self, message):
        """로그 메시지 출력"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, current, total, text):
        """진행률 업데이트"""
        percentage = int((current / total) * 100)
        self.progress_bar['value'] = percentage
        self.progress_label.config(text=f"{text} ({current}/{total}) - {percentage}%")
        self.root.update_idletasks()
    
    def update_stats(self, success=0, fail=0):
        """통계 업데이트"""
        total = len(self.image_files)
        self.stats_label.config(
            text=f"통계: 선택 {total}개 | 성공 {success}개 | 실패 {fail}개"
        )
    
    def enable_buttons(self):
        """버튼 활성화"""
        self.select_button.config(state=tk.NORMAL)
        self.process_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
    
    def clear_all(self):
        """초기화"""
        if self.processing:
            messagebox.showwarning("경고", "처리 중에는 초기화할 수 없습니다!")
            return
        
        self.image_files = []
        self.file_listbox.delete(0, tk.END)
        self.log_text.delete(1.0, tk.END)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="대기 중...")
        self.process_button.config(state=tk.DISABLED)
        self.update_stats()
        self.log_message("🔄 초기화 완료")

def main():
    """메인 실행 함수"""
    root = tk.Tk()
    app = DroneImageProcessor(root)
    root.mainloop()

if __name__ == "__main__":
    main()