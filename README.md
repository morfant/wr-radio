# WR-Radio

## 설정 방법

### 1. 첫 실행
```bash
python3 wr-radio.py
```
첫 실행 시 `config.json` 파일이 자동 생성됩니다.

### 2. 스테이션 추가/변경
```bash
nano ~/wr-radio/config.json
```
```json
{
  "stations": [
    {
      "name": "내가 좋아하는 라디오",
      "url": "http://stream-url.mp3",
      "location": "Seoul, Korea",
      "lat": 37.5665,
      "lon": 126.9780,
      "color": [255, 100, 100]
    }
  ]
}
```

### 3. 날씨 기능 (선택)
1. https://openweathermap.org/appid 에서 무료 API 키 발급
2. `config.json`에 키 입력:
```json
   {
     "openweather_api_key": "여기에_키_입력"
   }
```
