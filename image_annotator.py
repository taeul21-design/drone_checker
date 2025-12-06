#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
이미지 텍스트 오버레이 모듈
드론 이미지에 지번 정보를 반투명 배경과 함께 표시
"""

from PIL import Image, ImageDraw, ImageFont
import os

class ImageAnnotator:
    """이미지에 텍스트를 오버레이하는 클래스"""
    
    def __init__(self, config=None):
        """
        초기화
        
        Args:
            config (dict): 설정 딕셔너리
        """
        self.config = config or {}
        
        # 기본 설정 (모두 Space로 들여쓰기!)
        self.overlay_height = 110
        self.font_size = 72
        self.padding = 25
        
        # 색상 설정
        self.bg_color = (255, 255, 255)
        self.text_color = (0, 0, 0)
        self.opacity = 0.8
        
        # 한글 폰트 경로
        self.font_path = self._find_korean_font()
        
    def _find_korean_font(self):
        """시스템에서 한글 폰트 찾기"""
        font_paths = [
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/gulim.ttc',
            'C:/Windows/Fonts/batang.ttc',
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        
        return None
    
    def add_text_overlay(self, image_path, text, output_path=None):
        """
        이미지에 텍스트 오버레이 추가
        
        Args:
            image_path (str): 원본 이미지 경로
            text (str): 표시할 텍스트
            output_path (str): 저장할 경로 (None이면 원본 경로 사용)
        
        Returns:
            str: 저장된 파일 경로
        """
        if output_path is None:
            output_path = image_path
        
        img = Image.open(image_path).convert('RGBA')
        width, height = img.size
        
        overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        overlay_y_start = height - self.overlay_height
        alpha = int(255 * self.opacity)
        bg_color_with_alpha = self.bg_color + (alpha,)
        
        draw.rectangle(
            [(0, overlay_y_start), (width, height)],
            fill=bg_color_with_alpha
        )
        
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, self.font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (width - text_width) // 2
        text_y = overlay_y_start + (self.overlay_height - text_height) // 2
        
        draw.text(
            (text_x, text_y),
            text,
            fill=self.text_color,
            font=font
        )
        
        combined = Image.alpha_composite(img, overlay)
        combined_rgb = combined.convert('RGB')
        combined_rgb.save(output_path, 'JPEG', quality=95)
        
        return output_path
    
    def format_address_text(self, address_info, include_jimok=False, jimok=''):
        """
        주소 정보를 표시 텍스트로 포맷
        
        Args:
            address_info (dict): 주소 정보 딕셔너리
            include_jimok (bool): 지목 포함 여부
            jimok (str): 지목 (예: '답', '전', '임야')
        
        Returns:
            str: 포맷된 텍스트
        """
        sigungu = address_info.get('sigungu', '')
        eupmeondong = address_info.get('eupmeondong', '')
        jibun = address_info.get('jibun', '')
        
        parts = []
        
        if sigungu:
            parts.append(sigungu)
        
        if eupmeondong:
            parts.append(eupmeondong)
        
        if jibun:
            parts.append(jibun)
        
        if include_jimok and jimok:
            parts.append(jimok)
        
        text = ' '.join(parts)
        
        return text


def test_annotator():
    """테스트 함수"""
    print("=" * 70)
    print("이미지 텍스트 오버레이 테스트")
    print("=" * 70)
    
    test_image = input("테스트 이미지 경로 입력: ").strip().strip('"')
    
    if not os.path.exists(test_image):
        print(f"❌ 파일이 없습니다: {test_image}")
        return
    
    annotator = ImageAnnotator()
    
    test_texts = [
        "경주시 현곡면 804-9",
        "경주시 현곡면 804-9 답",
        "화성시 향남읍 123-45 전",
    ]
    
    print(f"\n✅ 원본 이미지: {test_image}")
    print(f"✅ 폰트: {annotator.font_path}")
    print()
    
    for i, text in enumerate(test_texts, 1):
        output_path = test_image.replace('.', f'_test{i}.')
        
        print(f"🔄 테스트 {i}: '{text}'")
        result = annotator.add_text_overlay(test_image, text, output_path)
        print(f"✅ 저장됨: {result}")
        print()
    
    print("=" * 70)
    print("✅ 테스트 완료!")
    print("=" * 70)


if __name__ == "__main__":
    test_annotator()
