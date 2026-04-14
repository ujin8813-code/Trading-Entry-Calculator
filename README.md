# 🎖️ 투자 사령부 대시보드

사령관의 매수 원칙 기반 자동 종목 스캐너 & 타점 계산기

## 배포 방법 (Streamlit Cloud)

### 1단계: GitHub 레포 생성

1. [github.com/new](https://github.com/new) 에서 새 레포 생성
1. 레포 이름: `investment-dashboard` (원하는 이름)
1. **Public** 선택 (Streamlit Cloud 무료 플랜은 Public만 지원)

### 2단계: 파일 업로드

이 폴더의 파일 전부를 레포에 업로드:

```
├── app.py                    # 메인 앱
├── requirements.txt          # 의존성
├── .streamlit/
│   └── config.toml          # 테마 설정
└── README.md
```

GitHub 웹에서 업로드하려면:

- 레포 페이지 → **Add file** → **Upload files** → 드래그앤드롭

### 3단계: Streamlit Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) 접속
1. GitHub 계정으로 로그인
1. **New app** 클릭
1. Repository: 방금 만든 레포 선택
1. Branch: `main`
1. Main file path: `app.py`
1. **Deploy!** 클릭

### 완료!

- 배포 URL이 생성됨 (예: `https://your-app.streamlit.app`)
- 모바일 브라우저에서 이 URL 접속
- **홈 화면에 추가**하면 앱처럼 사용 가능!

## 기능

- 🔍 자동 스캐너 (가치 + 기술 판정)
- 🎯 타점 자동 계산
- 📈 캔들차트 + RSI
- 💰 매수 이력 & 수익률
- 🏠 청약 자금 목표 추적
