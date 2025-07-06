import pandas as pd
from sqlalchemy import text
import json
import time
import logging
from database import get_db_connection
from crawler import get_post_content

# 로깅 설정
logger = logging.getLogger(__name__)

def analyze_post_sentiment(content):
    """게시글 감정 분석"""
    if not content:
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence_score': 0.0,
            'keywords': [],
            'bullish_bearish': 'neutral',
            'risk_level': 'low'
        }
    
    try:
        # 키워드 기반 감정 분석 - 더 많은 키워드 추가
        positive_keywords = [
            '상승', '급등', '호재', '좋다', '매수', '추천', '긍정', '성장', '이익', '수익',
            '올라', '오를', '상승세', '강세', '반등', '회복', '개선', '기대', '전망', '투자',
            '목표가', '상향', '돌파', '지지', '우상향', '플러스', '수혜', '성과'
        ]
        negative_keywords = [
            '하락', '급락', '악재', '나쁘다', '매도', '손실', '위험', '부정', '하락세', '손해',
            '떨어', '내려', '약세', '조정', '하락폭', '우하향', '저조', '부진', '위축',
            '마이너스', '적자', '손실', '리스크', '불안', '걱정', '우려', '경고'
        ]
        bullish_keywords = [
            '상승', '급등', '매수', '호재', '성장', '오를', '상승세', '강세', '반등',
            '돌파', '목표가', '상향', '투자', '기대', '전망', '수혜'
        ]
        bearish_keywords = [
            '하락', '급락', '매도', '악재', '떨어', '하락세', '약세', '조정',
            '손실', '위험', '우려', '경고', '부진'
        ]
        
        # 키워드 추출
        keywords = []
        for keyword in positive_keywords + negative_keywords:
            if keyword in content:
                keywords.append(keyword)
        
        # 감정 점수 계산
        positive_count = sum(1 for word in positive_keywords if word in content)
        negative_count = sum(1 for word in negative_keywords if word in content)
        total_count = positive_count + negative_count
        
        if total_count == 0:
            sentiment_score = 0.0
            sentiment_label = 'neutral'
            confidence_score = 0.0
        else:
            sentiment_score = (positive_count - negative_count) / total_count
            confidence_score = min(total_count / 10.0, 1.0)  # 최대 1.0
            
            if sentiment_score > 0.2:
                sentiment_label = 'positive'
            elif sentiment_score < -0.2:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
        
        # 상승/하락 전망 분석
        bullish_count = sum(1 for word in bullish_keywords if word in content)
        bearish_count = sum(1 for word in bearish_keywords if word in content)
        
        if bullish_count > bearish_count:
            bullish_bearish = 'bullish'
        elif bearish_count > bullish_count:
            bullish_bearish = 'bearish'
        else:
            bullish_bearish = 'neutral'
        
        # 위험도 계산
        risk_keywords = ['위험', '손실', '급락', '폭락', '주의']
        risk_count = sum(1 for word in risk_keywords if word in content)
        
        if risk_count >= 3:
            risk_level = 'high'
        elif risk_count >= 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'sentiment_score': round(sentiment_score, 4),
            'sentiment_label': sentiment_label,
            'confidence_score': round(confidence_score, 4),
            'keywords': keywords[:10],  # 상위 10개 키워드만
            'bullish_bearish': bullish_bearish,
            'risk_level': risk_level
        }
        
    except Exception as e:
        logger.error(f"감정 분석 실패: {e}")
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence_score': 0.0,
            'keywords': [],
            'bullish_bearish': 'neutral',
            'risk_level': 'low'
        }

def get_unanalyzed_posts(stock_code, limit=100): # limit=100, 1 = 테스트용
    """분석되지 않은 게시글 조회"""
    engine = get_db_connection()
    if engine is None:
        return pd.DataFrame()
    
    try:
        query = text("""
            SELECT id, link, title, content 
            FROM stock_posts 
            WHERE stock_code = :stock_code 
            AND is_analyzed = FALSE 
            AND link != '' 
            AND title != ''
            AND title IS NOT NULL
            AND TRIM(title) != ''
            ORDER BY date DESC 
            LIMIT :limit
        """)
        df = pd.read_sql(query, engine, params={'stock_code': stock_code, 'limit': limit})
        return df
    except Exception as e:
        logger.error(f"미분석 게시글 조회 실패: {e}")
        return pd.DataFrame()
    finally:
        engine.dispose()

def update_post_content(post_id, content):
    """게시글 본문 내용 업데이트"""
    engine = get_db_connection()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            query = text("UPDATE stock_posts SET content = :content WHERE id = :post_id")
            conn.execute(query, {'content': content, 'post_id': post_id})
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"게시글 본문 업데이트 실패: {e}")
        return False
    finally:
        engine.dispose()

