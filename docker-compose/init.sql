-- 게시글 기본 정보 테이블
CREATE TABLE IF NOT EXISTS stock_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    date DATETIME,
    title TEXT,
    author VARCHAR(100),
    views VARCHAR(20),
    likes VARCHAR(20),
    dislikes VARCHAR(20),
    link TEXT,
    content TEXT,  -- 게시글 본문 내용
    is_analyzed BOOLEAN DEFAULT FALSE,  -- 분석 완료 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_code (stock_code),
    INDEX idx_date (date),
    INDEX idx_author (author),
    INDEX idx_is_analyzed (is_analyzed),
    UNIQUE KEY unique_post (stock_code, date, author, title(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 게시글 분석 결과 테이블
CREATE TABLE IF NOT EXISTS post_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    sentiment_score DECIMAL(5,4),  -- 감정 점수 (-1.0 ~ 1.0)
    sentiment_label VARCHAR(20),   -- 감정 레이블 (positive, negative, neutral)
    confidence_score DECIMAL(5,4), -- 신뢰도 점수 (0.0 ~ 1.0)
    keywords JSON,                 -- 주요 키워드 (JSON 배열)
    topics JSON,                   -- 토픽 분류 결과 (JSON 배열)
    bullish_bearish VARCHAR(20),   -- 상승/하락 전망 (bullish, bearish, neutral)
    risk_level VARCHAR(20),        -- 위험도 (low, medium, high)
    summary TEXT,                  -- 요약 내용
    analysis_model VARCHAR(50),    -- 사용된 분석 모델
    analysis_version VARCHAR(20),  -- 분석 모델 버전
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES stock_posts(id) ON DELETE CASCADE,
    INDEX idx_post_id (post_id),
    INDEX idx_sentiment_label (sentiment_label),
    INDEX idx_bullish_bearish (bullish_bearish),
    INDEX idx_analysis_model (analysis_model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 일별 종목 분석 요약 테이블
CREATE TABLE IF NOT EXISTS daily_stock_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    date DATETIME NOT NULL,
    total_posts INT DEFAULT 0,
    positive_posts INT DEFAULT 0,
    negative_posts INT DEFAULT 0,
    neutral_posts INT DEFAULT 0,
    avg_sentiment_score DECIMAL(5,4),
    bullish_ratio DECIMAL(5,4),   -- 상승 전망 비율
    bearish_ratio DECIMAL(5,4),   -- 하락 전망 비율
    high_risk_posts INT DEFAULT 0,
    top_keywords JSON,            -- 상위 키워드
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_daily_summary (stock_code, date),
    INDEX idx_stock_code_date (stock_code, date),
    INDEX idx_avg_sentiment (avg_sentiment_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
