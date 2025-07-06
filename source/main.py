import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
import pymysql
from sqlalchemy import create_engine, text
import logging
import re
import json
from collections import Counter
import numpy as np
from database import test_database_connection, view_database_contents, get_existing_posts, save_posts_to_db,get_posts_count_from_db, get_db_connection, process_engine
from crawler import crawl_stock_discussion
from sentiment_analyzer import analyze_posts_content

# 로깅 설정 (디버깅 모드)
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # 데이터베이스 연결 테스트
    logger.info("=== 데이터베이스 연결 테스트 ===")
    if not test_database_connection():
        logger.error("데이터베이스 연결에 실패했습니다. Docker 컨테이너가 실행 중인지 확인하세요.")
        exit(1)
    
    # 139480 종목의 게시글 수집
    stock_code = "139480"
    
    # 기존 데이터 확인
    logger.info("=== 기존 데이터 확인 ===")
    view_database_contents(stock_code, limit=5)
    
    # 1단계: 게시글 목록 수집
    logger.info("=== 게시글 목록 수집 시작 ===")
    existing_set = get_existing_posts(stock_code)
    recent_posts = crawl_stock_discussion(stock_code, start_page=1, end_page=10, existing_set=existing_set)
    keep_continue = True
    
    if not recent_posts.empty:
        logger.info(f"수집된 게시글 수: {len(recent_posts)}개")
        # 수집된 데이터 미리보기
        print("\n📝 수집된 데이터 미리보기:")
        for idx, row in recent_posts.head(3).iterrows():
            print(f"  - [{row['날짜']}] {row['제목'][:40]}... (작성자: {row['작성자']})")
        
        saved_count = save_posts_to_db(recent_posts, stock_code)
        total_count = get_posts_count_from_db(stock_code)
        logger.info(f"새로 수집된 게시글: {saved_count}개")
        logger.info(f"총 저장된 게시글: {total_count}개")
        
        # 저장 후 데이터 확인
        logger.info("=== 저장 후 데이터 확인 ===")
        view_database_contents(stock_code, limit=10)
    else:
        logger.info("새로운 게시글이 없습니다.")
        # keep_continue = False
    
    if keep_continue:
        # 2단계: 게시글 본문 크롤링 및 분석
        logger.info("=== 게시글 분석 시작 ===")
        analyzed_count = analyze_posts_content(stock_code)
        logger.info(f"분석 완료된 게시글: {analyzed_count}개")
        
        # 3단계: 분석 결과 요약 출력
        logger.info("=== 분석 결과 요약 ===")
        engine = get_db_connection()
        process_engine(engine, stock_code)
        