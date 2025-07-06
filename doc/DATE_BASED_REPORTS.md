# 날짜 기반 리포트 사용법 (GUI 없이 파일 저장)

이제 주말에도 특정 날짜를 지정해서 리포트를 테스트할 수 있습니다.
**모든 차트는 GUI로 표시되지 않고 PNG 파일로 저장됩니다.**

## 변경사항

### 1. `generate_pre_market_report()` 함수
- **매개변수 추가**: `target_date` (선택적)
- **사용법**: 
  ```python
  # 오늘 기준 (기존 방식)
  analyzer.generate_pre_market_report()
  
  # 특정 날짜 기준 (새로운 방식)
  analyzer.generate_pre_market_report(target_date="2025-07-04")
  ```

### 2. `generate_post_market_report()` 함수  
- **매개변수 추가**: `target_date` (선택적)
- **사용법**:
  ```python
  # 오늘 기준 (기존 방식)
  analyzer.generate_post_market_report()
  
  # 특정 날짜 기준 (새로운 방식) 
  analyzer.generate_post_market_report(target_date="2025-07-04")
  ```

### 3. 시각화 개선
- **GUI 없음**: `plt.show()` 제거, `matplotlib.use('Agg')` 설정
- **파일 저장**: 모든 차트가 PNG 파일로 자동 저장
- **저장 알림**: 파일 저장 시 경로 출력

## 테스트 방법

### 1. 직접 Python 코드로 테스트
```python
from pattern_analyzer import PatternAnalyzer

analyzer = PatternAnalyzer()

# 2025년 7월 4일 금요일 데이터로 테스트
test_date = "2025-07-04"

# 장시작 전 리포트
results = analyzer.generate_pre_market_report(target_date=test_date)

# 장마감 후 리포트  
results = analyzer.generate_post_market_report(target_date=test_date)
```

### 2. 스케줄러를 통한 테스트
```bash
# 특정 날짜 테스트
python scheduler.py test-date 2025-07-04

# 전체 테스트 (기존 방식)
python scheduler.py test

# 스케줄러 실행 (기존 방식)
python scheduler.py schedule
```

### 3. 테스트 스크립트 실행
```bash
# 간단한 테스트
python simple_test.py

# 전체 리포트 테스트
python test_monthly_report.py
```

## 장점

1. **주말 테스트 가능**: 장이 열리지 않는 주말에도 과거 평일 데이터로 테스트
2. **특정 날짜 분석**: 원하는 날짜의 시장 데이터 분석 가능
3. **역사적 분석**: 과거 특정 일자의 패턴 분석 가능
4. **유연한 테스트**: 개발 및 디버깅 시 다양한 시나리오 테스트
5. **GUI 없음**: 서버 환경에서도 실행 가능, 파일로만 저장
6. **자동 저장**: 모든 차트가 PNG 파일로 자동 저장

## 생성되는 파일들

- `pattern_analysis_all_YYYYMMDD.png` - 기본 패턴 분석
- `pre_market_report_YYYYMMDD.png` - 장시작 전 리포트  
- `post_market_report_YYYYMMDD.png` - 장마감 후 리포트
- `weekly_report_YYYYMMDD.png` - 주간 리포트
- `monthly_report_YYYYMMDD.png` - 월간 리포트

## 사용 예시

```python
# 최근 금요일 데이터 분석
analyzer.generate_post_market_report(target_date="2025-07-04")

# 월요일 장시작 전 분석 (전주 금요일 기준)
analyzer.generate_pre_market_report(target_date="2025-07-07")

# 월간 리포트 (기존과 동일)
analyzer.generate_monthly_report()
analyzer.generate_monthly_report(target_date="2024-11")  # 특정 월

# 주간 리포트 (기존과 동일)
analyzer.generate_weekly_report()
```

이제 언제든지 원하는 날짜를 지정해서 리포트를 생성하고 테스트할 수 있습니다!

**📁 모든 시각화 결과는 PNG 파일로 저장되며, GUI 창은 표시되지 않습니다.**
**🖥️ 서버 환경이나 GUI가 없는 환경에서도 정상 작동합니다.**
