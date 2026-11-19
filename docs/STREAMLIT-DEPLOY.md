# Streamlit 앱으로 배포하기 (Streamlit Community Cloud)

이 저장소(`srbschoolex`)는 그대로 Streamlit 앱이 됩니다. 진입 파일은 루트의 `app.py`, 필요한 패키지는 `requirements.txt`에 있습니다.
배포는 무료 **Streamlit Community Cloud**(https://share.streamlit.io)에서 GitHub 계정으로 합니다.

## 1. 처음 한 번: Streamlit 계정 연결
1. https://share.streamlit.io 에 접속해 **Continue with GitHub**로 로그인합니다.
2. GitHub가 Streamlit에 저장소 접근 권한을 물으면 **Authorize**를 누릅니다.

## 2. 앱 만들기
1. 오른쪽 위 **Create app** → **Deploy a public app from GitHub**(또는 "Yup, I have an app")를 고릅니다.
2. 아래처럼 채웁니다.

   | 항목 | 값 |
   |---|---|
   | Repository | `pse915/srbschoolex` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | App URL | 원하는 주소 (예: `srbschoolex`) |

3. **Advanced settings**에서 Python 버전은 기본값(3.12)으로 둡니다.
4. **Deploy**를 누르면 2~5분 뒤 `https://<App URL>.streamlit.app` 주소로 앱이 열립니다.

## 3. 비밀값(Secrets) 넣기 — 교사용 대시보드·Google Sheets를 쓸 때만
게임만 할 거면 비밀값 없이도 동작합니다(학생 기기 저장 + 서버 임시 저장).
교사용 대시보드나 Google Sheets 백업을 쓰려면:

1. 앱 화면 오른쪽 아래 **Manage app** → **⋮** → **Settings** → **Secrets**를 엽니다.
2. `.streamlit/secrets.example.toml`의 내용을 붙여넣고, 자리표시자를 실제 값으로 바꿉니다.
   - `teacher_password`: 교사용 대시보드 비밀번호 (길고 무작위로)
   - `google_sheet_id`와 `[gcp_service_account]`: Sheets 백업을 쓸 때만. 서비스 계정에 시트 편집 권한을 줘야 합니다
3. **Save**를 누르면 앱이 자동으로 다시 시작합니다.

> 비밀값은 저장소에 커밋하지 마세요. `.streamlit/secrets.toml`은 `.gitignore`에 들어 있습니다.

## 4. 알아 둘 점
- **서버 저장은 임시입니다.** Community Cloud의 디스크(`private_data/progress.sqlite3`)는 앱이 재시작되면 사라질 수 있습니다. 오래 보관할 기록은 Google Sheets 연동을 켜거나, 학생이 다이어리에서 백업 JSON을 내려받게 하세요.
- **잠자기:** 며칠 접속이 없으면 앱이 잠듭니다. 처음 연 사람이 **Yes, get this app back up!**을 누르면 1분쯤 뒤 다시 켜집니다. 수업 직전에 미리 한 번 열어 두세요.
- **화면 구성:** 왼쪽 사이드바에서 **학교 탐방 게임(새)**(기본) / **학교 전체 지도** / **생애설계 게임(기존)** / **교사용 대시보드**를 고릅니다. 새 게임과 지도는 서버 저장 없이 기기에만 기록합니다.
- **공개 범위:** 이 저장소는 공개 저장소입니다. 앱도 기본으로 누구나 열 수 있습니다. 앱 접근을 제한하려면 **Settings → Sharing**에서 **Only specific people**로 바꾸고 이메일을 추가합니다.

## 4-1. 플립2 등 오래된 내장 브라우저: GitHub Pages 주소 사용
Streamlit 화면은 최신 브라우저가 필요해서, 플립2 내장 브라우저에서는 흰 화면만 보일 수 있습니다.
이때는 Streamlit 없이 게임만 여는 주소를 씁니다(저장소 Settings → Pages: `main` / `(root)`).
- 게임: https://pse915.github.io/srbschoolex/
- 지도만: https://pse915.github.io/srbschoolex/?map

`main`에 올리면 이 주소도 1~2분 안에 함께 바뀝니다.

## 5. 고친 내용을 앱에 반영하기
저장소 `main` 브랜치에 커밋을 올리면 Streamlit이 몇 분 안에 자동으로 다시 배포합니다.
학교 배치를 고칠 때는 `data/school_layout.json`을 수정한 뒤 아래 순서로 다시 만들고 커밋합니다(README "학교 외관·배치 다시 만들기" 참고).

```bash
python tools/school_art.py --out components/rpg_game/assets --only all
python build_world.py
python tools/build_explore_data.py
python tools/asset_manifest.py
python tools/check_maps.py
```

## 6. 내 컴퓨터에서 먼저 확인하기
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
브라우저에 표시된 주소(보통 http://localhost:8501)를 엽니다.
