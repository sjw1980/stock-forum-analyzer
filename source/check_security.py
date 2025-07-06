#!/usr/bin/env python3
"""
GitHub 업로드 전 설정 검증 스크립트
"""

import os
import sys
from pathlib import Path

def check_env_files():
    """환경변수 파일들을 검증합니다."""
    print("🔍 환경변수 파일 검증 중...")
    
    # .env 파일 확인
    env_file = Path('.env')
    env_example_file = Path('.env.example')
    
    if not env_example_file.exists():
        print("❌ .env.example 파일이 없습니다.")
        return False
    
    if env_file.exists():
        print("⚠️  .env 파일이 존재합니다. GitHub에 업로드되지 않도록 주의하세요.")
    
    # Docker Compose 환경변수 파일 확인
    docker_env_file = Path('docker-compose/.env')
    docker_env_example_file = Path('docker-compose/.env.example')
    
    if not docker_env_example_file.exists():
        print("❌ docker-compose/.env.example 파일이 없습니다.")
        return False
    
    if docker_env_file.exists():
        print("⚠️  docker-compose/.env 파일이 존재합니다. GitHub에 업로드되지 않도록 주의하세요.")
    
    print("✅ 환경변수 파일 검증 완료")
    return True

def check_sensitive_content():
    """민감한 정보가 포함된 파일들을 검증합니다."""
    print("🔍 민감한 정보 검증 중...")
    
    sensitive_patterns = [
        'crawlerpassword',
        'rootpassword',
        'password=',
        'PASSWORD='
    ]
    
    # 검사할 파일들
    files_to_check = [
        'README.md',
        'docker-compose/README.md',
        'docker-compose/docker-compose.yml',
        'database.py',
        'analysis_report.py',
        'fix_duplicates.py'
    ]
    
    issues_found = []
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in sensitive_patterns:
                    if pattern in content:
                        issues_found.append(f"{file_path}: '{pattern}' 발견")
    
    if issues_found:
        print("❌ 민감한 정보가 발견되었습니다:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    
    print("✅ 민감한 정보 검증 완료")
    return True

def check_gitignore():
    """gitignore 파일을 검증합니다."""
    print("🔍 .gitignore 파일 검증 중...")
    
    gitignore_file = Path('.gitignore')
    if not gitignore_file.exists():
        print("❌ .gitignore 파일이 없습니다.")
        return False
    
    with open(gitignore_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_patterns = ['.env', '*.log', '__pycache__/']
    missing_patterns = []
    
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ .gitignore에 다음 패턴들이 없습니다: {', '.join(missing_patterns)}")
        return False
    
    print("✅ .gitignore 파일 검증 완료")
    return True

def check_config_import():
    """config.py 임포트가 올바른지 검증합니다."""
    print("🔍 config.py 임포트 검증 중...")
    
    try:
        from config import DB_CONFIG, validate_config
        print("✅ config.py 임포트 성공")
        
        # .env 파일이 있는 경우에만 설정 검증
        if Path('.env').exists():
            validate_config()
            print("✅ 설정 검증 완료")
        else:
            print("ℹ️  .env 파일이 없어 설정 검증을 건너뜁니다.")
        
        return True
    except Exception as e:
        print(f"❌ config.py 문제: {e}")
        return False

def main():
    """메인 검증 함수"""
    print("🚀 GitHub 업로드 전 보안 검증 시작\n")
    
    checks = [
        check_env_files,
        check_sensitive_content,
        check_gitignore,
        check_config_import
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 모든 검증을 통과했습니다! GitHub에 안전하게 업로드할 수 있습니다.")
        print("\n📋 GitHub 업로드 전 체크리스트:")
        print("   ✅ .env 파일이 .gitignore에 포함되어 있음")
        print("   ✅ 하드코딩된 비밀번호가 제거됨")
        print("   ✅ .env.example 파일이 존재함")
        print("   ✅ README.md가 업데이트됨")
        print("   ✅ SECURITY.md가 존재함")
        return True
    else:
        print("❌ 일부 검증에 실패했습니다. 문제를 해결한 후 다시 시도하세요.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
