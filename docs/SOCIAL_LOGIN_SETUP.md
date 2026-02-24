# 소셜 로그인(Google, 카카오) 설정 가이드

앱에서 **Google 로그인**과 **카카오 로그인** 버튼이 이미 추가되어 있습니다.  
아래 순서대로 **한 번만** 설정하면 실제로 동작합니다. (모르는 분도 따라할 수 있도록 단계별로 적었습니다.)

---

## 0. 준비할 것

- **Supabase** 프로젝트 (이미 쓰고 있는 계정)
- **Google 계정**
- **카카오 계정** (카카오톡 로그인 가능한 계정)

---

## 1. Supabase에서 리다이렉트 URL 확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 접속 후 로그인
2. 사용 중인 **프로젝트** 선택
3. 왼쪽 메뉴에서 **Authentication** → **URL Configuration** 이동
4. **Redirect URLs** 항목에 아래 주소가 있는지 확인 (없으면 **Add URL**로 추가)
   - 로컬: `http://localhost:3000/auth/callback`
   - 실제 서비스 주소: `https://내도메인.com/auth/callback`  
     (예: `https://stock-cock.vercel.app/auth/callback`)
5. **Save** 저장

---

## 2. Google 로그인 설정

### 2-1. Google Cloud Console에서 프로젝트·OAuth 만들기

