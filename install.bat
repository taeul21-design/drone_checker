@echo off
echo ================================================
echo 드론 이미지 GPS 지번 변환 프로그램 설치
echo ================================================

echo.
echo [1/4] Python 버전 확인...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았습니다!
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit
)

echo.
echo [2/4] 필수 라이브러리 설치...
pip install pillow requests

echo.
echo [3/4] 설정 파일 확인...
if not exist config.json (
    echo ❌ config.json 파일이 없습니다!
    echo config.json 파일을 생성해주세요.
    pause
    exit
)

echo.
echo [4/4] 프로그램 실행 테스트...
python main.py

echo.
echo ================================================
echo ✅ 설치 완료!
echo ================================================
pause