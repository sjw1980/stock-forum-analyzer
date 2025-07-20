#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions Report Type Determiner
Determines the appropriate report type based on UTC time and Korean time (UTC+9).
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

def parse_date_argument(date_str):
    """Parse date string in various formats"""
    if not date_str:
        return None
    
    # Try different date formats
    formats = ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Invalid date format: {date_str}. Use YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD")

def get_kst_now(override_date=None):
    """Get current Korean time (UTC+9) or override with specific date"""
    if override_date:
        # Convert override_date to UTC then add 9 hours
        utc_date = override_date.replace(tzinfo=timezone.utc)
        return utc_date + timedelta(hours=9)
    return datetime.now(timezone.utc) + timedelta(hours=9)

def get_utc_now(override_date=None):
    """Get current UTC time or override with specific date"""
    if override_date:
        return override_date.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def determine_report_type(override_date=None):
    """Determine report type based on GitHub Actions event and time"""
    
    # Get event type from GitHub Actions environment variables
    github_event_name = os.environ.get('GITHUB_EVENT_NAME', 'schedule')
    github_event_inputs = os.environ.get('GITHUB_EVENT_INPUTS_REPORT_TYPE', '')
    
    print(f"GitHub Event: {github_event_name}")
    
    # Current time information (with possible override)
    kst_now = get_utc_now(override_date)
    
    if override_date:
        print(f"Using override date: {override_date.strftime('%Y-%m-%d')}")
    
    print(f"Current KST time: {kst_now.strftime('%Y-%m-%d %H:%M:%S KST')}")

    hour_kst = kst_now.hour
    minute_kst = kst_now.minute
    day_of_week_kst = kst_now.isoweekday()  # 1=Monday, 7=Sunday
    day_of_month_kst = kst_now.day
    
    print(f"KST: {hour_kst:02d}:{minute_kst:02d}, weekday={day_of_week_kst}, day={day_of_month_kst}")
    
    # Handle different event types
    if github_event_name == 'workflow_dispatch':
        # Manual execution: use user-selected value
        report_type = github_event_inputs or 'pre_market'
        print(f"Manual execution: {report_type}")
        return report_type
        
    elif github_event_name == 'push':
        # Push event: generate all reports
        print("Push event: all reports")
        return 'all'
        
    else:
        # Schedule event: determine by time
        print("Schedule event - determining by time...")
        
        # Determine report type by time
        if hour_kst == 8 or hour_kst == 9:
            print("Detected: Pre-market time (KST 08:xx day)")
            return 'pre_market'
            
        elif hour_kst == 18 or hour_kst == 19:
            # KST 18:xx weekday - Post-market
            print("Detected: Post-market time (KST 18:xx weekday)")
            return 'post_market'
            
        elif hour_kst == 22 or hour_kst == 23:
            # KST 22:xx Sunday - Weekly report
            print("Detected: Weekly report time (KST 22:xx Sunday)")
            return 'weekly'
            
        else:
            print("Detected: Monthly report time (KST 09:xx 1st)")
            return 'monthly'
            
def set_github_output(key, value):
    """Set value to GitHub Actions GITHUB_OUTPUT"""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a', encoding='utf-8') as f:
            f.write(f"{key}={value}\n")
        print(f"Set GitHub output: {key}={value}")
    else:
        print(f"GitHub output (local): {key}={value}")

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Determine GitHub Actions report type')
    parser.add_argument('--date', '-d', type=str, help='Override date (YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD)')
    parser.add_argument('--test-time', '-t', type=str, help='Test specific UTC time (HH:MM)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("GitHub Actions - Report Type Determiner")
    print("=" * 60)
    
    try:
        override_date = None
        
        # Parse override date if provided
        if args.date:
            try:
                override_date = parse_date_argument(args.date)
                print(f"Using override date: {override_date.strftime('%Y-%m-%d')}")
            except ValueError as e:
                print(f"Error parsing date: {e}")
                return 'pre_market'
        
        # Parse test time if provided
        if args.test_time and override_date:
            try:
                time_parts = args.test_time.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                override_date = override_date.replace(hour=hour, minute=minute)
                print(f"Using test time: {hour:02d}:{minute:02d} KST")
            except (ValueError, IndexError) as e:
                print(f"Error parsing test time: {e}")
                return 'pre_market'
        
        # Determine report type
        report_type = determine_report_type(override_date)
        
        # Set GitHub Actions output
        set_github_output('report_type', report_type)
        
        print("=" * 60)
        print(f"Final Result: {report_type}")
        print("=" * 60)
        
        return report_type
        
    except Exception as e:
        print(f"Error determining report type: {e}")
        # Use default value on error
        set_github_output('report_type', 'pre_market')
        return 'pre_market'

if __name__ == "__main__":
    print("Starting report type determination...")
    main()
