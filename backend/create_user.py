
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가 (backend 폴더 기준)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.utils.supabase_client import get_supabase

def create_user():
    supabase = get_supabase()
    email = "banlan21@gmail.com"
    # 비밀번호 최소 6자 정책
    password = "090909"
    
    print(f"Creating user: {email}")
    
    try:
        # Admin API를 사용하여 이메일 자동 확인 후 유저 생성
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        print(f"User created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"ID: {response.user.id}")
        
    except Exception as e:
        print(f"Error creating user: {e}")
        if "unique" in str(e).lower():
            # 이미 존재하는 경우 비밀번호 재설정 시도 (선택 사항)
            print("User already exists. Attempting to update password...")
            try:
                # 유저 검색 후 업데이트
                # (Admin API에서 list_users로 id 찾거나 해야 함. 여기서는 생략하고 그냥 알림만)
                print("Please try logging in. If password is wrong, delete user from dashboard and retry.")
            except Exception as e2:
                print(f"Update failed: {e2}")

if __name__ == "__main__":
    create_user()
