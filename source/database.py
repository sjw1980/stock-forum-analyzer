import pandas as pd
from sqlalchemy import create_engine, text
import logging
import pymysql
from datetime import datetime
from config import DB_CONFIG
from urllib.parse import quote_plus

# 로깅 설정
logger = logging.getLogger(__name__)

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
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def get_existing_posts(stock_code):
    """기존에 저장된 게시글 데이터 조회 (중복 체크용)"""
    engine = get_db_connection()
    if engine is None:
        return set()
    
    try:
        query = text("SELECT date, author FROM stock_posts WHERE stock_code = :stock_code")
        df = pd.read_sql(query, engine, params={'stock_code': stock_code})
        
        # 날짜와 작성자를 문자열로 변환하고 공백 제거
        existing_set = set()
        for _, row in df.iterrows():
            # DATETIME 형식으로 저장된 날짜를 문자열로 변환
            if pd.isna(row['date']):
                date_str = "Unknown"
            elif isinstance(row['date'], datetime):
                date_str = row['date'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = str(row['date']).strip()
            
            author_str = str(row['author']).strip()
            existing_set.add((date_str, author_str))
        
        logger.info(f"기존 데이터 {len(existing_set)}개 로드 완료")
        
        # 디버깅을 위해 몇 개 샘플 출력
        if existing_set:
            sample_keys = list(existing_set)[:3]
            logger.debug(f"기존 데이터 샘플: {sample_keys}")
        
        return existing_set
    except Exception as e:
        logger.error(f"기존 데이터 조회 실패: {e}")
        return set()
    finally:
        engine.dispose()

def save_posts_to_db(posts_df, stock_code):
    """게시글 데이터를 데이터베이스에 저장"""
    if posts_df.empty:
        logger.info("저장할 데이터가 없습니다.")
        return 0
    
    engine = get_db_connection()
    if engine is None:
        logger.error("데이터베이스 연결 실패")
        return 0
    
    try:
        # 데이터 전처리
        posts_df = posts_df.copy()
        posts_df['stock_code'] = stock_code
        
        # 컬럼명 영문으로 변경
        posts_df = posts_df.rename(columns={
            '날짜': 'date',
            '제목': 'title',
            '작성자': 'author',
            '조회수': 'views',
            '공감': 'likes',
            '비공감': 'dislikes',
            '링크': 'link'
        })
        
        # 날짜 형식 변환 (DATETIME으로 저장)
        posts_df['date'] = pd.to_datetime(posts_df['date'], errors='coerce')
        
        # content와 is_analyzed 컬럼 초기화
        posts_df['content'] = ''
        posts_df['is_analyzed'] = False
        
        # 데이터 정리 (None 값 처리)
        posts_df = posts_df.fillna('')
        
        saved_count = 0
        
        # 각 행을 개별적으로 저장 (중복 처리를 위해)
        with engine.connect() as conn:
            for idx, row in posts_df.iterrows():
                try:
                    # 중복 확인
                    check_query = text("""
                        SELECT COUNT(*) as count FROM stock_posts 
                        WHERE stock_code = :stock_code 
                        AND date = :date 
                        AND author = :author 
                        AND title = :title
                    """)
                    
                    result = conn.execute(check_query, {
                        'stock_code': row['stock_code'],
                        'date': row['date'],
                        'author': row['author'],
                        'title': row['title'][:100] if row['title'] else ''
                    }).fetchone()
                    
                    if result[0] == 0:  # 중복이 아닌 경우만 삽입
                        insert_query = text("""
                            INSERT INTO stock_posts 
                            (stock_code, date, title, author, views, likes, dislikes, link, content, is_analyzed)
                            VALUES 
                            (:stock_code, :date, :title, :author, :views, :likes, :dislikes, :link, :content, :is_analyzed)
                        """)
                        
                        conn.execute(insert_query, {
                            'stock_code': row['stock_code'],
                            'date': row['date'],
                            'title': row['title'],
                            'author': row['author'],
                            'views': row['views'],
                            'likes': row['likes'],
                            'dislikes': row['dislikes'],
                            'link': row['link'],
                            'content': row['content'],
                            'is_analyzed': row['is_analyzed']
                        })
                        
                        saved_count += 1
                        logger.debug(f"저장 완료: {row['title'][:50]}...")
                    else:
                        logger.debug(f"중복 건너뜀: {row['title'][:50]}...")
                        
                except Exception as e:
                    logger.error(f"개별 행 저장 실패: {e}, 행 데이터: {row.to_dict()}")
                    continue
            
            conn.commit()
        
        logger.info(f"{saved_count}개의 새로운 게시글이 데이터베이스에 저장되었습니다.")
        return saved_count
        
    except Exception as e:
        logger.error(f"데이터베이스 저장 실패: {e}")
        return 0
    finally:
        engine.dispose()

def get_posts_count_from_db(stock_code):
    """해당 종목의 총 게시글 수 조회"""
    engine = get_db_connection()
    if engine is None:
        return 0
    
    try:
        query = text("SELECT COUNT(*) as count FROM stock_posts WHERE stock_code = :stock_code")
        result = pd.read_sql(query, engine, params={'stock_code': stock_code})
        return result.iloc[0]['count']
    except Exception as e:
        logger.error(f"게시글 수 조회 실패: {e}")
        return 0
    finally:
        engine.dispose()

def test_database_connection():
    """데이터베이스 연결 테스트"""
    engine = get_db_connection()
    if engine is None:
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with engine.connect() as conn:
            # 테이블 존재 확인
            tables_query = text("SHOW TABLES")
            result = conn.execute(tables_query).fetchall()
            
            print("✅ 데이터베이스 연결 성공")
            print("📊 존재하는 테이블:")
            for table in result:
                print(f"  - {table[0]}")
            
            # 각 테이블의 행 수 확인
            for table in result:
                table_name = table[0]
                count_query = text(f"SELECT COUNT(*) as count FROM {table_name}")
                count_result = conn.execute(count_query).fetchone()
                print(f"    └─ {table_name}: {count_result[0]}개 행")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        return False
    finally:
        engine.dispose()

def view_database_contents(stock_code=None, limit=100):
    """데이터베이스에 저장된 내용 확인"""
    engine = get_db_connection()
    if engine is None:
        print("데이터베이스 연결 실패")
        return
    
    try:
        # 게시글 테이블 조회
        if stock_code:
            posts_query = text("""
                SELECT id, stock_code, date, title, author, views, likes, dislikes, is_analyzed, created_at
                FROM stock_posts 
                WHERE stock_code = :stock_code
                ORDER BY date DESC, created_at DESC
                LIMIT :limit
            """)
            posts_df = pd.read_sql(posts_query, engine, params={'stock_code': stock_code, 'limit': limit})
            print(f"\n📋 {stock_code} 종목 게시글 목록 (최근 {limit}개):")
        else:
            posts_query = text("""
                SELECT id, stock_code, date, title, author, views, likes, dislikes, is_analyzed, created_at
                FROM stock_posts 
                ORDER BY date DESC
                LIMIT :limit
            """)
            posts_df = pd.read_sql(posts_query, engine, params={'limit': limit})
            print(f"\n📋 전체 게시글 목록 (최근 {limit}개):")
        
        if not posts_df.empty:
            for idx, row in posts_df.iterrows():
                analyzed_status = "✅" if row['is_analyzed'] else "❌"
                print(f"  {idx:3d}. [{row['date']}] {row['title'][:40]}... "
                      f"(작성자: {row['author']}, 분석: {analyzed_status})")
        else:
            print("  저장된 게시글이 없습니다.")
        
        # 통계 정보
        stats_query = text("SELECT COUNT(*) as total_posts FROM stock_posts")
        if stock_code:
            stats_query = text("SELECT COUNT(*) as total_posts FROM stock_posts WHERE stock_code = :stock_code")
            stats_result = pd.read_sql(stats_query, engine, params={'stock_code': stock_code})
        else:
            stats_result = pd.read_sql(stats_query, engine)
        
        total_posts = stats_result.iloc[0]['total_posts']
        print(f"\n📊 저장된 총 게시글 수: {total_posts}개")
        
        # 분석 결과가 있다면 표시
        if stock_code:
            analysis_query = text("""
                SELECT pa.sentiment_label, COUNT(*) as count
                FROM post_analysis pa
                JOIN stock_posts sp ON pa.post_id = sp.id
                WHERE sp.stock_code = :stock_code
                GROUP BY pa.sentiment_label
            """)
            analysis_df = pd.read_sql(analysis_query, engine, params={'stock_code': stock_code})
        else:
            analysis_query = text("""
                SELECT pa.sentiment_label, COUNT(*) as count
                FROM post_analysis pa
                GROUP BY pa.sentiment_label
            """)
            analysis_df = pd.read_sql(analysis_query, engine)
        
        if not analysis_df.empty:
            print("\n🔍 감정 분석 결과:")
            for _, row in analysis_df.iterrows():
                print(f"  {row['sentiment_label']}: {row['count']}개")
        
    except Exception as e:
        print(f"데이터베이스 조회 실패: {e}")
    finally:
        engine.dispose()

def process_engine(engine, stock_code):
    if engine:
        try:
            with engine.connect() as conn:
                # 데이터 상태 분석
                print("=== 데이터 상태 분석 ===")
                
                # 전체 게시글 수
                total_query = text("SELECT COUNT(*) as total FROM stock_posts WHERE stock_code = :stock_code")
                total_result = conn.execute(total_query, {'stock_code': stock_code}).fetchone()
                total_posts = total_result[0] if total_result else 0
                
                # 분석 완료된 게시글 수
                analyzed_query = text("SELECT COUNT(*) as analyzed FROM stock_posts WHERE stock_code = :stock_code AND is_analyzed = TRUE")
                analyzed_result = conn.execute(analyzed_query, {'stock_code': stock_code}).fetchone()
                analyzed_posts = analyzed_result[0] if analyzed_result else 0
                
                # 분석 대상 게시글 수 (제목과 링크가 있는 것)
                target_query = text("""
                    SELECT COUNT(*) as target FROM stock_posts 
                    WHERE stock_code = :stock_code 
                    AND is_analyzed = FALSE 
                    AND link != '' 
                    AND link IS NOT NULL
                    AND title != ''
                    AND title IS NOT NULL
                    AND TRIM(title) != ''
                """)
                target_result = conn.execute(target_query, {'stock_code': stock_code}).fetchone()
                target_posts = target_result[0] if target_result else 0
                
                # post_analysis 테이블의 레코드 수
                analysis_query = text("""
                    SELECT COUNT(*) as analysis_count 
                    FROM post_analysis pa 
                    JOIN stock_posts sp ON pa.post_id = sp.id 
                    WHERE sp.stock_code = :stock_code
                """)
                analysis_result = conn.execute(analysis_query, {'stock_code': stock_code}).fetchone()
                analysis_count = analysis_result[0] if analysis_result else 0
                
                # 제목이나 링크가 없는 게시글 수
                excluded_query = text("""
                    SELECT COUNT(*) as excluded FROM stock_posts 
                    WHERE stock_code = :stock_code 
                    AND (link = '' OR link IS NULL OR title = '' OR title IS NULL OR TRIM(title) = '')
                """)
                excluded_result = conn.execute(excluded_query, {'stock_code': stock_code}).fetchone()
                excluded_posts = excluded_result[0] if excluded_result else 0
                
                print(f"📊 전체 게시글: {total_posts}개")
                print(f"📊 분석 완료: {analyzed_posts}개")
                print(f"📊 분석 대상: {target_posts}개")
                print(f"📊 분석 결과 레코드: {analysis_count}개")
                print(f"📊 제외된 게시글: {excluded_posts}개 (제목/링크 없음)")
                
                # 불일치 상황 분석
                if analyzed_posts != analysis_count:
                    print(f"⚠️ 분석 완료 게시글({analyzed_posts})과 분석 결과 레코드({analysis_count}) 수가 다릅니다!")
                
                # 미분석 게시글 샘플 확인
                if target_posts > 0:
                    sample_query = text("""
                        SELECT id, title, link, content, is_analyzed
                        FROM stock_posts 
                        WHERE stock_code = :stock_code 
                        AND is_analyzed = FALSE 
                        AND link != '' 
                        AND link IS NOT NULL
                        AND title != ''
                        AND title IS NOT NULL
                        AND TRIM(title) != ''
                        LIMIT 5
                    """)
                    sample_result = conn.execute(sample_query, {'stock_code': stock_code}).fetchall()
                    
                    print("📋 미분석 게시글 샘플:")
                    for row in sample_result:
                        print(f"  ID: {row[0]}, 제목: {row[1][:30]}..., 링크: {'있음' if row[2] else '없음'}, 본문: {'있음' if row[3] else '없음'}, 분석완료: {row[4]}")
                
                # 분석 오류가 있는 게시글 찾기
                error_query = text("""
                    SELECT id, title, is_analyzed
                    FROM stock_posts sp
                    WHERE stock_code = :stock_code 
                    AND is_analyzed = TRUE
                    AND NOT EXISTS (
                        SELECT 1 FROM post_analysis pa WHERE pa.post_id = sp.id
                    )
                    LIMIT 5
                """)
                error_result = conn.execute(error_query, {'stock_code': stock_code}).fetchall()
                
                if error_result:
                    print("⚠️ 분석 완료로 표시되었지만 분석 결과가 없는 게시글:")
                    for row in error_result:
                        print(f"  ID: {row[0]}, 제목: {row[1][:30]}..., 분석완료: {row[2]}")
            
            # 최근 분석 결과 요약
            summary_query = text("""
                SELECT 
                    sentiment_label,
                    bullish_bearish,
                    risk_level,
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_sentiment,
                    AVG(confidence_score) as avg_confidence
                FROM post_analysis pa
                JOIN stock_posts sp ON pa.post_id = sp.id
                WHERE sp.stock_code = :stock_code
                AND pa.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
                GROUP BY sentiment_label, bullish_bearish, risk_level
                ORDER BY count DESC
            """)
            
            summary_df = pd.read_sql(summary_query, engine, params={'stock_code': stock_code})
            if not summary_df.empty:
                print("\n📊 최근 24시간 분석 결과:")
                for _, row in summary_df.iterrows():
                    print(f"  감정: {row['sentiment_label']}, 전망: {row['bullish_bearish']}, "
                        f"위험도: {row['risk_level']}, 게시글 수: {row['count']}")
                
                # 전체 감정 분포
                total_query = text("""
                    SELECT 
                        sentiment_label,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM post_analysis pa2 
                                                JOIN stock_posts sp2 ON pa2.post_id = sp2.id 
                                                WHERE sp2.stock_code = :stock_code), 1) as percentage
                    FROM post_analysis pa
                    JOIN stock_posts sp ON pa.post_id = sp.id
                    WHERE sp.stock_code = :stock_code
                    GROUP BY sentiment_label
                """)
                
                total_df = pd.read_sql(total_query, engine, params={'stock_code': stock_code})
                if not total_df.empty:
                    print(f"\n📈 전체 감정 분포 (종목: {stock_code}):")
                    for _, row in total_df.iterrows():
                        print(f"  {row['sentiment_label']}: {row['count']}개 ({row['percentage']}%)")
            else:
                print("\n📊 분석된 데이터가 없습니다.")
            
        except Exception as e:
            print(f"분석 결과 요약 실패: {e}")
        finally:
            engine.dispose()

if __name__ == "__main__":
    print(get_db_connection())