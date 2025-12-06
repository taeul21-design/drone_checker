"""
파일 관리 모듈
이미지 파일을 지번이 포함된 파일명으로 복사 및 저장합니다.
"""

import os
import shutil
from pathlib import Path
from typing import Dict
import re


class FileManager:
    """파일 복사 및 이름 변경을 관리하는 클래스"""
    
    def __init__(self, output_folder: str, backup_original: bool = True):
        """
        Args:
            output_folder: 출력 폴더 경로
            backup_original: 원본 파일 백업 여부
        """
        self.output_folder = Path(output_folder)
        self.backup_original = backup_original
        
        # 출력 폴더 생성
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        if backup_original:
            self.backup_folder = self.output_folder / 'original_backup'
            self.backup_folder.mkdir(parents=True, exist_ok=True)
    
    def sanitize_filename(self, text: str) -> str:
        """
        파일명에 사용할 수 없는 문자 제거
        
        Args:
            text: 원본 텍스트
            
        Returns:
            정제된 텍스트
        """
        # 파일명에 사용할 수 없는 문자 제거
        text = re.sub(r'[\\/*?:"<>|]', '', text)
        # 공백을 언더스코어로 변경
        text = text.replace(' ', '_')
        # 연속된 언더스코어를 하나로
        text = re.sub(r'_+', '_', text)
        return text
    
    def generate_filename(self, jibun_info: Dict, date: str, time: str, 
                         original_ext: str = '.jpg') -> str:
        """
        지번 정보를 기반으로 파일명 생성
        
        Args:
            jibun_info: 지번 정보 딕셔너리
            date: 날짜 (YYYYMMDD)
            time: 시간 (HHMMSS)
            original_ext: 원본 파일 확장자
            
        Returns:
            생성된 파일명
        """
        sido = self.sanitize_filename(jibun_info.get('sido', '알수없음'))
        sigungu = self.sanitize_filename(jibun_info.get('sigungu', ''))
        emd = self.sanitize_filename(jibun_info.get('emd', ''))
        jibun = self.sanitize_filename(jibun_info.get('jibun', ''))
        
        # 리가 있는 경우 추가
        ri = jibun_info.get('ri', '')
        if ri:
            ri = self.sanitize_filename(ri)
            location = f"{emd}_{ri}"
        else:
            location = emd
        
        # 파일명 형식: 시도_시군구_읍면동_지번_날짜_시간.jpg
        filename = f"{sido}_{sigungu}_{location}_{jibun}_{date}_{time}{original_ext}"
        
        # 파일명 길이 제한 (255자)
        if len(filename) > 255:
            # 중간 부분 축약
            filename = f"{sido}_{sigungu[:10]}_{jibun[:20]}_{date}_{time}{original_ext}"
        
        return filename
    
    def copy_and_rename(self, source_path: str, jibun_info: Dict, 
                       gps_data: Dict) -> str:
        """
        파일을 복사하고 지번이 포함된 파일명으로 변경
        
        Args:
            source_path: 원본 파일 경로
            jibun_info: 지번 정보
            gps_data: GPS 정보 (날짜/시간 포함)
            
        Returns:
            새로운 파일 경로
        """
        try:
            source = Path(source_path)
            
            # 파일 확장자 추출
            ext = source.suffix.lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                ext = '.jpg'
            
            # 새 파일명 생성
            new_filename = self.generate_filename(
                jibun_info,
                gps_data['date'],
                gps_data['time'],
                ext
            )
            
            new_path = self.output_folder / new_filename
            
            # 파일명 중복 처리
            counter = 1
            while new_path.exists():
                name_without_ext = new_filename.rsplit('.', 1)[0]
                new_filename = f"{name_without_ext}_{counter}{ext}"
                new_path = self.output_folder / new_filename
                counter += 1
            
            # 파일 복사
            shutil.copy2(source, new_path)
            print(f"✅ 파일 저장 완료: {new_path.name}")
            
            # 원본 백업 (옵션)
            if self.backup_original:
                backup_path = self.backup_folder / source.name
                if not backup_path.exists():
                    shutil.copy2(source, backup_path)
            
            return str(new_path)
            
        except Exception as e:
            print(f"❌ 파일 복사 오류: {e}")
            return None
    
    def create_report(self, processed_files: list, output_file: str = 'report.csv'):
        """
        처리 결과 리포트 생성 (CSV)
        
        Args:
            processed_files: 처리된 파일 정보 리스트
            output_file: 출력 파일명
        """
        try:
            import csv
            
            report_path = self.output_folder / output_file
            
            with open(report_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 헤더
                writer.writerow([
                    '원본파일명', '새파일명', '위도', '경도', 
                    '시도', '시군구', '읍면동', '지번', 
                    '전체주소', '촬영일시', '처리상태'
                ])
                
                # 데이터
                for item in processed_files:
                    writer.writerow([
                        item.get('original_name', ''),
                        item.get('new_name', ''),
                        item.get('latitude', ''),
                        item.get('longitude', ''),
                        item.get('sido', ''),
                        item.get('sigungu', ''),
                        item.get('emd', ''),
                        item.get('jibun', ''),
                        item.get('full_address', ''),
                        item.get('datetime', ''),
                        item.get('status', '')
                    ])
            
            print(f"\n📄 리포트 생성 완료: {report_path}")
            
        except Exception as e:
            print(f"❌ 리포트 생성 오류: {e}")


# 테스트 코드
if __name__ == "__main__":
    fm = FileManager('./processed_images', backup_original=True)
    
    test_jibun = {
        'sido': '경기도',
        'sigungu': '화성시',
        'emd': '향남읍',
        'jibun': '123-45'
    }
    
    test_gps = {
        'date': '20250110',
        'time': '143522'
    }
    
    filename = fm.generate_filename(test_jibun, test_gps['date'], test_gps['time'])
    print(f"생성된 파일명: {filename}")
