# 주식 크롤링 & 감정분석 프로젝트

## 프로젝트 개요

네이버 금융 종목토론실의 게시글을 수집하고, 자연어 처리를 통해 투자 심리를 분석하는 프로젝트입니다.

## 주요 기능

- 🕷️ 네이버 금융 종목토론실 크롤링
- 📊 게시글 감정 분석 (긍정/부정/중립)
- 📈 투자 전망 분석 (상승/하락/중립)
- 🎯 키워드 추출 및 분석
- 🗄️ MariaDB/MySQL 데이터베이스 저장
- 📋 분석 리포트 생성

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/sjw1980/stock-forum-analyzer.git
cd stock-forum-analyzer
```

### 2. Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example ./../.env

# .env 파일을 편집하여 실제 DB 정보 입력
# DB_PASSWORD와 MYSQL_ROOT_PASSWORD를 실제 비밀번호로 변경하세요
```

### 4. 데이터베이스 설정 (Docker 사용)

```bash
cd docker-compose

# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일을 편집하여 실제 DB 비밀번호 설정
# MYSQL_ROOT_PASSWORD와 MYSQL_PASSWORD를 원하는 비밀번호로 변경

# MariaDB 컨테이너 시작
docker-compose up -d
```

### 5. 설정 검증

```bash
# 설정이 올바른지 확인
python config.py
```

## 실행 방법

### 크롤링 및 분석 실행

```bash
# 메인 크롤링 및 분석
python main.py

# 분석 리포트 조회
python analysis_report.py

# 데이터베이스 연결 테스트
python -c "from database import test_database_connection; test_database_connection()"
```

## 환경변수 설정

`.env` 파일에서 다음 설정을 구성할 수 있습니다:

### 데이터베이스 설정

- `DB_HOST`: 데이터베이스 호스트 (기본값: localhost)
- `DB_PORT`: 데이터베이스 포트 (기본값: 3306)
- `DB_USER`: 데이터베이스 사용자명 (기본값: crawler)
- `DB_PASSWORD`: 데이터베이스 비밀번호 (필수 설정)
- `DB_NAME`: 데이터베이스명 (기본값: stock_crawling)

### 크롤링 설정

- `CRAWLING_DELAY`: 크롤링 지연시간 (기본값: 1.0초)
- `MAX_PAGES`: 최대 크롤링 페이지 수 (기본값: 10)
- `USER_AGENT`: HTTP User-Agent

### 로깅 설정

- `LOG_LEVEL`: 로그 레벨 (기본값: INFO)
- `LOG_FILE`: 로그 파일명 (기본값: crawler.log)

## 데이터베이스 스키마

### 1. stock_posts (게시글 기본 정보)

- id: 기본키 (자동증가)
- stock_code: 종목코드
- date: 게시일
- title: 제목
- author: 작성자
- views: 조회수
- likes: 공감수
- dislikes: 비공감수
- link: 게시글 링크
- content: 게시글 본문
- is_analyzed: 분석 완료 여부
- created_at: 생성시간

### 2. post_analysis (게시글 분석 결과)

- id: 기본키
- post_id: 게시글 ID (외래키)
- sentiment_score: 감정 점수 (-1.0 ~ 1.0)
- sentiment_label: 감정 레이블 (positive/negative/neutral)
- confidence_score: 신뢰도 점수 (0.0 ~ 1.0)
- keywords: 주요 키워드 (JSON 배열)
- bullish_bearish: 상승/하락 전망
- risk_level: 위험도 (low/medium/high)
- analysis_model: 분석 모델명
- analysis_version: 모델 버전

### 3. daily_stock_summary (일별 종목 요약)

- 일별 감정 분석 요약 데이터

## 분석 방법

### 감정 분석

- 키워드 기반 감정 분석
- 긍정 키워드: 상승, 급등, 호재, 매수, 추천 등
- 부정 키워드: 하락, 급락, 악재, 매도, 손실 등

### 투자 전망 분석

- 상승 전망: 상승, 급등, 매수, 호재 관련 키워드
- 하락 전망: 하락, 급락, 매도, 악재 관련 키워드

### 위험도 분석

- High: 위험, 손실, 급락 등 키워드 3개 이상
- Medium: 위험 관련 키워드 1-2개
- Low: 위험 관련 키워드 없음

## 사용 예시

```python
# 특정 종목 분석 리포트 보기
from analysis_report import print_analysis_report
print_analysis_report("139480", days=7)

# 키워드 분석
from analysis_report import get_keyword_analysis
keywords = get_keyword_analysis("139480", days=7)
print(keywords.head(10))
```

## 종료 방법

```bash
cd docker-compose

# 서비스만 종료 (데이터 유지)
docker-compose down

# 데이터까지 삭제
docker-compose down -v
```

## 주의사항

- 크롤링 시 서버 부하를 줄이기 위해 딜레이가 설정되어 있습니다
- 대량의 데이터 분석 시 시간이 오래 걸릴 수 있습니다
- 네이버 금융의 구조 변경 시 크롤링 코드 수정이 필요할 수 있습니다

## 🤖 GitHub Actions 자동화

이 프로젝트는 GitHub Actions를 통해 자동으로 크롤링 및 분석을 수행할 수 있습니다.

### 자동 실행 스케줄

- **매 10분마다**: 실시간 데이터 수집 및 감정 분석

### 수동 실행

GitHub 저장소의 Actions 탭에서 언제든지 수동으로 실행 가능합니다.

### 설정 방법

1. **GitHub Secrets 설정** (필수):

   - `DB_HOST`: 외부 데이터베이스 호스트
   - `DB_USER`: 데이터베이스 사용자명
   - `DB_PASSWORD`: 데이터베이스 비밀번호
   - `DB_PORT`: 데이터베이스 포트 (선택사항)
   - `DB_NAME`: 데이터베이스명 (선택사항)

2. **워크플로우 활성화**:
   - 저장소를 포크하거나 클론 후 GitHub에 푸시
   - Actions 탭에서 워크플로우 활성화

자세한 설정 방법은 [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)를 참조하세요.
