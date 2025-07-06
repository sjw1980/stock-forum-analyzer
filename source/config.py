"""
설정 파일 - 환경변수를 로드하고 설정을 관리합니다.
"""
import os
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv()

# 데이터베이스 설정
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'crawler'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_crawling'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4')
}

# 크롤링 설정
CRAWLING_CONFIG = {
    'delay': float(os.getenv('CRAWLING_DELAY', 1.0)),
    'max_pages': int(os.getenv('MAX_PAGES', 10)),
    'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
}

# 로깅 설정
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file': os.getenv('LOG_FILE', 'crawler.log')
}

# 로거 설정
def setup_logging():
    """로깅 설정을 초기화합니다."""
    log_level = getattr(logging, LOG_CONFIG['level'].upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_CONFIG['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# 설정 검증
def validate_config():
    """필수 설정값들이 올바르게 설정되었는지 검증합니다."""
    required_settings = {
        'DB_PASSWORD': DB_CONFIG['password'],
        'DB_HOST': DB_CONFIG['host'],
        'DB_USER': DB_CONFIG['user'],
        'DB_NAME': DB_CONFIG['database']
    }
    
    missing_settings = []
    for key, value in required_settings.items():
        if not value:
            missing_settings.append(key)
    
    if missing_settings:
        raise ValueError(f"다음 설정값들이 누락되었습니다: {', '.join(missing_settings)}")
    
    return True

if __name__ == "__main__":
    # 설정 검증 테스트
    try:
        validate_config()
        print("✅ 모든 설정이 올바르게 구성되었습니다.")
        print(f"DB Host: {DB_CONFIG['host']}")
        print(f"DB User: {DB_CONFIG['user']}")
        print(f"DB Name: {DB_CONFIG['database']}")
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
