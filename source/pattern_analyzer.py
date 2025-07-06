import pandas as pd
import matplotlib
matplotlib.use('Agg')  # GUI 없이 파일로만 저장
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime, timedelta
import numpy as np
import os
from database import get_db_connection
import warnings
warnings.filterwarnings('ignore')

# quick_readme 모듈의 auto_update 기능 import (선택적)
try:
    from readme_manager import ReadmeManager
    HAS_README_MANAGER = True
except ImportError:
    HAS_README_MANAGER = False
    print("Warning: readme_manager not found. README auto-update disabled.")


# seaborn 선택적 import
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    print("Warning: seaborn not installed. Some visualizations will use matplotlib only.")

class PatternAnalyzer:
    def __init__(self, auto_update_readme=True):
        self.connection = get_db_connection()
        self.auto_update_readme = auto_update_readme
        self._readme_manager = ReadmeManager() if HAS_README_MANAGER else None
    
    def _create_output_directory(self, date_for_dir=None):
        """출력 디렉토리 생성 (date_for_dir: datetime 또는 str, 없으면 오늘)"""
        if date_for_dir is None:
            today = datetime.now().strftime('%Y%m%d')
        else:
            if isinstance(date_for_dir, str):
                today = date_for_dir.replace('-', '')
            elif isinstance(date_for_dir, datetime):
                today = date_for_dir.strftime('%Y%m%d')
            else:
                today = str(date_for_dir)
        output_dir = os.path.join('generate', today)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def analyze_temporal_patterns(self, stock_code=None, target_date=None):
        """시간적 패턴 분석"""
        
        # 기본 쿼리
        base_query = """
        SELECT 
            sp.date,
            sp.stock_code,
            pa.sentiment_score,
            pa.sentiment_label,
            pa.bullish_bearish,
            HOUR(sp.date) as hour_of_day,
            DAYOFWEEK(sp.date) as day_of_week,
            DAYNAME(sp.date) as day_name
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE sp.date IS NOT NULL
        """
        
        if stock_code:
            base_query += f" AND sp.stock_code = '{stock_code}'"
            
        df = pd.read_sql(base_query, self.connection)
        df['date'] = pd.to_datetime(df['date'])
        
        return self._generate_temporal_reports(df, stock_code, target_date)
    
    def _generate_temporal_reports(self, df, stock_code=None, target_date=None):
        """시간적 패턴 리포트 생성"""
        
        results = {}
        
        # 1. 시간대별 패턴
        hourly_pattern = df.groupby('hour_of_day').agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        # 2. 요일별 패턴
        daily_pattern = df.groupby(['day_of_week', 'day_name']).agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        # 3. 장시간 vs 장외시간
        df['market_session'] = df['hour_of_day'].apply(
            lambda x: 'Market Hours' if 9 <= x <= 15 else 'After Hours'
        )
        
        session_pattern = df.groupby('market_session').agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        results['hourly'] = hourly_pattern
        results['daily'] = daily_pattern
        results['session'] = session_pattern
        
        # 시각화
        output_dir = self._create_output_directory(target_date)
        generated_file = self._plot_patterns(df, stock_code, output_dir)

        # README 업데이트 (실제 생성된 파일만 반영)
        if generated_file:
            self._ensure_readme_updated(target_date, new_files=[generated_file])
        
        return results
    
    def _plot_patterns(self, df, stock_code=None, output_dir=None):
        """패턴 시각화"""
        
        title_suffix = f" - {stock_code}" if stock_code else ""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Post Pattern Analysis{title_suffix}', fontsize=16)
        
        # 1. 시간대별 게시글 수
        hourly_counts = df.groupby('hour_of_day').size()
        axes[0, 0].bar(hourly_counts.index, hourly_counts.values)
        axes[0, 0].set_title('Posts by Hour')
        axes[0, 0].set_xlabel('Hour of Day')
        axes[0, 0].set_ylabel('Number of Posts')
        
        # 2. 시간대별 감정 점수
        hourly_sentiment = df.groupby('hour_of_day')['sentiment_score'].mean()
        axes[0, 1].plot(hourly_sentiment.index, hourly_sentiment.values, marker='o')
        axes[0, 1].set_title('Average Sentiment by Hour')
        axes[0, 1].set_xlabel('Hour of Day')
        axes[0, 1].set_ylabel('Sentiment Score')
        axes[0, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        # 3. 요일별 게시글 수
        daily_counts = df.groupby('day_name').size()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_counts = daily_counts.reindex([day for day in day_order if day in daily_counts.index])
        
        axes[1, 0].bar(range(len(daily_counts)), daily_counts.values)
        axes[1, 0].set_title('Posts by Day of Week')
        axes[1, 0].set_xlabel('Day of Week')
        axes[1, 0].set_ylabel('Number of Posts')
        axes[1, 0].set_xticks(range(len(daily_counts)))
        axes[1, 0].set_xticklabels([day[:3] for day in daily_counts.index], rotation=45)
        
        # 4. 감정 분포
        sentiment_counts = df['sentiment_label'].value_counts()
        axes[1, 1].pie(sentiment_counts.values, labels=sentiment_counts.index, autopct='%1.1f%%')
        axes[1, 1].set_title('Sentiment Distribution')
        
        plt.tight_layout()
        
        if output_dir is None:
            output_dir = self._create_output_directory()

        # 파일명 저장 날짜를 output_dir 기준 폴더명(YYYYMMDD)으로 맞춤
        folder_date = os.path.basename(output_dir)

        filename = f"pattern_analysis_{stock_code}_{folder_date}.png" if stock_code else f"pattern_analysis_all_{folder_date}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Chart saved: {filepath}")
        return filename
    
    def _on_chart_saved(self, filepath):
        """차트 저장 후 호출되는 콜백"""
        self._chart_generated = True
        print(f"📊 Chart saved: {filepath}")
        
        # 자동 README 업데이트가 활성화되어 있으면 업데이트
        if self.auto_update_readme:
            self._auto_update_readme_if_needed()
    
    def _auto_update_readme_if_needed(self):
        """필요시 README 자동 업데이트"""
        if self._chart_generated:
            try:
                self.update_readme_with_latest_files()
                self._chart_generated = False  # 플래그 리셋
            except Exception as e:
                print(f"⚠️ Auto README update failed: {e}")

    def analyze_correlation_patterns(self, stock_code=None):
        """상관관계 패턴 분석"""
        
        query = """
        SELECT 
            sp.date,
            sp.stock_code,
            sp.views,
            sp.likes,
            sp.dislikes,
            pa.sentiment_score,
            pa.confidence_score,
            pa.bullish_bearish,
            COUNT(*) OVER (PARTITION BY sp.stock_code, DATE(sp.date)) as daily_post_count
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE sp.date IS NOT NULL
        """
        
        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"
            
        df = pd.read_sql(query, self.connection)
        
        # 숫자형 컬럼만 선택하여 상관관계 분석
        numeric_cols = ['sentiment_score', 'confidence_score', 'daily_post_count']
        
        # views, likes, dislikes를 숫자로 변환 (가능한 경우)
        for col in ['views', 'likes', 'dislikes']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if not df[col].isna().all():
                numeric_cols.append(col)
        
        correlation_matrix = df[numeric_cols].corr()
        
        # # 상관관계 히트맵
        # plt.figure(figsize=(10, 8))
        # if HAS_SEABORN:
        #     sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
        # else:
        #     # seaborn이 없을 경우 matplotlib로 대체
        #     im = plt.imshow(correlation_matrix, cmap='coolwarm', aspect='auto')
        #     plt.colorbar(im)
            
        #     # 값 표시
        #     for i in range(len(correlation_matrix)):
        #         for j in range(len(correlation_matrix.columns)):
        #             plt.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}', 
        #                    ha='center', va='center')
            
        #     plt.xticks(range(len(correlation_matrix.columns)), correlation_matrix.columns, rotation=45)
        #     plt.yticks(range(len(correlation_matrix.index)), correlation_matrix.index)
            
        # plt.title(f'Correlation Analysis{" - " + stock_code if stock_code else ""}')
        # plt.tight_layout()
        # plt.show()
        
        return correlation_matrix
    
    def analyze_keyword_trends(self, stock_code=None, top_n=20):
        """키워드 트렌드 분석"""
        
        query = """
        SELECT 
            sp.date,
            sp.stock_code,
            pa.keywords,
            pa.sentiment_score
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE pa.keywords IS NOT NULL
        """
        
        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"
            
        df = pd.read_sql(query, self.connection)
        
        # JSON 키워드 파싱 및 분석
        # 이 부분은 실제 키워드 JSON 구조에 따라 수정 필요
        
        return df

    def generate_summary_report(self, stock_code=None, target_date=None):
        """종합 분석 리포트 생성"""
        
        print(f"=== Post Pattern Analysis Report{' - ' + stock_code if stock_code else ''} ===\n")
        
        # 시간적 패턴 분석
        temporal_results = self.analyze_temporal_patterns(stock_code, target_date=target_date)

        print("1. Hourly Patterns:")
        print(temporal_results['hourly'])
        print("\n2. Daily Patterns:")
        print(temporal_results['daily'])
        print("\n3. Market Hours vs After Hours:")
        print(temporal_results['session'])
        
        # 상관관계 분석
        print("\n4. Correlation Analysis:")
        correlation_results = self.analyze_correlation_patterns(stock_code)
        print(correlation_results)
        
        return {
            'temporal': temporal_results,
            'correlation': correlation_results
        }
    
    def generate_pre_market_report(self, stock_code=None, target_date=None):
        """장시작 전 리포트 (최근 평일 16시~오늘 9시까지 분석)"""
        # target_date를 오늘로 간주
        if target_date is None:
            print("⚠️ target_date를 지정해야 장시작 전 리포트가 생성됩니다.")
            return None
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        today_date = target_date.date()

        # 최근 평일(월~금) 찾기 (target_date가 평일이면 그날, 아니면 가장 가까운 이전 평일)
        weekday = target_date.weekday()  # 월:0 ~ 일:6
        if weekday >= 5:  # 토/일
            # 가장 가까운 이전 금요일
            days_to_friday = weekday - 4
            base_date = target_date - timedelta(days=days_to_friday)
        else:
            base_date = target_date
        base_date_only = base_date.date()

        # 분석 구간: base_date(평일) 16:00 ~ target_date 09:00
        start_dt = datetime.combine(base_date_only, datetime.min.time()) + timedelta(hours=16)
        end_dt = datetime.combine(today_date, datetime.min.time()) + timedelta(hours=9)
        if start_dt > end_dt:
            start_dt = start_dt - timedelta(days=1)

        print(f"=== 📈 Pre-Market Analysis Report{' - ' + stock_code if stock_code else ''} ===")
        print(f"분석 구간: {start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"Generated at: {target_date.strftime('%Y-%m-%d 09:00:00')}")
        print("=" * 60)

        # 쿼리: 해당 구간의 글만 추출
        query = f"""
        SELECT 
            sp.date,
            sp.stock_code,
            pa.sentiment_score,
            pa.sentiment_label,
            pa.bullish_bearish,
            HOUR(sp.date) as hour_of_day
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE sp.date >= '{start_dt.strftime('%Y-%m-%d %H:%M:%S')}'
          AND sp.date <= '{end_dt.strftime('%Y-%m-%d %H:%M:%S')}'
        """
        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"

        df = pd.read_sql(query, self.connection)

        if df.empty:
            print("⚠️  No data available for the specified pre-market period.")
            return None

        # 요약 통계
        total_posts = len(df)
        avg_sentiment = df['sentiment_score'].mean()
        bullish_ratio = (df['bullish_bearish'] == 'bullish').mean()
        after_hours = df[df['hour_of_day'] >= 16]
        early_morning = df[df['hour_of_day'] <= 8]

        print(f"\n📊 Pre-Market Summary:")
        print(f"   • Total Posts: {total_posts}")
        print(f"   • Average Sentiment: {avg_sentiment:.4f}")
        print(f"   • Bullish Ratio: {bullish_ratio:.2%}")
        print(f"   • After Hours Posts (16~23시): {len(after_hours)}")
        print(f"   • Early Morning Posts (0~8시): {len(early_morning)}")

        # 감정 분포
        sentiment_dist = df['sentiment_label'].value_counts()
        print(f"\n🎯 Sentiment Distribution:")
        for sentiment, count in sentiment_dist.items():
            print(f"   • {sentiment.capitalize()}: {count} ({count/total_posts:.1%})")

        # 시각화
        output_dir = self._create_output_directory(target_date)
        generated_file = self._plot_pre_market_patterns(after_hours, early_morning, stock_code, output_dir=output_dir)

        # README 업데이트 (실제 생성된 파일만 반영)
        if generated_file:
            self._ensure_readme_updated(target_date, new_files=[generated_file])

        return {
            'pre_market_summary': {
                'total_posts': total_posts,
                'avg_sentiment': avg_sentiment,
                'bullish_ratio': bullish_ratio,
                'after_hours_posts': len(after_hours),
                'early_morning_posts': len(early_morning)
            }
        }
    
    def generate_post_market_report(self, stock_code=None, target_date=None):
        """장마감 후 리포트 (당일 또는 특정 날짜 장시간 분석)"""
        if target_date is None:
            print("⚠️ target_date를 지정해야 장마감 후 리포트가 생성됩니다.")
            return None
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        report_date = target_date.strftime('%Y-%m-%d')
        date_desc = f" ({report_date})"

        print(f"=== 📉 Post-Market Analysis Report{' - ' + stock_code if stock_code else ''}{date_desc} ===")
        print(f"Generated at: {target_date.strftime('%Y-%m-%d 15:30:00')}")
        print("=" * 60)

        # 대상 날짜 장시간 데이터 분석
        today = report_date

        query = f"""
        SELECT 
            sp.date,
            sp.stock_code,
            pa.sentiment_score,
            pa.sentiment_label,
            pa.bullish_bearish,
            HOUR(sp.date) as hour_of_day
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE DATE(sp.date) = '{today}' AND HOUR(sp.date) BETWEEN 9 AND 15
        """

        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"

        df = pd.read_sql(query, self.connection)

        if df.empty:
            print(f"⚠️  No trading hours data available for {report_date}.")
            return None

        # 장시간 요약 통계
        total_posts = len(df)
        avg_sentiment = df['sentiment_score'].mean()
        bullish_ratio = (df['bullish_bearish'] == 'bullish').mean()

        # 시간대별 분석
        hourly_stats = df.groupby('hour_of_day').agg({
            'sentiment_score': ['count', 'mean'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)

        print(f"\n📈 Trading Hours Summary ({report_date}):")
        print(f"   • Total Posts: {total_posts}")
        print(f"   • Average Sentiment: {avg_sentiment:.4f}")
        print(f"   • Bullish Ratio: {bullish_ratio:.2%}")

        # 가장 활발한 시간대
        peak_hour = df.groupby('hour_of_day').size().idxmax()
        peak_posts = df.groupby('hour_of_day').size().max()

        print(f"\n⏰ Peak Activity:")
        print(f"   • Peak Hour: {peak_hour}:00")
        print(f"   • Posts in Peak Hour: {peak_posts}")

        # 감정 변화 추이
        hourly_sentiment = df.groupby('hour_of_day')['sentiment_score'].mean()
        sentiment_trend = "📈 Improving" if hourly_sentiment.iloc[-1] > hourly_sentiment.iloc[0] else "📉 Declining"

        print(f"\n💭 Sentiment Trend: {sentiment_trend}")
        print(f"   • 9AM Sentiment: {hourly_sentiment.iloc[0]:.4f}")
        print(f"   • 3PM Sentiment: {hourly_sentiment.iloc[-1]:.4f}")

        # 시간대별 상세 분석
        print(f"\n⏱️  Hourly Breakdown:")
        for hour in range(9, 16):
            if hour in hourly_stats.index:
                posts = int(hourly_stats.loc[hour, ('sentiment_score', 'count')])
                sentiment = hourly_stats.loc[hour, ('sentiment_score', 'mean')]
                bullish = hourly_stats.loc[hour, ('bullish_bearish', '<lambda>')]
                print(f"   • {hour}:00-{hour+1}:00 | Posts: {posts:3d} | Sentiment: {sentiment:6.3f} | Bullish: {bullish:.1%}")

        # 시각화
        output_dir = self._create_output_directory(target_date)
        generated_file = self._plot_post_market_patterns(df, stock_code, output_dir=output_dir)

        # README 업데이트 (실제 생성된 파일만 반영)
        if generated_file:
            self._ensure_readme_updated(target_date, new_files=[generated_file])

        return {
            'trading_hours_summary': {
                'total_posts': total_posts,
                'avg_sentiment': avg_sentiment,
                'bullish_ratio': bullish_ratio,
                'peak_hour': peak_hour
            },
            'hourly_breakdown': hourly_stats
        }
    
    def generate_weekly_report(self, stock_code=None, target_date=None):
        """주간 리포트 (지난 7일 종합 분석)"""

        if target_date is None:
            print("⚠️ target_date를 지정해야 주간 리포트가 생성됩니다.")
            return None
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')

        report_date = target_date.strftime('%Y-%m-%d')
        date_desc = f" ({report_date})"
        
        print(f"=== 📅 Weekly Analysis Report{' - ' + stock_code if stock_code else ''}{date_desc} ===")
        print(f"Generated at: {target_date.strftime('%Y-%m-%d 24:00:00')}")
        print("=" * 60)
        
        # 지난 7일 데이터 분석
        end_date = target_date
        start_date = end_date - timedelta(days=7)
        
        query = f"""
        SELECT 
            sp.date,
            sp.stock_code,
            pa.sentiment_score,
            pa.sentiment_label,
            pa.bullish_bearish,
            DAYNAME(sp.date) as day_name,
            HOUR(sp.date) as hour_of_day
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE sp.date >= '{start_date.strftime('%Y-%m-%d')}'
        AND sp.date <= '{end_date.strftime('%Y-%m-%d')}'
        """
        
        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"
            
        df = pd.read_sql(query, self.connection)
        
        if df.empty:
            print("⚠️  No data available for the past week.")
            return None
        
        # 주간 요약 통계
        total_posts = len(df)
        avg_sentiment = df['sentiment_score'].mean()
        bullish_ratio = (df['bullish_bearish'] == 'bullish').mean()
        
        print(f"\n📊 Weekly Summary ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}):")
        print(f"   • Total Posts: {total_posts}")
        print(f"   • Average Sentiment: {avg_sentiment:.4f}")
        print(f"   • Bullish Ratio: {bullish_ratio:.2%}")
        
        # 요일별 분석
        daily_stats = df.groupby('day_name').agg({
            'sentiment_score': ['count', 'mean'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        # 요일 순서 정렬
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_stats = daily_stats.reindex([day for day in day_order if day in daily_stats.index])
        
        print(f"\n📅 Daily Breakdown:")
        for day in daily_stats.index:
            posts = int(daily_stats.loc[day, ('sentiment_score', 'count')])
            sentiment = daily_stats.loc[day, ('sentiment_score', 'mean')]
            bullish = daily_stats.loc[day, ('bullish_bearish', '<lambda>')]
            print(f"   • {day[:3]}: Posts: {posts:3d} | Sentiment: {sentiment:6.3f} | Bullish: {bullish:.1%}")
        
        # 가장 활발한 요일
        most_active_day = daily_stats[('sentiment_score', 'count')].idxmax()
        most_posts = daily_stats.loc[most_active_day, ('sentiment_score', 'count')]
        
        print(f"\n🔥 Most Active Day: {most_active_day} ({int(most_posts)} posts)")
        
        # 장시간 vs 장외시간 비교
        df['market_session'] = df['hour_of_day'].apply(
            lambda x: 'Market Hours' if 9 <= x <= 15 else 'After Hours'
        )
        
        session_stats = df.groupby('market_session').agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        print(f"\n🕐 Session Comparison:")
        for session in session_stats.index:
            posts = int(session_stats.loc[session, ('sentiment_score', 'count')])
            sentiment = session_stats.loc[session, ('sentiment_score', 'mean')]
            bullish = session_stats.loc[session, ('bullish_bearish', '<lambda>')]
            print(f"   • {session}: Posts: {posts:3d} | Sentiment: {sentiment:6.3f} | Bullish: {bullish:.1%}")
        
        # 감정 트렌드 분석
        daily_sentiment = df.groupby(df['date'].dt.date)['sentiment_score'].mean()
        if len(daily_sentiment) > 1:
            trend = "📈 Improving" if daily_sentiment.iloc[-1] > daily_sentiment.iloc[0] else "📉 Declining"
            print(f"\n📈 Weekly Sentiment Trend: {trend}")
            print(f"   • Start of Week: {daily_sentiment.iloc[0]:.4f}")
            print(f"   • End of Week: {daily_sentiment.iloc[-1]:.4f}")
        
        # 시각화
        output_dir = self._create_output_directory(target_date)
        generated_file = self._plot_weekly_patterns(df, stock_code, output_dir=output_dir)

        # README 업데이트 (실제 생성된 파일만 반영)
        if generated_file:
            self._ensure_readme_updated(target_date, new_files=[generated_file])
        
        return {
            'weekly_summary': {
                'total_posts': total_posts,
                'avg_sentiment': avg_sentiment,
                'bullish_ratio': bullish_ratio,
                'most_active_day': most_active_day
            },
            'daily_breakdown': daily_stats,
            'session_comparison': session_stats
        }
    
    def generate_monthly_report(self, stock_code=None, target_date=None):
        """월간 리포트 (지난 30일 또는 특정 월 종합 분석)"""
        
        # 대상 날짜 설정
        if target_date:
            if isinstance(target_date, str):
                # 날짜 문자열 포맷에 따라 분기 처리
                if len(target_date) == 7:  # 'YYYY-MM'
                    target_date = datetime.strptime(target_date, '%Y-%m')
                elif len(target_date) == 10:  # 'YYYY-MM-DD'
                    target_date = datetime.strptime(target_date, '%Y-%m-%d')
                else:
                    raise ValueError("target_date 문자열 포맷이 올바르지 않습니다. (YYYY-MM 또는 YYYY-MM-DD)")
            # 해당 월의 첫째 날과 마지막 날
            start_date = target_date.replace(day=1)
            if target_date.month == 12:
                end_date = target_date.replace(year=target_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)
            period_desc = f"{target_date.strftime('%Y년 %m월')}"
        else:
            # 지난 30일
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            period_desc = "Last 30 Days"
        
        print(f"=== 📆 Monthly Analysis Report{' - ' + stock_code if stock_code else ''} ===")
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Period: {period_desc} ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})")
        print("=" * 70)
        
        # 월간 데이터 분석
        query = f"""
        SELECT 
            sp.date,
            sp.stock_code,
            pa.sentiment_score,
            pa.sentiment_label,
            pa.bullish_bearish,
            DAYNAME(sp.date) as day_name,
            WEEK(sp.date) as week_number,
            DAY(sp.date) as day_of_month,
            HOUR(sp.date) as hour_of_day
        FROM stock_posts sp
        JOIN post_analysis pa ON sp.id = pa.post_id
        WHERE sp.date >= '{start_date.strftime('%Y-%m-%d')}'
        AND sp.date <= '{end_date.strftime('%Y-%m-%d')}'
        """
        
        if stock_code:
            query += f" AND sp.stock_code = '{stock_code}'"
            
        df = pd.read_sql(query, self.connection)
        
        if df.empty:
            print("⚠️  No data available for the specified period.")
            return None
        
        # 월간 요약 통계
        total_posts = len(df)
        avg_sentiment = df['sentiment_score'].mean()
        bullish_ratio = (df['bullish_bearish'] == 'bullish').mean()
        bearish_ratio = (df['bullish_bearish'] == 'bearish').mean()
        neutral_ratio = (df['bullish_bearish'] == 'neutral').mean()
        
        # 주별 분석
        df['week_start'] = df['date'].dt.to_period('W').dt.start_time
        weekly_stats = df.groupby('week_start').agg({
            'sentiment_score': ['count', 'mean'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        # 요일별 종합 분석
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_comprehensive = df.groupby('day_name').agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        daily_comprehensive = daily_comprehensive.reindex([day for day in day_order if day in daily_comprehensive.index])
        
        # 장시간 vs 장외시간 월간 비교
        df['market_session'] = df['hour_of_day'].apply(
            lambda x: 'Market Hours' if 9 <= x <= 15 else 'After Hours'
        )
        
        session_comprehensive = df.groupby('market_session').agg({
            'sentiment_score': ['count', 'mean', 'std'],
            'bullish_bearish': lambda x: (x == 'bullish').mean()
        }).round(4)
        
        print(f"\n📊 Monthly Summary:")
        print(f"   • Total Posts: {total_posts:,}")
        print(f"   • Average Sentiment: {avg_sentiment:.4f}")
        print(f"   • Bullish Ratio: {bullish_ratio:.2%}")
        print(f"   • Bearish Ratio: {bearish_ratio:.2%}")
        print(f"   • Neutral Ratio: {neutral_ratio:.2%}")
        print(f"   • Daily Average: {total_posts / ((end_date - start_date).days + 1):.1f} posts/day")
        
        # 주별 트렌드
        print(f"\n📈 Weekly Trends:")
        for week_start in weekly_stats.index:
            posts = int(weekly_stats.loc[week_start, ('sentiment_score', 'count')])
            sentiment = weekly_stats.loc[week_start, ('sentiment_score', 'mean')]
            bullish = weekly_stats.loc[week_start, ('bullish_bearish', '<lambda>')]
            week_end = week_start + timedelta(days=6)
            print(f"   • {week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}: Posts: {posts:4d} | Sentiment: {sentiment:6.3f} | Bullish: {bullish:.1%}")
        
        # 요일별 종합 분석
        print(f"\n📅 Daily Patterns (전체 기간 평균):")
        for day in daily_comprehensive.index:
            posts = int(daily_comprehensive.loc[day, ('sentiment_score', 'count')])
            sentiment = daily_comprehensive.loc[day, ('sentiment_score', 'mean')]
            std_dev = daily_comprehensive.loc[day, ('sentiment_score', 'std')]
            bullish = daily_comprehensive.loc[day, ('bullish_bearish', '<lambda>')]
            avg_daily = posts / len(weekly_stats)  # 주 수로 나누어 일평균 계산
            print(f"   • {day[:3]}: 총 {posts:3d}개 (주평균 {avg_daily:.1f}개) | Sentiment: {sentiment:6.3f}±{std_dev:.3f} | Bullish: {bullish:.1%}")
        
        # 가장 활발했던 주와 조용했던 주
        most_active_week = weekly_stats[('sentiment_score', 'count')].idxmax()
        least_active_week = weekly_stats[('sentiment_score', 'count')].idxmin()
        most_posts = weekly_stats.loc[most_active_week, ('sentiment_score', 'count')]
        least_posts = weekly_stats.loc[least_active_week, ('sentiment_score', 'count')]
        
        print(f"\n🔥 Activity Extremes:")
        print(f"   • Most Active Week: {most_active_week.strftime('%m/%d')} ({int(most_posts)} posts)")
        print(f"   • Least Active Week: {least_active_week.strftime('%m/%d')} ({int(least_posts)} posts)")
        
        # 장시간 vs 장외시간 비교
        print(f"\n🕐 Session Analysis:")
        for session in session_comprehensive.index:
            posts = int(session_comprehensive.loc[session, ('sentiment_score', 'count')])
            sentiment = session_comprehensive.loc[session, ('sentiment_score', 'mean')]
            std_dev = session_comprehensive.loc[session, ('sentiment_score', 'std')]
            bullish = session_comprehensive.loc[session, ('bullish_bearish', '<lambda>')]
            ratio = posts / total_posts
            print(f"   • {session}: {posts:4d}개 ({ratio:.1%}) | Sentiment: {sentiment:6.3f}±{std_dev:.3f} | Bullish: {bullish:.1%}")
        
        # 감정 변동성 분석
        sentiment_volatility = df['sentiment_score'].std()
        daily_sentiment_avg = df.groupby(df['date'].dt.date)['sentiment_score'].mean()
        
        if len(daily_sentiment_avg) > 1:
            overall_trend = "📈 Improving" if daily_sentiment_avg.iloc[-1] > daily_sentiment_avg.iloc[0] else "📉 Declining"
            trend_change = daily_sentiment_avg.iloc[-1] - daily_sentiment_avg.iloc[0]
            print(f"\n📊 Sentiment Analysis:")
            print(f"   • Overall Trend: {overall_trend} ({trend_change:+.4f})")
            print(f"   • Sentiment Volatility: {sentiment_volatility:.4f}")
            print(f"   • Highest Daily Avg: {daily_sentiment_avg.max():.4f}")
            print(f"   • Lowest Daily Avg: {daily_sentiment_avg.min():.4f}")
        
        # 시간대별 활동 패턴
        hourly_activity = df.groupby('hour_of_day').size()
        peak_hour = hourly_activity.idxmax()
        quiet_hour = hourly_activity.idxmin()
        
        print(f"\n⏰ Activity Patterns:")
        print(f"   • Peak Hour: {peak_hour}:00 ({hourly_activity[peak_hour]} posts)")
        print(f"   • Quiet Hour: {quiet_hour}:00 ({hourly_activity[quiet_hour]} posts)")
        print(f"   • Market Hours Activity: {(df['market_session'] == 'Market Hours').mean():.1%}")
        
        # 월말 vs 월초 비교 (30일 이상 데이터가 있는 경우)
        if (end_date - start_date).days >= 29:
            df['period_section'] = df['day_of_month'].apply(
                lambda x: 'Month Start' if x <= 10 else 'Month End' if x >= 21 else 'Month Middle'
            )
            
            section_stats = df.groupby('period_section').agg({
                'sentiment_score': ['count', 'mean'],
                'bullish_bearish': lambda x: (x == 'bullish').mean()
            }).round(4)
            
            if len(section_stats) > 1:
                print(f"\n📅 Month Period Analysis:")
                for section in ['Month Start', 'Month Middle', 'Month End']:
                    if section in section_stats.index:
                        posts = int(section_stats.loc[section, ('sentiment_score', 'count')])
                        sentiment = section_stats.loc[section, ('sentiment_score', 'mean')]
                        bullish = section_stats.loc[section, ('bullish_bearish', '<lambda>')]
                        print(f"   • {section}: {posts:3d}개 | Sentiment: {sentiment:6.3f} | Bullish: {bullish:.1%}")
        
        # 시각화
        output_dir = self._create_output_directory(target_date)
        generated_file = self._plot_monthly_patterns(df, stock_code, period_desc, output_dir=output_dir)

        # README 업데이트 (실제 생성된 파일만 반영)
        if generated_file:
            self._ensure_readme_updated(target_date, new_files=[generated_file])
        
        return {
            'monthly_summary': {
                'total_posts': total_posts,
                'avg_sentiment': avg_sentiment,
                'bullish_ratio': bullish_ratio,
                'sentiment_volatility': sentiment_volatility,
                'peak_hour': peak_hour
            },
            'weekly_breakdown': weekly_stats,
            'daily_patterns': daily_comprehensive,
            'session_analysis': session_comprehensive
        }
    
    def _plot_pre_market_patterns(self, yesterday_df, early_df, stock_code=None, output_dir=None):
        """장시작 전 리포트 시각화"""
        
        title_suffix = f" - {stock_code}" if stock_code else ""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'🌅 Pre-Market Analysis{title_suffix}', fontsize=16)
        
        # 1. 전일 시간대별 활동
        if not yesterday_df.empty:
            hourly_counts = yesterday_df.groupby('hour_of_day').size()
            axes[0, 0].bar(hourly_counts.index, hourly_counts.values, alpha=0.7, color='skyblue')
            axes[0, 0].set_title("Yesterday's Hourly Activity")
            axes[0, 0].set_xlabel('Hour of Day')
            axes[0, 0].set_ylabel('Number of Posts')
            axes[0, 0].axvspan(9, 15, alpha=0.2, color='green', label='Market Hours')
            axes[0, 0].legend()
        
        # 2. 전일 감정 분포
        if not yesterday_df.empty:
            sentiment_counts = yesterday_df['sentiment_label'].value_counts()
            colors = ['#ff9999', '#66b3ff', '#99ff99']
            axes[0, 1].pie(sentiment_counts.values, labels=sentiment_counts.index, 
                          autopct='%1.1f%%', colors=colors[:len(sentiment_counts)])
            axes[0, 1].set_title("Yesterday's Sentiment Distribution")
        
        # 3. 장외시간 vs 새벽시간 비교
        comparison_data = []
        comparison_labels = []
        
        if not yesterday_df.empty:
            after_hours = yesterday_df[yesterday_df['hour_of_day'] >= 16]
            comparison_data.append(len(after_hours))
            comparison_labels.append('After Hours\n(Yesterday)')
        
        if not early_df.empty:
            comparison_data.append(len(early_df))
            comparison_labels.append('Early Morning\n(Today)')
        
        if comparison_data:
            axes[1, 0].bar(comparison_labels, comparison_data, color=['orange', 'lightblue'])
            axes[1, 0].set_title('After Hours vs Early Morning Activity')
            axes[1, 0].set_ylabel('Number of Posts')
        
        # 4. 감정 점수 비교
        sentiment_data = []
        sentiment_labels = []
        
        if not yesterday_df.empty:
            sentiment_data.append(yesterday_df['sentiment_score'].mean())
            sentiment_labels.append('Yesterday\nOverall')
        
        if not early_df.empty:
            sentiment_data.append(early_df['sentiment_score'].mean())
            sentiment_labels.append('Early Morning\n(Today)')
        
        if sentiment_data:
            bars = axes[1, 1].bar(sentiment_labels, sentiment_data, 
                                 color=['lightcoral' if x < 0 else 'lightgreen' for x in sentiment_data])
            axes[1, 1].set_title('Sentiment Score Comparison')
            axes[1, 1].set_ylabel('Average Sentiment Score')
            axes[1, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
            
            # 값 표시
            for bar, value in zip(bars, sentiment_data):
                height = bar.get_height()
                axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                               f'{value:.3f}', ha='center', va='bottom')
        
        if output_dir is None:
            output_dir = self._create_output_directory()

        # 파일명 저장 날짜를 output_dir 기준 폴더명(YYYYMMDD)으로 맞춤
        folder_date = os.path.basename(output_dir)

        filename = f"pre_market_report_{stock_code}_{folder_date}.png" if stock_code else f"pre_market_report_{folder_date}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Pre-market chart saved: {filepath}")
        return filename
    
    def _plot_post_market_patterns(self, df, stock_code=None, output_dir=None):
        """장마감 후 리포트 시각화"""
        
        title_suffix = f" - {stock_code}" if stock_code else ""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'🌆 Post-Market Analysis{title_suffix}', fontsize=16)
        
        # 1. 장시간 시간대별 활동
        hourly_counts = df.groupby('hour_of_day').size()
        bars = axes[0, 0].bar(hourly_counts.index, hourly_counts.values, alpha=0.7, color='lightcoral')
        axes[0, 0].set_title("Trading Hours Activity")
        axes[0, 0].set_xlabel('Hour of Day')
        axes[0, 0].set_ylabel('Number of Posts')
        axes[0, 0].set_xticks(range(9, 16))
        
        # 피크 시간 강조
        peak_hour = hourly_counts.idxmax()
        peak_bar_idx = list(hourly_counts.index).index(peak_hour)
        bars[peak_bar_idx].set_color('red')
        bars[peak_bar_idx].set_alpha(1.0)
        
        # 2. 시간대별 감정 변화
        hourly_sentiment = df.groupby('hour_of_day')['sentiment_score'].mean()
        axes[0, 1].plot(hourly_sentiment.index, hourly_sentiment.values, 
                       marker='o', linewidth=2, markersize=8, color='blue')
        axes[0, 1].fill_between(hourly_sentiment.index, hourly_sentiment.values, 
                               alpha=0.3, color='blue')
        axes[0, 1].set_title('Sentiment Trend During Trading Hours')
        axes[0, 1].set_xlabel('Hour of Day')
        axes[0, 1].set_ylabel('Average Sentiment Score')
        axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[0, 1].set_xticks(range(9, 16))
        
        # 3. 강세/약세 비율
        bullish_ratio = (df['bullish_bearish'] == 'bullish').mean()
        bearish_ratio = (df['bullish_bearish'] == 'bearish').mean()
        neutral_ratio = (df['bullish_bearish'] == 'neutral').mean()
        
        ratios = [bullish_ratio, bearish_ratio, neutral_ratio]
        labels = ['Bullish', 'Bearish', 'Neutral']
        colors = ['green', 'red', 'gray']
        
        axes[1, 0].pie(ratios, labels=labels, autopct='%1.1f%%', colors=colors)
        axes[1, 0].set_title('Bullish/Bearish Distribution')
        
        # 4. 시간대별 게시글 수와 감정 점수 결합
        ax2 = axes[1, 1].twinx()
        
        # 게시글 수 (막대그래프)
        bars = axes[1, 1].bar(hourly_counts.index, hourly_counts.values, 
                             alpha=0.6, color='lightblue', label='Posts Count')
        axes[1, 1].set_ylabel('Number of Posts', color='blue')
        axes[1, 1].tick_params(axis='y', labelcolor='blue')
        
        # 감정 점수 (선그래프)
        line = ax2.plot(hourly_sentiment.index, hourly_sentiment.values, 
                       color='red', marker='o', linewidth=2, label='Sentiment Score')
        ax2.set_ylabel('Sentiment Score', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.3)
        
        axes[1, 1].set_title('Posts Count vs Sentiment Score')
        axes[1, 1].set_xlabel('Hour of Day')
        axes[1, 1].set_xticks(range(9, 16))
        
        plt.tight_layout()
        if output_dir is None:
            output_dir = self._create_output_directory()
        # 파일명 저장 날짜를 output_dir 기준 폴더명(YYYYMMDD)으로 맞춤
        folder_date = os.path.basename(output_dir)
        filename = f"post_market_report_{stock_code}_{folder_date}.png" if stock_code else f"post_market_report_{folder_date}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Post-market chart saved: {filepath}")
        return filename
    
    def _plot_weekly_patterns(self, df, stock_code=None, output_dir=None):
        """주간 리포트 시각화"""
        
        title_suffix = f" - {stock_code}" if stock_code else ""
        
        fig, axes = plt.subplots(3, 3, figsize=(18, 15))
        fig.suptitle(f'📅 Weekly Analysis{title_suffix}', fontsize=16)
        
        # 1. 요일별 게시글 수
        daily_counts = df.groupby('day_name').size()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_counts = daily_counts.reindex([day for day in day_order if day in daily_counts.index])
        
        bars = axes[0, 0].bar(range(len(daily_counts)), daily_counts.values, color='lightblue')
        axes[0, 0].set_title('Posts by Day of Week')
        axes[0, 0].set_xlabel('Day of Week')
        axes[0, 0].set_ylabel('Number of Posts')
        axes[0, 0].set_xticks(range(len(daily_counts)))
        axes[0, 0].set_xticklabels([day[:3] for day in daily_counts.index], rotation=45)
        
        # 가장 활발한 요일 강조
        if len(daily_counts) > 0:
            max_idx = daily_counts.values.argmax()
            bars[max_idx].set_color('red')
        
        # 2. 요일별 평균 감정 점수
        df['week_start'] = df['date'].dt.to_period('W').dt.start_time
        weekly_sentiment = df.groupby('week_start')['sentiment_score'].mean()
        
        colors = ['green' if x > 0 else 'red' for x in weekly_sentiment.values]
        axes[0, 1].bar(range(len(weekly_sentiment)), weekly_sentiment.values, color=colors, alpha=0.7)
        axes[0, 1].set_title('Weekly Average Sentiment')
        axes[0, 1].set_xlabel('Week Number')
        axes[0, 1].set_ylabel('Average Sentiment Score')
        axes[0, 1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        week_labels = [f"W{i+1}" for i in range(len(weekly_sentiment))]
        axes[0, 1].set_xticks(range(len(weekly_sentiment)))
        axes[0, 1].set_xticklabels(week_labels)
        
        # 3. 요일별 감정 점수
        daily_sentiment = df.groupby('day_name')['sentiment_score'].mean()
        daily_sentiment = daily_sentiment.reindex([day for day in day_order if day in daily_sentiment.index])
        
        colors = ['green' if x > 0 else 'red' for x in daily_sentiment.values]
        axes[0, 2].bar(range(len(daily_sentiment)), daily_sentiment.values, color=colors, alpha=0.7)
        axes[0, 2].set_title('Average Sentiment by Day')
        axes[0, 2].set_xlabel('Day of Week')
        axes[0, 2].set_ylabel('Average Sentiment Score')
        axes[0, 2].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[0, 2].set_xticks(range(len(daily_sentiment)))
        axes[0, 2].set_xticklabels([day[:3] for day in daily_sentiment.index], rotation=45)
        
        # 4. 일별 감정 점수 변화 (전체 기간)
        daily_sentiment_trend = df.groupby(df['date'].dt.date)['sentiment_score'].mean()
        
        axes[1, 0].plot(daily_sentiment_trend.index, daily_sentiment_trend.values, 
                       marker='.', linewidth=1, markersize=4, alpha=0.8)
        axes[1, 0].fill_between(daily_sentiment_trend.index, daily_sentiment_trend.values, 
                               alpha=0.2)
        axes[1, 0].set_title('Daily Sentiment Trend')
        axes[1, 0].set_xlabel('Date')
        axes[1, 0].set_ylabel('Average Sentiment Score')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # 5. 시간대별 활동 히트맵 (요일별)
        activity_matrix = df.groupby(['day_name', 'hour_of_day']).size().unstack(fill_value=0)
        activity_matrix = activity_matrix.reindex([day for day in day_order if day in activity_matrix.index])
        
        if HAS_SEABORN:
            sns.heatmap(activity_matrix, ax=axes[1, 1], cmap='YlOrRd', 
                       cbar_kws={'label': 'Number of Posts'})
        else:
            im = axes[1, 1].imshow(activity_matrix.values, cmap='YlOrRd', aspect='auto')
            axes[1, 1].set_xticks(range(len(activity_matrix.columns)))
            axes[1, 1].set_xticklabels(activity_matrix.columns)
            axes[1, 1].set_yticks(range(len(activity_matrix.index)))
            axes[1, 1].set_yticklabels([day[:3] for day in activity_matrix.index])
            plt.colorbar(im, ax=axes[1, 1])
        
        axes[1, 1].set_title('Activity Heatmap (Day vs Hour)')
        axes[1, 1].set_xlabel('Hour of Day')
        axes[1, 1].set_ylabel('Day of Week')
        
        # 6. 감정 분포 파이차트
        sentiment_dist = df['sentiment_label'].value_counts()
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        axes[1, 2].pie(sentiment_dist.values, labels=sentiment_dist.index, 
                      autopct='%1.1f%%', colors=colors[:len(sentiment_dist)])
        axes[1, 2].set_title('Overall Sentiment Distribution')
        
        # 7. 장시간 vs 장외시간 비교
        df['market_session'] = df['hour_of_day'].apply(
            lambda x: 'Market Hours' if 9 <= x <= 15 else 'After Hours'
        )
        
        session_counts = df.groupby('market_session').size()
        
        # 게시글 수 비교
        axes[2, 0].bar(session_counts.index, session_counts.values, 
                      color=['lightgreen', 'lightcoral'], alpha=0.7)
        axes[2, 0].set_title('Market Hours vs After Hours\n(Post Count)')
        axes[2, 0].set_ylabel('Number of Posts')
        
        # 각 막대 위에 값 표시
        for i, (session, count) in enumerate(session_counts.items()):
            axes[2, 0].text(i, count + max(session_counts.values) * 0.01, 
                           f'{count}\n({count/sum(session_counts.values):.1%})', 
                           ha='center', va='bottom')
        
        # 8. 강세/약세 비율 트렌드 (주별)
        weekly_bullish = df.groupby('week_start').apply(
            lambda x: (x['bullish_bearish'] == 'bullish').mean()
        )
        
        axes[2, 1].plot(range(len(weekly_bullish)), weekly_bullish.values, 
                       marker='o', linewidth=2, markersize=8, color='green')
        axes[2, 1].fill_between(range(len(weekly_bullish)), weekly_bullish.values, 
                               alpha=0.3, color='green')
        axes[2, 1].set_title('Weekly Bullish Ratio Trend')
        axes[2, 1].set_xlabel('Week Number')
        axes[2, 1].set_ylabel('Bullish Ratio')
        axes[2, 1].set_xticks(range(len(weekly_bullish)))
        axes[2, 1].set_xticklabels([f"W{i+1}" for i in range(len(weekly_bullish))])
        axes[2, 1].axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
        axes[2, 1].set_ylim(0, 1)
        
        # 9. 시간대별 평균 감정 점수
        hourly_sentiment = df.groupby('hour_of_day')['sentiment_score'].mean()
        
        colors = ['green' if x > 0 else 'red' for x in hourly_sentiment.values]
        bars = axes[2, 2].bar(hourly_sentiment.index, hourly_sentiment.values, 
                             color=colors, alpha=0.7)
        axes[2, 2].set_title('Average Sentiment by Hour')
        axes[2, 2].set_xlabel('Hour of Day')
        axes[2, 2].set_ylabel('Average Sentiment Score')
        axes[2, 2].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        # 장시간 영역 표시
        axes[2, 2].axvspan(9, 15, alpha=0.2, color='yellow', label='Market Hours')
        axes[2, 2].legend()
        
        plt.tight_layout()

        if output_dir is None:
            output_dir = self._create_output_directory()

        # 파일명 저장 날짜를 output_dir 기준 폴더명(YYYYMMDD)으로 맞춤
        folder_date = os.path.basename(output_dir)

        filename = f"weekly_report_{stock_code}_{folder_date}.png" if stock_code else f"weekly_report_{folder_date}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Weekly chart saved: {filepath}")
        return filename
    
    def _plot_monthly_patterns(self, df, stock_code=None, period_desc="", output_dir=None):
        """월간 리포트 시각화"""
        
        title_suffix = f" - {stock_code}" if stock_code else ""
        
        fig, axes = plt.subplots(3, 3, figsize=(18, 15))
        fig.suptitle(f'📆 Monthly Analysis{title_suffix}', fontsize=16)
        
        # 1. 일별 게시글 수
        daily_counts = df.groupby('date').size()
        axes[0, 0].bar(daily_counts.index, daily_counts.values, color='lightblue')
        axes[0, 0].set_title('Posts by Date')
        axes[0, 0].set_xlabel('Date')
        axes[0, 0].set_ylabel('Number of Posts')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. 일별 평균 감정 점수
        daily_sentiment = df.groupby('date')['sentiment_score'].mean()
        axes[0, 1].plot(daily_sentiment.index, daily_sentiment.values, marker='o', color='blue')
        axes[0, 1].set_title('Average Sentiment by Date')
        axes[0, 1].set_xlabel('Date')
        axes[0, 1].set_ylabel('Average Sentiment Score')
        axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. 월별 게시글 수
        monthly_counts = df.groupby(df['date'].dt.to_period("M")).size()
        axes[0, 2].bar(monthly_counts.index.astype(str), monthly_counts.values, color='lightgreen')
        axes[0, 2].set_title('Posts by Month')
        axes[0, 2].set_xlabel('Month')
        axes[0, 2].set_ylabel('Number of Posts')
        axes[0, 2].tick_params(axis='x', rotation=45)
        
        # 4. 월별 평균 감정 점수
        monthly_sentiment = df.groupby(df['date'].dt.to_period("M"))['sentiment_score'].mean()
        axes[1, 0].plot(monthly_sentiment.index.astype(str), monthly_sentiment.values, marker='o', color='green')
        axes[1, 0].set_title('Average Sentiment by Month')
        axes[1, 0].set_xlabel('Month')
        axes[1, 0].set_ylabel('Average Sentiment Score')
        axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 5. 주별 게시글 수
        weekly_counts = df.groupby(df['date'].dt.to_period("W")).size()
        axes[1, 1].bar(weekly_counts.index.astype(str), weekly_counts.values, color='salmon')
        axes[1, 1].set_title('Posts by Week')
        axes[1, 1].set_xlabel('Week')
        axes[1, 1].set_ylabel('Number of Posts')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        # 6. 주별 평균 감정 점수
        weekly_sentiment = df.groupby(df['date'].dt.to_period("W"))['sentiment_score'].mean()
        axes[1, 2].plot(weekly_sentiment.index.astype(str), weekly_sentiment.values, marker='o', color='orange')
        axes[1, 2].set_title('Average Sentiment by Week')
        axes[1, 2].set_xlabel('Week')
        axes[1, 2].set_ylabel('Average Sentiment Score')
        axes[1, 2].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        axes[1, 2].tick_params(axis='x', rotation=45)
        
        # 7. 감정 분포 파이차트
        sentiment_dist = df['sentiment_label'].value_counts()
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        axes[2, 0].pie(sentiment_dist.values, labels=sentiment_dist.index, 
                      autopct='%1.1f%%', colors=colors[:len(sentiment_dist)])
        axes[2, 0].set_title('Overall Sentiment Distribution')
        
        # 8. 장시간 vs 장외시간 비교
        df['market_session'] = df['hour_of_day'].apply(
            lambda x: 'Market Hours' if 9 <= x <= 15 else 'After Hours'
        )
        
        session_counts = df.groupby('market_session').size()
        
        # 게시글 수 비교
        axes[2, 1].bar(session_counts.index, session_counts.values, 
                      color=['lightgreen', 'lightcoral'], alpha=0.7)
        axes[2, 1].set_title('Market Hours vs After Hours\n(Post Count)')
        axes[2, 1].set_ylabel('Number of Posts')
        
        # 각 막대 위에 값 표시
        for i, (session, count) in enumerate(session_counts.items()):
            axes[2, 1].text(i, count + max(session_counts.values) * 0.01, 
                           f'{count}\n({count/sum(session_counts.values):.1%})', 
                           ha='center', va='bottom')
        
        # 9. 강세/약세 비율 트렌드 (월별)
        monthly_bullish = df.groupby(df['date'].dt.to_period("M")).apply(
            lambda x: (x['bullish_bearish'] == 'bullish').mean()
        )
        
        axes[2, 2].plot(monthly_bullish.index.astype(str), monthly_bullish.values, 
                       marker='o', linewidth=2, markersize=8, color='green')
        axes[2, 2].fill_between(monthly_bullish.index.astype(str), monthly_bullish.values, 
                               alpha=0.3, color='green')
        axes[2, 2].set_title('Monthly Bullish Ratio Trend')
        axes[2, 2].set_xlabel('Month')
        axes[2, 2].set_ylabel('Bullish Ratio')
        axes[2, 2].set_xticks(range(len(monthly_bullish)))
        axes[2, 2].set_xticklabels([f"{(datetime.now() - timedelta(days=30*i)).strftime('%Y-%m')}월" for i in range(len(monthly_bullish))])
        axes[2, 2].axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
        axes[2, 2].set_ylim(0, 1)
        
        plt.tight_layout()
        
        if output_dir is None:
            output_dir = self._create_output_directory()

        # 파일명 저장 날짜를 output_dir 기준 폴더명(YYYYMMDD)으로 맞춤
        folder_date = os.path.basename(output_dir)

        filename = f"monthly_report_{stock_code}_{folder_date}.png" if stock_code else f"monthly_report_{folder_date}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Monthly chart saved: {filepath}")
        return filename

    def _ensure_readme_updated(self, target_date=None, new_files=None):
        """리포트 생성 후 README가 최신 상태인지 확인하고 업데이트 (신규 파일만 반영)"""
        if self.auto_update_readme and self._readme_manager:
            try:
                self._readme_manager.ensure_readme_updated(custom_date=target_date, new_files=new_files)
            except Exception as e:
                print(f"⚠️ Failed to update README after report generation: {e}")
        elif self.auto_update_readme:
            print("⚠️ README manager not available. Install readme_manager.py")
        
    def generate_readme_file(self):
        """README.md 파일 생성 (통합 관리자 사용)"""
        
        if self._readme_manager:
            try:
                result = self._readme_manager.create_readme()
                if result:
                    print(f"📝 README.md file generated successfully!")
                    return result
                else:
                    print("❌ Failed to generate README.md")
                    return None
            except Exception as e:
                print(f"❌ README generation failed: {e}")
                return None
        else:
            print("⚠️ README manager not available. Please install readme_manager.py")
            return None

if __name__ == "__main__":
    import sys

    analyzer = PatternAnalyzer()

    # 파라미터 파싱
    args = sys.argv[1:]
    # 사용법: python pattern_analyzer.py [report_type] [date]
    # 예시: python pattern_analyzer.py pre_market 20250706

    report_type = args[0] if len(args) > 0 else None
    date_arg = args[1] if len(args) > 1 else None

    # 날짜 파싱
    target_date = None
    if date_arg:
        # YYYYMMDD 또는 YYYY-MM-DD 지원
        if '-' in date_arg:
            target_date = date_arg
        else:
            try:
                target_date = f"{date_arg[:4]}-{date_arg[4:6]}-{date_arg[6:]}"
            except Exception:
                target_date = date_arg

    if report_type == "pre_market":
        print(f"\n🌅 Generating Pre-Market Report for {target_date}")
        analyzer.generate_pre_market_report(target_date=target_date)
    elif report_type == "post_market":
        print(f"\n🌆 Generating Post-Market Report for {target_date}")
        analyzer.generate_post_market_report(target_date=target_date)
    elif report_type == "weekly":
        print(f"\n📅 Generating Weekly Report for {target_date}")
        analyzer.generate_weekly_report(target_date=target_date)
    elif report_type == "monthly":
        print(f"\n📆 Generating Monthly Report for {target_date}")
        analyzer.generate_monthly_report(target_date=target_date)
    elif report_type == "summary":
        print(f"\n📊 Generating General Analysis Report for {target_date}")
        analyzer.generate_summary_report(target_date=target_date)
    else:
        # 파라미터 없으면 기존 전체 실행
        print("📊 Starting comprehensive pattern analysis...")
        print("=" * 60)
        test_date = "2025-07-04"  # 금요일 예시

        # print(f"\n🌅 Generating Pre-Market Report for {test_date} (Test)")
        # analyzer.generate_pre_market_report(target_date=test_date)

        print(f"\n🌆 Generating Post-Market Report for {test_date} (Test)")
        analyzer.generate_post_market_report(target_date=test_date)

        # print("📅 Generating Weekly Report (Sunday Schedule)")
        # analyzer.generate_weekly_report(target_date=test_date)

        # print("📆 Generating Monthly Report (Monthly Schedule)")
        # analyzer.generate_monthly_report(target_date=test_date)

        print("📊 Generating General Analysis Report")
        analyzer.generate_summary_report(target_date=test_date)

        print("\n" + "=" * 60)
        print("📝 All individual reports have been generated with README updates...")
        try:
            generate_dir = analyzer._create_output_directory(test_date)
            if os.path.exists(generate_dir):
                files = [f for f in os.listdir(generate_dir) if f.endswith('.png')]
                print(f"📊 Generated {len(files)} chart files in {generate_dir}")
                print(f"✅ All reports and README.md updated successfully!")
                print(" Check your GitHub repository for updated charts!")
            else:
                print("⚠️ No files generated in the target directory")
        except Exception as e:
            print(f"⚠️ Error checking generated files: {e}")

