# Docker Compose 설정

이 폴더는 주식 크롤링 프로젝트의 Docker 환경 설정을 포함합니다.

## 파일 구성

- `docker-compose.yml`: MariaDB 서비스 정의
- `init.sql`: 데이터베이스 초기화 스크립트 (테이블 생성)
- `.env.example`: 환경 변수 설정 예시 파일
- `.env`: 실제 환경 변수 설정 파일 (gitignore 대상)

## 설정 방법

### 1. 환경변수 파일 생성

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env
```

### 2. 비밀번호 설정

`.env` 파일을 편집하여 다음 값들을 실제 비밀번호로 변경하세요:

- `MYSQL_ROOT_PASSWORD`: MariaDB root 사용자 비밀번호
- `MYSQL_PASSWORD`: 애플리케이션 사용자(crawler) 비밀번호

### 3. 서비스 구성

#### MariaDB

- **포트**: 3306
- **데이터베이스**: stock_crawling
- **사용자**: crawler
- **비밀번호**: `.env` 파일에서 설정한 값

## 실행 방법

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 상태 확인
docker-compose ps

# 서비스 중지
docker-compose down

# 데이터까지 삭제
docker-compose down -v
```

## 데이터베이스 스키마

`init.sql` 파일에는 다음 테이블들이 정의되어 있습니다:

1. **stock_posts**: 게시글 기본 정보
2. **post_analysis**: 게시글 분석 결과
3. **daily_stock_summary**: 일별 종목 요약

## 주의사항

- 처음 실행 시 데이터베이스 초기화에 시간이 걸릴 수 있습니다
- 포트 3306, 8080이 사용 중이지 않은지 확인하세요
- 데이터는 Docker 볼륨에 저장되어 컨테이너 재시작 후에도 유지됩니다