1. [Google Cloud Console](https://console.cloud.google.com/) 접속 후 Google 계정으로 로그인
2. 상단 프로젝트 선택 드롭다운 클릭 → **새 프로젝트** → 이름 입력 (예: `Stock Cock`) → **만들기**
3. 왼쪽 메뉴 **API 및 서비스** → **사용자 인증 정보**
4. **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID** 선택
5. 처음이면 **애플리케이션 유형** 설정 화면이 나옵니다.
   - **동의 화면 구성** 클릭
   - **User Type**: **외부** 선택 → **만들기**
   - **앱 이름**: `Stock Cock` (또는 원하는 이름)
   - **사용자 지원 이메일**: 본인 이메일
   - **개발자 연락처**: 본인 이메일
   - **저장 후 계속** → **저장 후 계속** (범위는 비워두고) → **대시보드로 돌아가기**
6. 다시 **사용자 인증 정보** → **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
7. **애플리케이션 유형**: **웹 애플리케이션**
8. **이름**: `Stock Cock Web` (아무 이름이나 가능)
9. **승인된 JavaScript 원본**에 다음 추가:
   - `http://localhost:3000` (개발용)
   - `https://내도메인.com` (실제 서비스 주소, 예: `https://stock-cock.vercel.app`)
10. **승인된 리디렉션 URI**에 다음 **정확히** 추가:
    - Supabase 프로젝트 URL이 `https://xxxxx.supabase.co` 라면  
      `https://xxxxx.supabase.co/auth/v1/callback`  
      (Supabase 대시보드 → **Settings** → **API** 에서 **Project URL** 확인)
    - 로컬 Supabase 사용 시: `http://127.0.0.1:54321/auth/v1/callback`
11. **만들기** 클릭
12. **클라이언트 ID**와 **클라이언트 보안 비밀**이 나오면 **복사**해서 메모장에 붙여넣기 (나중에 Supabase에 입력)

### 2-2. Supabase에 Google 정보 입력

1. Supabase 대시보드 → **Authentication** → **Providers**
2. **Google** 행 찾기 → **Enable** 켜기
3. **Client ID**: 위에서 복사한 Google **클라이언트 ID** 붙여넣기
4. **Client Secret**: 위에서 복사한 **클라이언트 보안 비밀** 붙여넣기
5. **Save** 저장

---

## 3. 카카오 로그인 설정

### 3-1. 카카오 디벨로퍼스에서 앱·키 만들기

1. [카카오 디벨로퍼스](https://developers.kakao.com/) 접속 후 카카오 계정으로 로그인
2. **내 애플리케이션** → **애플리케이션 추가하기**
3. **앱 이름**: `Stock Cock` (또는 원하는 이름) → **저장**
4. 방금 만든 앱 클릭
5. **앱 키** 탭에서 **REST API 키** 복사 (숫자로 된 긴 키) → 메모장에 붙여넣기
6. **카카오 로그인** 메뉴 클릭 → **활성화 설정**에서 **활성** 상태로 **저장**
7. **Redirect URI** 설정:
   - **Redirect URI** 에 **아래 주소 정확히** 추가  
     (Supabase Project URL이 `https://xxxxx.supabase.co` 일 때)  
     `https://xxxxx.supabase.co/auth/v1/callback`
   - 로컬 Supabase: `http://127.0.0.1:54321/auth/v1/callback`
   - **저장**
8. **동의 항목** 탭 → **닉네임**, **프로필 사진**, **카카오계정(이메일)** 중 필요 항목 **필수 동의** 또는 **선택 동의**로 설정 후 저장
9. **제품 설정** → **카카오 로그인** → **코드** 탭에서 **Client Secret** 생성 후 **비밀번호** 설정  
   → **Client Secret** 값 복사 (한 번만 보이므로 메모장에 저장)

### 3-2. Supabase에 카카오 정보 입력

1. Supabase 대시보드 → **Authentication** → **Providers**
2. **Kakao** 행 찾기 → **Enable** 켜기
3. **Client ID (REST API 키)**: 위에서 복사한 **REST API 키** 붙여넣기
4. **Client Secret (Secret Key)**: 위에서 복사한 **Client Secret** 붙여넣기
5. **Save** 저장

---

## 4. 확인

1. 프론트엔드 실행: `npm run dev` (프로젝트 루트에서)
2. 브라우저에서 `http://localhost:3000/login` 접속
3. **이메일/비밀번호 로그인** 아래에 **소셜 로그인** 구역이 보이는지 확인
4. **Google로 로그인** / **카카오로 로그인** 클릭
5. 각각 Google·카카오 로그인 화면으로 이동했다가, 로그인 후 다시 앱(`/auth/callback` → 메인)으로 돌아오면 성공

---

## 5. 자주 나오는 문제

| 증상 | 확인할 것 |
|------|------------|
| Google/카카오 로그인 후 에러 페이지로 감 | Supabase **Redirect URLs**에 `http://localhost:3000/auth/callback` (또는 실제 도메인/auth/callback) 추가했는지 |
| "redirect_uri_mismatch" (Google) | Google Cloud **승인된 리디렉션 URI**에 `https://xxxxx.supabase.co/auth/v1/callback` 가 **정확히** 들어갔는지 (Supabase Project URL과 일치하는지) |
| 카카오 "Redirect URI 일치하지 않음" | 카카오 **Redirect URI**에 `https://xxxxx.supabase.co/auth/v1/callback` 가 **정확히** 들어갔는지 |
| 로그인 버튼 눌러도 반응 없음 | 브라우저 콘솔(F12) 에러 메시지 확인. Supabase **Providers**에서 Google/Kakao **Enable** 및 Client ID·Secret 저장했는지 확인 |

---

## 요약 체크리스트

- [ ] Supabase **URL Configuration** → Redirect URLs에 `/auth/callback` 주소 추가
- [ ] Google Cloud Console: OAuth 클라이언트 ID 생성, 리디렉션 URI에 `https://xxxxx.supabase.co/auth/v1/callback` 추가
- [ ] Supabase **Providers** → **Google** Enable, Client ID·Secret 입력 후 Save
- [ ] 카카오 디벨로퍼스: 앱 생성, 카카오 로그인 활성화, Redirect URI에 `https://xxxxx.supabase.co/auth/v1/callback` 추가, Client Secret 생성
- [ ] Supabase **Providers** → **Kakao** Enable, REST API 키·Client Secret 입력 후 Save

위까지 하면 **기존 이메일 로그인은 그대로** 두고, **Google / 카카오 소셜 로그인**만 추가된 상태로 동작합니다.
