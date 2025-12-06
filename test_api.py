import requests

# 발급받은 API 키 입력
api_key =  "D7DAD017-CFFF-3690-9B60-5612730DF5D7"
# 테스트 좌표 (서울 시청)
lat = 37.5665
lon = 126.9780

url = f"https://api.vworld.kr/req/address?service=address&request=getAddress&version=2.0&crs=epsg:4326&point={lon},{lat}&format=json&type=both&key={api_key}"

print("🔍 API 테스트 중...")
response = requests.get(url)
data = response.json()

if data['response']['status'] == 'OK':
    print("✅ API 키 정상 작동!")
    print(f"주소: {data['response']['result'][0]['text']}")
else:
    print("❌ API 키 오류!")
    print(data)