def save_analysis_result(post_id, analysis_result):
    """분석 결과를 데이터베이스에 저장"""
    engine = get_db_connection()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            # 분석 결과 저장
            analysis_query = text("""
                INSERT INTO post_analysis 
                (post_id, sentiment_score, sentiment_label, confidence_score, 
                 keywords, bullish_bearish, risk_level, analysis_model, analysis_version)
                VALUES 
                (:post_id, :sentiment_score, :sentiment_label, :confidence_score,
                 :keywords, :bullish_bearish, :risk_level, :analysis_model, :analysis_version)
                ON DUPLICATE KEY UPDATE
                sentiment_score = VALUES(sentiment_score),
                sentiment_label = VALUES(sentiment_label),
                confidence_score = VALUES(confidence_score),
                keywords = VALUES(keywords),
                bullish_bearish = VALUES(bullish_bearish),
                risk_level = VALUES(risk_level),
                updated_at = CURRENT_TIMESTAMP
            """)
            
            conn.execute(analysis_query, {
                'post_id': post_id,
                'sentiment_score': analysis_result['sentiment_score'],
                'sentiment_label': analysis_result['sentiment_label'],
                'confidence_score': analysis_result['confidence_score'],
                'keywords': json.dumps(analysis_result['keywords'], ensure_ascii=False),
                'bullish_bearish': analysis_result['bullish_bearish'],
                'risk_level': analysis_result['risk_level'],
                'analysis_model': 'keyword_based',
                'analysis_version': '1.0'
            })
            
            # 게시글 분석 완료 표시
            update_query = text("UPDATE stock_posts SET is_analyzed = TRUE WHERE id = :post_id")
            conn.execute(update_query, {'post_id': post_id})
            
            conn.commit()
        
        return True
    except Exception as e:
        logger.error(f"분석 결과 저장 실패: {e}")
        return False
    finally:
        engine.dispose()

def analyze_posts_content(stock_code):
    """게시글 본문 크롤링 및 분석 수행"""
    # 먼저 제목/링크가 없는 게시글들을 분석 완료로 표시
    mark_empty_posts_as_analyzed(stock_code)
    
    # 분석 가능한 게시글들 조회
    unanalyzed_posts = get_unanalyzed_posts(stock_code)
    
    if unanalyzed_posts.empty:
        logger.info("분석할 게시글이 없습니다.")
        return 0
    
    logger.info(f"분석 대상 게시글: {len(unanalyzed_posts)}개")
    analyzed_count = 0
    
    for idx, post in unanalyzed_posts.iterrows():
        try:
            post_id = post['id']
            link = post['link']
            
            logger.info(f"게시글 분석 중: {post_id} ({idx + 1}/{len(unanalyzed_posts)})")
            
            # 본문이 없으면 크롤링
            content = post['content']
            title = post['title']
            
            if not content and link:
                logger.debug(f"게시글 본문 크롤링 중: {link}")
                crawled_content = get_post_content(link)
                if crawled_content:
                    content = crawled_content  # 변수에도 업데이트
                    update_post_content(post_id, content)
                    logger.debug(f"본문 크롤링 완료: {len(content)}자")
                else:
                    logger.warning(f"본문 크롤링 실패: {link}")
            
            # 제목과 본문을 합쳐서 분석 (제목도 중요한 감정 정보 포함)
            full_text = f"{title} {content}".strip()
            
            # 감정 분석 수행
            if full_text:
                analysis_result = analyze_post_sentiment(full_text)
                if save_analysis_result(post_id, analysis_result):
                    analyzed_count += 1
                    logger.info(f"분석 완료: 감정={analysis_result['sentiment_label']}, 전망={analysis_result['bullish_bearish']}")
            else:
                # 제목과 본문이 모두 없는 경우
                logger.warning(f"게시글 {post_id}: 제목과 본문이 모두 비어있음")
                save_analysis_result(post_id, {
                    'sentiment_score': 0.0,
                    'sentiment_label': 'neutral',
                    'confidence_score': 0.0,
                    'keywords': [],
                    'bullish_bearish': 'neutral',
                    'risk_level': 'low'
                })
            
            # 서버 부하 방지
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"게시글 {post_id} 분석 실패: {e}")
            continue
    
    return analyzed_count

def mark_empty_posts_as_analyzed(stock_code):
    """제목이 없거나 링크가 없는 게시글을 분석 완료로 표시"""
    engine = get_db_connection()
    if engine is None:
        return 0
    
    try:
        with engine.connect() as conn:
            # 제목이 없거나 링크가 없는 게시글을 분석 완료로 표시
            query = text("""
                UPDATE stock_posts 
                SET is_analyzed = TRUE 
                WHERE stock_code = :stock_code 
                AND is_analyzed = FALSE 
                AND (
                    link = '' 
                    OR link IS NULL 
                    OR title = '' 
                    OR title IS NULL 
                    OR TRIM(title) = ''
                )
            """)
            result = conn.execute(query, {'stock_code': stock_code})
            conn.commit()
            
            updated_count = result.rowcount
            if updated_count > 0:
                logger.info(f"제목/링크가 없는 {updated_count}개 게시글을 분석 완료로 표시했습니다.")
            
            return updated_count
    except Exception as e:
        logger.error(f"빈 게시글 처리 실패: {e}")
        return 0
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("hi")