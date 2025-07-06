"""
post_analysis 테이블의 중복 레코드를 정리하고 UNIQUE 제약조건을 추가하는 스크립트
"""

import logging
from database import get_db_connection
from sqlalchemy import text
from config import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

def fix_duplicate_analysis():
    """post_analysis 테이블의 중복 레코드를 정리"""
    engine = get_db_connection()
    if engine is None:
        logger.error("DB 연결 실패")
        return False
    
    try:
        with engine.connect() as conn:
            # 현재 상황 확인
            logger.info("=== 중복 레코드 정리 시작 ===")
            
            total_query = text("SELECT COUNT(*) FROM post_analysis")
            unique_query = text("SELECT COUNT(DISTINCT post_id) FROM post_analysis")
            
            total_before = conn.execute(total_query).fetchone()[0]
            unique_before = conn.execute(unique_query).fetchone()[0]
            
            logger.info(f"정리 전 - 전체 레코드: {total_before}, 고유 post_id: {unique_before}, 중복: {total_before - unique_before}")
            
            # 중복 레코드 중 가장 최신 것만 남기고 나머지 삭제
            # (created_at이 최신인 것을 유지)
            cleanup_query = text("""
                DELETE pa1 FROM post_analysis pa1
                INNER JOIN post_analysis pa2 
                WHERE pa1.post_id = pa2.post_id 
                AND pa1.id < pa2.id
            """)
            
            result = conn.execute(cleanup_query)
            deleted_count = result.rowcount
            logger.info(f"중복 레코드 {deleted_count}개 삭제 완료")
            
            # 정리 후 상황 확인
            total_after = conn.execute(total_query).fetchone()[0]
            unique_after = conn.execute(unique_query).fetchone()[0]
            
            logger.info(f"정리 후 - 전체 레코드: {total_after}, 고유 post_id: {unique_after}, 중복: {total_after - unique_after}")
            
            # UNIQUE 제약조건 추가 (이미 있으면 에러가 나지만 무시)
            try:
                add_unique_query = text("""
                    ALTER TABLE post_analysis 
                    ADD UNIQUE KEY unique_post_id (post_id)
                """)
                conn.execute(add_unique_query)
                logger.info("post_id에 UNIQUE 제약조건 추가 완료")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    logger.info("UNIQUE 제약조건이 이미 존재합니다.")
                else:
                    logger.warning(f"UNIQUE 제약조건 추가 실패: {e}")
            
            conn.commit()
            logger.info("=== 중복 레코드 정리 완료 ===")
            
            return True
            
    except Exception as e:
        logger.error(f"중복 레코드 정리 실패: {e}")
        return False
    finally:
        engine.dispose()

def validate_analysis_integrity():
    """분석 결과 데이터 정합성 검증"""
    engine = get_db_connection()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            logger.info("=== 데이터 정합성 검증 ===")
            
            # 1. 분석 완료로 표시되었지만 분석 결과가 없는 게시글
            orphan_analyzed_query = text("""
                SELECT COUNT(*) 
                FROM stock_posts sp
                WHERE sp.is_analyzed = TRUE
                AND NOT EXISTS (
                    SELECT 1 FROM post_analysis pa WHERE pa.post_id = sp.id
                )
            """)
            orphan_analyzed = conn.execute(orphan_analyzed_query).fetchone()[0]
            
            # 2. 분석 결과는 있지만 분석 완료로 표시되지 않은 게시글
            orphan_results_query = text("""
                SELECT COUNT(*) 
                FROM post_analysis pa
                JOIN stock_posts sp ON pa.post_id = sp.id
                WHERE sp.is_analyzed = FALSE
            """)
            orphan_results = conn.execute(orphan_results_query).fetchone()[0]
            
            # 3. 존재하지 않는 게시글을 참조하는 분석 결과
            invalid_refs_query = text("""
                SELECT COUNT(*) 
                FROM post_analysis pa
                WHERE NOT EXISTS (
                    SELECT 1 FROM stock_posts sp WHERE sp.id = pa.post_id
                )
            """)
            invalid_refs = conn.execute(invalid_refs_query).fetchone()[0]
            
            logger.info(f"분석 완료 플래그만 있고 결과 없음: {orphan_analyzed}개")
            logger.info(f"분석 결과만 있고 플래그 없음: {orphan_results}개")
            logger.info(f"존재하지 않는 게시글 참조: {invalid_refs}개")
            
            # 정합성 문제 수정
            if orphan_analyzed > 0:
                logger.info("분석 완료 플래그 재설정 중...")
                reset_flag_query = text("""
                    UPDATE stock_posts sp
                    SET is_analyzed = FALSE
                    WHERE sp.is_analyzed = TRUE
                    AND NOT EXISTS (
                        SELECT 1 FROM post_analysis pa WHERE pa.post_id = sp.id
                    )
                """)
                conn.execute(reset_flag_query)
                logger.info(f"분석 완료 플래그 {orphan_analyzed}개 재설정 완료")
            
            if orphan_results > 0:
                logger.info("분석 완료 플래그 설정 중...")
                set_flag_query = text("""
                    UPDATE stock_posts sp
                    JOIN post_analysis pa ON sp.id = pa.post_id
                    SET sp.is_analyzed = TRUE
                    WHERE sp.is_analyzed = FALSE
                """)
                conn.execute(set_flag_query)
                logger.info(f"분석 완료 플래그 {orphan_results}개 설정 완료")
            
            if invalid_refs > 0:
                logger.warning(f"⚠️ 존재하지 않는 게시글을 참조하는 분석 결과 {invalid_refs}개 발견")
                logger.warning("   수동으로 확인이 필요합니다.")
            
            conn.commit()
            logger.info("=== 데이터 정합성 검증 완료 ===")
            
    except Exception as e:
        logger.error(f"데이터 정합성 검증 실패: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    # 중복 레코드 정리
    if fix_duplicate_analysis():
        # 데이터 정합성 검증 및 수정
        validate_analysis_integrity()
        print("\n✅ post_analysis 테이블 정리 완료!")
        print("이제 ON DUPLICATE KEY UPDATE가 정상적으로 작동할 것입니다.")
    else:
        print("❌ 정리 작업 실패")
