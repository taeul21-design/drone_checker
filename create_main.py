code = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
'''

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("main.py 생성 완료!")
