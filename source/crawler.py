import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime, timedelta
import re

# 로깅 설정
logger = logging.getLogger(__name__)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://finance.naver.com/'
}

def get_discussion_url(stock_code, page=1):
    """네이버 종목토론실 URL 생성"""
    base_url = "https://finance.naver.com/item/board.naver"
    return f"{base_url}?code={stock_code}&page={page}"

def parse_naver_board_list(html):
    """네이버 종목토론실 게시글 목록 파싱"""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='type2')
    posts = []
    if not table:
        return pd.DataFrame()
    
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) != 6:
            continue  # 헤더, 안내, 클린봇 등 스킵
        
        # 날짜 파싱 개선
        date_raw = cols[0].get_text(strip=True)
        date = parse_date(date_raw)
        
        # 제목 및 링크
        title_td = cols[1]
        blind = title_td.find('span', class_='cleanbot_list_blind')
        a_tag = title_td.find('a')
        
        if blind:
            title = ''
            link = ''
        else:
            if a_tag:
                # 텍스트 노드만 추출 (이미지, span 등 제외)
                text_node = a_tag.find(string=True, recursive=False)
                title = text_node.strip() if text_node else a_tag.get_text(strip=True)
                link = f"https://finance.naver.com{a_tag['href']}" if a_tag.has_attr('href') else ''
            else:
                title = title_td.get_text(strip=True)
                link = ''
        
        # 작성자
        author = cols[2].get_text(strip=True)
        # 조회수
        views = cols[3].get_text(strip=True)
        # 공감/비공감
        like = cols[4].get_text(strip=True)
        dislike = cols[5].get_text(strip=True)
        
        posts.append({
            '날짜': date,
            '제목': title,
            '작성자': author,
            '조회수': views,
            '공감': like,
            '비공감': dislike,
            '링크': link
        })
    
    return pd.DataFrame(posts)

def get_posts_from_page(stock_code, page_no):
    """한 페이지의 게시글 정보를 수집"""
    url = get_discussion_url(stock_code, page_no)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        df = parse_naver_board_list(response.text)
        return df
    except Exception as e:
        logger.error(f"페이지 {page_no} 수집 중 오류: {e}")
        return None

def get_last_page(stock_code):
    """해당 종목 토론실의 마지막 페이지 번호 구하기"""
    url = get_discussion_url(stock_code, 1)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 페이지네이션에서 마지막 페이지 번호 추출
        page_links = soup.select('.pgRR a')
        if page_links:
            last_page_url = page_links[-1]['href']
            last_page = int(last_page_url.split('=')[-1])
            return last_page
        return 1
    except Exception as e:
        logger.error(f"마지막 페이지 조회 실패: {e}")
        return 1

def crawl_stock_discussion(stock_code, start_page=1, end_page=None, existing_set=None, include_title_in_key=False):
    """종목토론실 전체 데이터 수집 (중복시 중단)"""
    
    if end_page is None:
        end_page = get_last_page(stock_code)
    
    all_posts = []
    stop_crawling = False
    
    # 기존 데이터가 제목을 포함하는지 확인
    if existing_set and len(next(iter(existing_set), ())) == 3:
        include_title_in_key = True
        logger.info("기존 데이터가 제목을 포함하므로 제목도 함께 비교합니다.")
    
    for page in range(start_page, end_page + 1):
        logger.info(f"페이지 {page}/{end_page} 수집 중...")
        
        posts_df = get_posts_from_page(stock_code, page)
        if posts_df is not None and not posts_df.empty:
            # 중복 체크 개선
            logger.debug(f"페이지 {page}에서 {len(posts_df)}개 게시글 수집")
            
            page_posts = []
            for idx, row in posts_df.iterrows():
                # 키 생성
                key = create_post_key(row, include_title_in_key)
                
                logger.debug(f"검사 중: {key}")
                
                if existing_set and key in existing_set:
                    logger.info(f"중복 데이터 발견: {key}")
                    logger.info(f"기존 데이터 수: {len(existing_set)}개")
                    stop_crawling = True
                    break
                else:
                    page_posts.append(row)
            
            # 중복 발견 전까지의 데이터만 추가
            if page_posts:
                page_df = pd.DataFrame(page_posts)
                all_posts.append(page_df)
                logger.info(f"페이지 {page}에서 {len(page_posts)}개 새 게시글 추가")
            
            if stop_crawling:
                logger.info(f"중복으로 인한 크롤링 중단 (페이지 {page})")
                break
        else:
            logger.warning(f"페이지 {page} 데이터 수집 실패")
        
        if stop_crawling:
            break
        
        # 서버 부하 방지를 위한 딜레이
        time.sleep(1)
    
    if all_posts:
        final_df = pd.concat(all_posts, ignore_index=True)
        return final_df
    return pd.DataFrame()

