import pandas as pd
from sqlalchemy import create_engine, text
import json
from datetime import datetime, timedelta
import pymysql
from config import DB_CONFIG
from urllib.parse import quote_plus

def get_db_connection():
    """데이터베이스 연결 객체 반환"""
    try:
        # 비밀번호에 특수 문자가 있을 경우 URL 인코딩
        encoded_password = quote_plus(DB_CONFIG['password'])
        encoded_user = quote_plus(DB_CONFIG['user'])
        
        connection_string = f"mysql+pymysql://{encoded_user}:{encoded_password}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
        engine = create_engine(connection_string, echo=False)
        return engine
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        return None

def get_analysis_summary(stock_code, days=7):
    """지정된 기간의 분석 결과 요약"""
    engine = get_db_connection()
    if engine is None:
        return None
    
    try:
        query = text("""
            SELECT 
                DATE(sp.date) as analysis_date,
                COUNT(*) as total_posts,
                SUM(CASE WHEN pa.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN pa.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN pa.sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                SUM(CASE WHEN pa.bullish_bearish = 'bullish' THEN 1 ELSE 0 END) as bullish_count,
                SUM(CASE WHEN pa.bullish_bearish = 'bearish' THEN 1 ELSE 0 END) as bearish_count,
                AVG(pa.sentiment_score) as avg_sentiment_score,
                AVG(pa.confidence_score) as avg_confidence_score
            FROM stock_posts sp
            JOIN post_analysis pa ON sp.id = pa.post_id
            WHERE sp.stock_code = :stock_code
            AND sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            GROUP BY DATE(sp.date)
            ORDER BY analysis_date DESC
        """)
        
        df = pd.read_sql(query, engine, params={'stock_code': stock_code, 'days': days})
        return df
        
    except Exception as e:
        print(f"분석 요약 조회 실패: {e}")
        return None
    finally:
        engine.dispose()

def get_keyword_analysis(stock_code, days=7, top_n=20):
    """키워드 분석 결과"""
    engine = get_db_connection()
    if engine is None:
        return None
    
    try:
        query = text("""
            SELECT pa.keywords
            FROM stock_posts sp
            JOIN post_analysis pa ON sp.id = pa.post_id
            WHERE sp.stock_code = :stock_code
            AND sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            AND pa.keywords IS NOT NULL
            AND pa.keywords != '[]'
        """)
        
        df = pd.read_sql(query, engine, params={'stock_code': stock_code, 'days': days})
        
        # 키워드 빈도 계산
        all_keywords = []
        for keywords_str in df['keywords']:
            try:
                keywords = json.loads(keywords_str)
                all_keywords.extend(keywords)
            except:
                continue
        
        keyword_counts = pd.Series(all_keywords).value_counts().head(top_n)
        return keyword_counts
        
    except Exception as e:
        print(f"키워드 분석 실패: {e}")
        return None
    finally:
        engine.dispose()

def print_analysis_report(stock_code, days=7):
    """분석 리포트 출력"""
    print(f"\n📊 {stock_code} 종목 분석 리포트 (최근 {days}일)")
    print("=" * 50)
    
    # 1. 전체 요약
    summary_df = get_analysis_summary(stock_code, days)
    if summary_df is not None and not summary_df.empty:
        total_posts = summary_df['total_posts'].sum()
        total_positive = summary_df['positive_count'].sum()
        total_negative = summary_df['negative_count'].sum()
        total_neutral = summary_df['neutral_count'].sum()
        total_bullish = summary_df['bullish_count'].sum()
        total_bearish = summary_df['bearish_count'].sum()
        avg_sentiment = summary_df['avg_sentiment_score'].mean()
        
        print(f"📈 전체 통계:")
        print(f"  총 분석된 게시글: {total_posts}개")
        print(f"  긍정: {total_positive}개 ({total_positive/total_posts*100:.1f}%)")
        print(f"  부정: {total_negative}개 ({total_negative/total_posts*100:.1f}%)")
        print(f"  중립: {total_neutral}개 ({total_neutral/total_posts*100:.1f}%)")
        print(f"  상승전망: {total_bullish}개 ({total_bullish/total_posts*100:.1f}%)")
        print(f"  하락전망: {total_bearish}개 ({total_bearish/total_posts*100:.1f}%)")
        print(f"  평균 감정점수: {avg_sentiment:.3f}")
        
        # 2. 일별 추이
        print(f"\n📅 일별 감정 추이:")
        for _, row in summary_df.iterrows():
            date = row['analysis_date']
            sentiment_ratio = row['positive_count'] / row['total_posts'] * 100 if row['total_posts'] > 0 else 0
            bullish_ratio = row['bullish_count'] / row['total_posts'] * 100 if row['total_posts'] > 0 else 0
            print(f"  {date}: 긍정비율 {sentiment_ratio:.1f}%, 상승전망 {bullish_ratio:.1f}% (총 {row['total_posts']}개)")
    
    # 3. 키워드 분석
    keywords = get_keyword_analysis(stock_code, days)
    if keywords is not None and not keywords.empty:
        print(f"\n🔍 주요 키워드 (Top 10):")
        for i, (keyword, count) in enumerate(keywords.head(10).items(), 1):
            print(f"  {i:2d}. {keyword}: {count}회")

if __name__ == "__main__":
    # 사용 예시
    stock_code = "139480"
    print_analysis_report(stock_code, days=7)
