#!/usr/bin/env python3
"""
통합 README 관리자 (Unified README Manager)

이 모듈은 README.md 파일의 생성, 업데이트, 관리를 담당합니다.
모든 README 관련 작업을 이 하나의 모듈에서 처리합니다.

주요 기능:
- README.md 파일 생성
- 날짜 경로 자동 업데이트
- 템플릿 관리
- 에러 처리 및 복구

사용법:
    from readme_manager import ReadmeManager
    
    manager = ReadmeManager()
    manager.ensure_readme_updated()  # 자동 생성/업데이트
"""

import os
import re
from datetime import datetime, timedelta, timezone

class ReadmeManager:
    """README.md 파일 통합 관리 클래스"""
    
    def __init__(self, readme_path='README.md', generate_dir='generate'):
        self.readme_path = readme_path
        self.generate_dir = generate_dir

    def get_latest_date_folder(self, custom_date=None):
        """generate 폴더에서 최신 날짜 폴더 찾기"""
        
        if custom_date == None:
            # 현재 날짜를 기본값으로 사용
            latest_date = datetime.now().strftime('%Y%m%d')
        else:
            # 사용자 지정 날짜가 주어진 경우 해당 날짜를 사용
            latest_date = custom_date
        
        if os.path.exists(self.generate_dir):
            date_folders = []
            for item in os.listdir(self.generate_dir):
                item_path = os.path.join(self.generate_dir, item)
                if os.path.isdir(item_path) and item.isdigit() and len(item) == 8:
                    date_folders.append(item)
            
            if date_folders:
                latest_date = max(date_folders)
        
        return latest_date
    
    def get_kst_now(self):
        """한국 시간(KST) datetime 반환"""
        return datetime.utcnow() + timedelta(hours=9)

    def create_readme_template(self, date_folder):
        """README.md 템플릿 생성"""
        
        current_time = self.get_kst_now().strftime('%Y-%m-%d %H:%M')
        
        # 날짜를 YYYY-MM-DD 형식으로 변환
        formatted_date = f"{date_folder[:4]}-{date_folder[4:6]}-{date_folder[6:8]}"
        
        template = f"""# 📈 Stock Sentiment Analysis Reports

*Last Updated: {current_time}*

주식 게시글 감정 분석 및 패턴 분석 리포트

## 📅 보고서 갱신 현황

| 보고서 타입 | 최근 갱신일 | 상태 |
|------------|------------|------|
| 🌅 장시작 전 리포트 | {formatted_date} | ✅ 최신 |
| 🌆 장마감 후 리포트 | {formatted_date} | ✅ 최신 |
| 📅 주간 리포트 | {formatted_date} | ✅ 최신 |
| 📆 월간 리포트 | {formatted_date} | ✅ 최신 |
| 📊 종합 패턴 분석 | {formatted_date} | ✅ 최신 |


---

## 🌅 장시작 전 리포트 (Pre-Market Analysis)
*전일 활동 분석 및 새벽 시간대 감정 변화*

![Pre-Market Report](./generate/{date_folder}/pre_market_report_{date_folder}.png)

---

## 🌆 장마감 후 리포트 (Post-Market Analysis)
*당일 장시간 활동 분석 및 감정 트렌드*

![Post-Market Report](./generate/{date_folder}/post_market_report_{date_folder}.png)

---

## 📅 주간 리포트 (Weekly Analysis)
*지난 7일 종합 분석 및 요일별 패턴*

![Weekly Report](./generate/{date_folder}/weekly_report_{date_folder}.png)

---

## 📆 월간 리포트 (Monthly Analysis)
*월간 종합 분석 및 트렌드*

![Monthly Report](./generate/{date_folder}/monthly_report_{date_folder}.png)

---

## 📊 종합 패턴 분석 (Pattern Analysis)
*시간대별/요일별 활동 패턴*

![Pattern Analysis](./generate/{date_folder}/pattern_analysis_all_{date_folder}.png)

---

## 📋 리포트 설명

| 리포트 타입 | 생성 주기 | 주요 내용 |
|------------|----------|-----------|
| 🌅 장시작 전 | 매일 아침 | 전일 활동, 새벽 감정 변화, 장외시간 분석 |
| 🌆 장마감 후 | 매일 저녁 | 당일 장시간 활동, 시간대별 감정 트렌드 |
| 📅 주간 | 매주 일요일 | 7일 종합 분석, 요일별 패턴 |
| 📆 월간 | 매월 1일 | 월간 트렌드, 감정 변동성 분석 |
| 📊 패턴 분석 | 요청 시 | 시간대/요일별 활동 패턴 종합 |

---
"""
        return template
    
    def create_readme(self, custom_date=None, new_files=None):
        """새 README.md 파일 생성 (new_files가 있으면 해당 파일만 반영)"""
        
        try:
            if custom_date:
                # custom_date가 datetime 객체라면 문자열로 변환
                if isinstance(custom_date, datetime):
                    date_folder = custom_date.strftime('%Y%m%d')
                else:
                    # custom_date가 'YYYY-MM-DD' 형식이면 'YYYYMMDD'로 변환
                    if isinstance(custom_date, str) and len(custom_date) == 10 and custom_date[4] == '-' and custom_date[7] == '-':
                        date_folder = custom_date.replace('-', '')
                    else:
                        date_folder = str(custom_date)
            else:
                date_folder = self.get_latest_date_folder(custom_date=custom_date)
            
            template = self.create_readme_template(date_folder)
            
            # 기존 README가 있으면, new_files에 없는 섹션은 기존 README에서 이미지 링크를 복사
            if new_files and os.path.exists(self.readme_path):
                with open(self.readme_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                    
                sections = [
                    ('Pre-Market Report', 'pre_market'),
                    ('Post-Market Report', 'post_market'),
                    ('Weekly Report', 'weekly'),
                    ('Monthly Report', 'monthly'),
                    ('Pattern Analysis', 'pattern_analysis')
                ]
                
                for section, key in sections:
                    if not any(key in f for f in new_files):
                        # 기존 README에서 해당 섹션 이미지 링크 추출
                        pattern = rf'!\[{re.escape(section)}\]\([^)]+\)'
                        match = re.search(pattern, old_content)
                        if match:
                            template = re.sub(pattern, match.group(0), template)
                
                # new_files에 해당하는 섹션만 업데이트
                for file in new_files:
                    if 'pre_market' in file:
                        section = 'Pre-Market Report'
                    elif 'post_market' in file:
                        section = 'Post-Market Report'
                    elif 'weekly' in file:
                        section = 'Weekly Report'
                    elif 'monthly' in file:
                        section = 'Monthly Report'
                    elif 'pattern_analysis' in file:
                        section = 'Pattern Analysis'
                    else:
                        section = None
                    if section:
                        pattern = rf'!\[{re.escape(section)}\]\([^)]+\)'
                        new_img_path = f'./generate/{date_folder}/{file}'
                        template = re.sub(pattern, f'![{section}]({new_img_path})', template)
            
            with open(self.readme_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            print(f"📝 README.md created successfully with date: {date_folder}")
            return self.readme_path
            
        except Exception as e:
            print(f"❌ Failed to create README.md: {e}")
            return None

    def update_readme_dates(self, custom_date=None, new_files=None):
        """기존 README.md의 날짜 경로만 업데이트, new_files가 있으면 해당 파일만 반영"""
        
        if not os.path.exists(self.readme_path):
            print("📝 README.md not found, creating new one...")
            return self.create_readme(custom_date=custom_date, new_files=new_files)
        
        try:
            if custom_date:
                # custom_date가 datetime 객체라면 문자열로 변환
                if isinstance(custom_date, datetime):
                    latest_date = custom_date.strftime('%Y%m%d')
                else:
                    # custom_date가 'YYYY-MM-DD' 형식이면 'YYYYMMDD'로 변환
                    if isinstance(custom_date, str) and len(custom_date) == 10 and custom_date[4] == '-' and custom_date[7] == '-':
                        latest_date = custom_date.replace('-', '')
                    else:
                        latest_date = str(custom_date)
            else:
                # 현재 날짜를 기본값으로 사용
                latest_date = self.get_latest_date_folder()
            
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if new_files:
                # 신규 파일만 README에 반영
                for file in new_files:
                    # 파일명에서 타입 추출 (pre/post/weekly/monthly/pattern 등)
                    if 'pre_market' in file:
                        section = 'Pre-Market Report'
                    elif 'post_market' in file:
                        section = 'Post-Market Report'
                    elif 'weekly' in file:
                        section = 'Weekly Report'
                    elif 'monthly' in file:
                        section = 'Monthly Report'
                    elif 'pattern_analysis' in file:
                        section = 'Pattern Analysis'
                    else:
                        section = None
                    if section:
                        # 더 정확한 패턴으로 "## 📊 최신 리포트" 섹션 내의 이미지만 업데이트
                        # "📋 리포트 설명" 섹션은 건드리지 않음
                        section_start = content.find('## 📊 최신 리포트')
                        if section_start != -1:
                            # "📊 최신 리포트" 섹션부터 다음 ## 섹션까지만 처리
                            next_section = content.find('\n##', section_start + 1)
                            if next_section == -1:
                                section_content = content[section_start:]
                                remaining_content = ""
                            else:
                                section_content = content[section_start:next_section]
                                remaining_content = content[next_section:]
                            
                            # 해당 섹션 내에서만 이미지 교체
                            pattern = rf'!\[{re.escape(section)}\]\([^)]+\)'
                            new_img_path = f'./generate/{latest_date}/{file}'
                            updated_section = re.sub(pattern, f'![{section}]({new_img_path})', section_content)
                            
                            # 전체 content 재구성
                            content = content[:section_start] + updated_section + remaining_content
                        
                        # 보고서 갱신 현황 테이블도 업데이트
                        formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"
                        if 'pre_market' in file:
                            report_name = '🌅 장시작 전 리포트'
                        elif 'post_market' in file:
                            report_name = '🌆 장마감 후 리포트'
                        elif 'weekly' in file:
                            report_name = '📅 주간 리포트'
                        elif 'monthly' in file:
                            report_name = '📆 월간 리포트'
                        elif 'pattern_analysis' in file:
                            report_name = '📊 종합 패턴 분석'
                        else:
                            report_name = None
                        
                        if report_name:
                            # 테이블의 해당 행 업데이트 (더 간단한 패턴 사용)
                            table_pattern = rf'\| {re.escape(report_name)} \| [^|]+ \| [^|]+ \|'
                            replacement = f'| {report_name} | {formatted_date} | ✅ 최신 |'
                            content = re.sub(table_pattern, replacement, content)
                
                # 마지막 업데이트 시간 갱신
                current_time = self.get_kst_now().strftime('%Y-%m-%d %H:%M')
                content = re.sub(
                    r'\*Last Updated: [^*]+\*',
                    f'*Last Updated: {current_time}*',
                    content
                )
                
                with open(self.readme_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"🔄 README.md updated with new files: {new_files}")
                return self.readme_path
            
            # 기존 전체 날짜 일괄 변경 로직
            old_date_pattern = r'generate/\d{8}/'
            new_date_path = f'generate/{latest_date}/'
            updated_content = re.sub(old_date_pattern, new_date_path, content)

            # 파일명 내 날짜(8자리)도 최신 날짜로 변경
            old_filename_date_pattern = r'_(\d{8})\.png'
            updated_content = re.sub(old_filename_date_pattern, f'_{latest_date}.png', updated_content)
            
            # 마지막 업데이트 시간 갱신
            current_time = self.get_kst_now().strftime('%Y-%m-%d %H:%M')
            updated_content = re.sub(
                r'\*Last Updated: [^*]+\*',
                f'*Last Updated: {current_time}*',
                updated_content
            )
            
            with open(self.readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"🔄 README.md updated with latest date: {latest_date}")
            return self.readme_path
            
        except Exception as e:
            print(f"⚠️ Failed to update README.md: {e}")
            print("💡 Attempting to recreate README.md...")
            return self.create_readme(custom_date=custom_date, new_files=new_files)
    
    def ensure_readme_updated(self, custom_date=None, new_files=None):
        """README.md가 최신 상태인지 확인하고 필요시 생성/업데이트 (신규 파일만 반영 가능)"""
        
        try:
            if os.path.exists(self.readme_path):
                return self.update_readme_dates(custom_date=custom_date, new_files=new_files)
            else:
                return self.create_readme(custom_date=custom_date, new_files=new_files)

        except Exception as e:
            print(f"❌ README management failed: {e}")
            return None
    
    def get_readme_status(self):
        """README.md 상태 정보 반환"""
        
        status = {
            'exists': os.path.exists(self.readme_path),
            'size': 0,
            'modified': None,
            'latest_date': self.get_latest_date_folder()
        }
        
        if status['exists']:
            status['size'] = os.path.getsize(self.readme_path)
            mtime = os.path.getmtime(self.readme_path)
            status['modified'] = datetime.fromtimestamp(mtime)
        
        return status


# 메인 실행
if __name__ == "__main__":
    print("📝 README Manager")
    print("=" * 40)
    
    manager = ReadmeManager()
    
    # 상태 확인
    status = manager.get_readme_status()
    print(f"📁 README exists: {status['exists']}")
    print(f"📅 Latest date: {status['latest_date']}")
    
    if status['exists']:
        print(f"📊 File size: {status['size']:,} bytes")
        print(f"🕐 Modified: {manager.get_kst_now().strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    print()
    
    # README 업데이트/생성
    result = manager.ensure_readme_updated()
    
    if result:
        print("✅ README.md is now up to date!")
    else:
        print("❌ Failed to update README.md")