def get_post_content(post_url):
    """개별 게시글의 본문 내용을 크롤링"""
    try:
        response = requests.get(post_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = ""
        
        # 방법 1: summary 속성을 이용한 본문 테이블 찾기 (가장 정확한 방법)
        content_table = soup.find('table', {'summary': '게시판 글 본문보기'})
        if content_table:
            # 테이블 내에서 실제 본문 영역 찾기
            content_cells = content_table.find_all('td')
            for cell in content_cells:
                cell_text = cell.get_text(strip=True, separator='\n')
                
                # 본문으로 보이는 셀 조건
                if (len(cell_text) > 5 and 
                    any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in cell_text) and
                    not any(header_word in cell_text for header_word in [
                        '게시판 글 본문보기', '조회', '공감', '비공감', '작성자', 
                        '더보기', 'IP', '작성일', '신고', '스크랩'
                    ])):
                    
                    # 불필요한 텍스트 제거
                    lines = cell_text.split('\n')
                    content_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if (line and 
                            len(line) > 1 and 
                            not line.replace(',', '').replace('.', '').isdigit() and  # 숫자만 있는 라인 제외
                            not any(word in line for word in [
                                '게시판 글 본문보기', '조회', '공감', '비공감', '작성자',
                                '더보기', 'IP', '작성일', '신고', '스크랩',
                                '목록', '이전', '다음', '추천', '종목토론실', '네이버', 
                                '로그인', '검색', '댓글', 'Copyright', '©', 'Corp'
                            ]) and
                            not re.match(r'^\d{4}\.\d{2}\.\d{2}', line) and  # 날짜 형식 제외
                            not re.match(r'^\d+\.\d+\.\*\*\*\.\d+', line)):  # IP 주소 형식 제외
                            content_lines.append(line)
                    
                    if content_lines and len('\n'.join(content_lines)) > 5:
                        content = '\n'.join(content_lines)
                        logger.debug(f"summary 속성으로 본문 추출: {len(content)}자")
                        return content.strip()
        
        # 방법 2: 일반적인 본문 선택자들 시도
        # 방법 2: 일반적인 본문 선택자들 시도
        content_selectors = [
            '.view_text',
            'td.view_text', 
            '.board_view .view_text',
            'div.view_text',
            '.article_view .view_text'
        ]
        
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(strip=True, separator='\n')
                if content and len(content) > 10:
                    logger.debug(f"본문 추출 성공 (선택자: {selector}): {len(content)}자")
                    return content.strip()
        
        # 방법 3: 테이블 구조에서 본문 영역 찾기
        if not content:
            tables = soup.find_all('table')
            candidates = []
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    for cell in cells:
                        cell_text = cell.get_text(strip=True, separator='\n')
                        
                        # 본문 후보 조건
                        if (len(cell_text) > 5 and 
                            any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in cell_text) and
                            not any(nav_word in cell_text for nav_word in [
                                '이전글', '다음글', '목록', '추천', '신고', '스크랩',
                                '종목토론실', '네이버 금융', '로그인', '검색', '댓글'
                            ])):
                            
                            # 불필요한 텍스트 제거
                            lines = cell_text.split('\n')
                            content_lines = []
                            
                            for line in lines:
                                line = line.strip()
                                if (line and 
                                    len(line) > 1 and 
                                    not line.replace(',', '').replace('.', '').isdigit() and  # 숫자만 있는 라인 제외
                                    not any(word in line for word in [
                                        '목록', '이전', '다음', '추천', '신고', '스크랩',
                                        '종목토론실', '네이버', '로그인', '검색', '댓글',
                                        'Copyright', '©', 'Corp', 'All Rights Reserved'
                                    ])):
                                    content_lines.append(line)
                            
                            if content_lines:
                                clean_content = '\n'.join(content_lines)
                                # 한글 비율 계산
                                korean_chars = sum(1 for c in clean_content if 0xAC00 <= ord(c) <= 0xD7A3)
                                total_chars = len(clean_content.replace(' ', '').replace('\n', ''))
                                korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
                                
                                # 점수 계산 (한글 비율 * 길이)
                                score = korean_ratio * len(clean_content)
                                candidates.append((clean_content, score))
            
            # 가장 높은 점수의 후보 선택
            if candidates:
                best_content = max(candidates, key=lambda x: x[1])[0]
                if len(best_content) > 5:
                    logger.debug(f"테이블에서 본문 추출: {len(best_content)}자")
                    return best_content.strip()
        
        # 방법 4: 특정 속성을 가진 td 요소 찾기
        if not content:
            # 높이나 패딩이 있는 td (본문 영역일 가능성)
            content_tds = soup.find_all('td', attrs=lambda x: x and (
                'height' in x or 'style' in x
            ))
            
            for td in content_tds:
                if td.get('style') and ('padding' in td.get('style', '') or 'height' in td.get('style', '')):
                    td_text = td.get_text(strip=True, separator='\n')
                    if (len(td_text) > 5 and  # 길이 조건 완화
                        any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in td_text)):
                        
                        # 불필요한 텍스트 필터링
                        lines = [line.strip() for line in td_text.split('\n') if line.strip()]
                        filtered_lines = []
                        
                        for line in lines:
                            if (len(line) > 1 and  # 2자 이상의 라인
                                not any(word in line for word in [
                                    '목록', '이전글', '다음글', '추천', '신고', '스크랩',
                                    '종목토론실', '네이버 금융', '로그인', '검색'
                                ])):
                                filtered_lines.append(line)
                        
                        if filtered_lines and len('\n'.join(filtered_lines)) > 5:
                            content = '\n'.join(filtered_lines)
                            logger.debug(f"속성 기반 td에서 본문 추출: {len(content)}자")
                            return content.strip()
        
        # 방법 5: 가장 긴 텍스트 블록 찾기 (최후의 방법)
        if not content:
            all_tds = soup.find_all('td')
            best_content = ""
            best_score = 0
            
            for td in all_tds:
                td_text = td.get_text(strip=True, separator='\n')
                if (len(td_text) > 5 and 
                    any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in td_text) and
                    not any(nav_word in td_text[:50] for nav_word in [
                        '목록', '이전글', '다음글', '네이버 금융', '종목토론실'
                    ])):
                    
                    # 점수 계산 (한글 비율과 길이 고려)
                    korean_chars = sum(1 for c in td_text if 0xAC00 <= ord(c) <= 0xD7A3)
                    total_chars = len(td_text.replace(' ', '').replace('\n', ''))
                    korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
                    
                    # 숫자만 있는 텍스트 제외
                    if not td_text.replace(',', '').replace('.', '').isdigit():
                        score = korean_ratio * len(td_text)
                        
                        if score > best_score:
                            best_score = score
                            best_content = td_text
            
            if best_content:
                # 불필요한 텍스트 정리
                lines = [line.strip() for line in best_content.split('\n') if line.strip()]
                filtered_lines = []
                
                for line in lines:
                    if (len(line) > 1 and 
                        not line.replace(',', '').replace('.', '').isdigit() and  # 숫자만 있는 라인 제외
                        not any(word in line for word in [
                            '목록', '이전', '다음', '추천', '신고', '스크랩',
                            '종목토론실', '네이버', '로그인', '검색', '댓글'
                        ])):
                        filtered_lines.append(line)
                
                if filtered_lines:
                    content = '\n'.join(filtered_lines)
                    logger.debug(f"가장 적합한 텍스트 블록에서 본문 추출: {len(content)}자")
        
        return content.strip() if content else ""
        
    except Exception as e:
        logger.error(f"게시글 본문 크롤링 실패 {post_url}: {e}")
        return ""

