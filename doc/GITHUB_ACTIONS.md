# GitHub Actions 설정 가이드

## 개요

이 프로젝트는 GitHub Actions를 통해 자동으로 주식 크롤링 및 감정분석을 수행합니다.

## 🔧 GitHub Secrets 설정

GitHub Actions가 작동하려면 다음 Secrets를 설정해야 합니다:

### 1. GitHub 저장소 설정

1. GitHub 저장소로 이동
2. `Settings` > `Secrets and variables` > `Actions` 클릭
3. `New repository secret` 버튼 클릭

### 2. 필수 Secrets 추가

| Secret Name   | 설명                         | 예시 값                  |
| ------------- | ---------------------------- | ------------------------ |
| `DB_HOST`     | 외부 데이터베이스 호스트     | `your-database-host.com` |
| `DB_PORT`     | 데이터베이스 포트 (선택사항) | `3306`                   |
| `DB_USER`     | 데이터베이스 사용자명        | `crawler`                |
| `DB_PASSWORD` | 데이터베이스 비밀번호        | `your_strong_password`   |
| `DB_NAME`     | 데이터베이스명 (선택사항)    | `stock_crawling`         |

### 3. Secret 추가 방법

각 Secret을 다음과 같이 추가하세요:

```
Name: DB_HOST
Value: your-database-host.com
```

```
Name: DB_USER
Value: crawler
```

```
Name: DB_PASSWORD
Value: your_strong_password_here
```

## ⚙️ 워크플로우 권한 설정

커밋 및 푸시 작업이 필요한 워크플로우의 경우, **write 권한**이 필요합니다.

1. 저장소의 `Settings` > `Actions` > `General`로 이동
2. `Workflow permissions` 섹션에서  
   - `Read and write permissions`를 선택
3. 변경사항 저장


## 🚀 워크플로우 실행 방법

### 1. 자동 실행 (스케줄)

- **매 10분마다**: 지속적인 데이터 수집 및 실시간 분석

### 2. 수동 실행

1. GitHub 저장소의 `Actions` 탭으로 이동
2. `Stock Crawler and Analysis` 워크플로우 선택
3. `Run workflow` 버튼 클릭
4. 선택적으로 매개변수 설정:
   - **종목코드**: 크롤링할 종목코드 (기본값: 139480)
   - **최대 페이지**: 크롤링할 페이지 수 (기본값: 10)

### 3. 코드 푸시 시 자동 실행

- `main` 브랜치에 Python 파일이나 설정 파일을 푸시하면 자동으로 테스트 실행

## 📊 실행 결과 확인

### 1. 워크플로우 로그

- `Actions` 탭에서 실행 중인/완료된 워크플로우 확인
- 각 단계별 상세 로그 확인 가능

### 2. 아티팩트 다운로드

- 실행 완료 후 로그 파일을 아티팩트로 다운로드 가능
- 7일간 보관

### 3. 실행 요약

- 각 워크플로우 실행 후 요약 리포트 자동 생성
- 성공/실패 상태, 실행 시간, 주요 로그 정보 포함

## 🛠️ 문제 해결

### 일반적인 문제들

#### 1. Secrets 설정 오류

```
Error: Missing required secret: MYSQL_PASSWORD
```

**해결**: GitHub Secrets에 `MYSQL_PASSWORD` 추가

#### 2. 데이터베이스 연결 실패

```
Error: Database connection failed
```

**해결**:

- Secrets 값이 올바른지 확인
- MySQL 서비스 상태 확인

#### 3. 크롤링 실패

```
Error: Failed to crawl posts
```

**해결**:

- 네트워크 연결 상태 확인
- 대상 웹사이트 접근 가능 여부 확인
- User-Agent 설정 확인

### 디버깅 방법

1. **워크플로우 로그 확인**

   - Actions 탭에서 실패한 단계의 상세 로그 확인

2. **로컬 테스트**

   ```bash
   # 로컬에서 설정 확인
   python config.py

   # 데이터베이스 연결 테스트
   python -c "from database import test_database_connection; test_database_connection()"

   # 크롤러 실행
   python main.py
   ```

3. **환경변수 확인**
   - `.env` 파일 설정이 올바른지 확인
   - GitHub Secrets 설정이 올바른지 확인

## 📝 워크플로우 수정

워크플로우 설정을 수정하려면:

1. `.github/workflows/crawler.yml` 파일 편집
2. 스케줄, 환경변수, 실행 단계 등 수정 가능
3. 변경사항을 `main` 브랜치에 푸시

## 🔒 보안 고려사항

1. **Secrets 관리**

   - 강력한 비밀번호 사용
   - 정기적인 비밀번호 변경
   - 불필요한 권한 부여 금지

2. **크롤링 윤리**

   - 적절한 지연시간 설정 (기본 1초)
   - 과도한 요청 방지
   - 대상 사이트의 robots.txt 준수

3. **데이터 보안**
   - 민감한 데이터 로깅 금지
   - 아티팩트 보관 기간 제한 (7일)
   - 공개 저장소에서 개인정보 노출 방지

### ⚠️ 주의사항 (매 10분 실행)

**자주 실행되는 워크플로우를 사용할 때 고려사항:**

1. **GitHub Actions 사용량**:

   - 무료 계정: 월 2,000분 제한
   - 매 10분 실행 시 하루 144회, 월 약 4,320회 실행
   - 각 실행이 5분 소요 시 월 21,600분 사용 (유료 플랜 필요)

2. **서버 부하 방지**:

   - `CRAWLING_DELAY` 설정으로 크롤링 간격 조절 (기본 1초)
   - 너무 자주 실행하면 대상 웹사이트에서 차단될 수 있음

3. **모니터링 및 조절**:

   - Actions 탭에서 실행 현황 모니터링
   - 필요에 따라 스케줄 조정 (`*/30 * * * *`는 30분마다)
   - 실패가 자주 발생하면 간격을 늘리는 것을 권장

4. **비용 최적화**:
   - 주요 거래 시간대에만 실행하도록 조건 추가 가능
   - 주말이나 휴일 제외 설정 가능