def filter_by_date(df, start_date, end_date):
    """날짜 범위로 게시글 필터링"""
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        mask = (df['날짜'] >= start_date) & (df['날짜'] <= end_date)
        return df.loc[mask]
    return df

def create_post_key(row, include_title=False):
    """게시글의 고유 키 생성 (중복 체크용)"""
    # 날짜를 문자열로 변환 (DATETIME 형식 고려)
    if pd.isna(row['날짜']):
        date_str = "Unknown"
    elif isinstance(row['날짜'], datetime):
        date_str = row['날짜'].strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_str = str(row['날짜']).strip()
    
    author_str = str(row['작성자']).strip()
    
    if include_title:
        title_str = str(row['제목']).strip()
        return (date_str, author_str, title_str)
    else:
        return (date_str, author_str)

def parse_date(date_str):
    """네이버 종목토론실 날짜 형식 파싱"""
    try:
        date_str = date_str.strip()
        
        # "12.29" 형식 (같은 해)
        if re.match(r'^\d{2}\.\d{2}$', date_str):
            current_year = datetime.now().year
            month, day = date_str.split('.')
            return datetime(current_year, int(month), int(day))
        
        # "2024.12.29" 형식
        elif re.match(r'^\d{4}\.\d{2}\.\d{2}$', date_str):
            year, month, day = date_str.split('.')
            return datetime(int(year), int(month), int(day))
        
        # "12/29" 형식
        elif re.match(r'^\d{2}/\d{2}$', date_str):
            current_year = datetime.now().year
            month, day = date_str.split('/')
            return datetime(current_year, int(month), int(day))
        
        # "어제", "오늘" 등의 상대적 날짜
        elif date_str == '오늘':
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str == '어제':
            return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 기본적으로 pandas의 to_datetime 사용
        else:
            return pd.to_datetime(date_str, errors='coerce')
            
    except Exception as e:
        logger.warning(f"날짜 파싱 실패: {date_str}, 오류: {e}")
        return None


if __name__ == "__main__":
    # 테스트용 코드
    logging.basicConfig(level=logging.INFO)
    
    url = "https://finance.naver.com/item/board_read.naver?code=139480&nid=305317830&st=&sw=&page=1"
    print(f"크롤링 URL: {url}")
    
    contents = get_post_content(url)
    print("게시글 본문 내용:")
    print("=" * 50)
    print(contents)
    print("=" * 50)
    print(f"본문 길이: {len(contents)}자")
