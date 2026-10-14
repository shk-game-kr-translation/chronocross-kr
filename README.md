# 크로노 크로스: 래디컬 드리머즈 에디션 한글 패치

Steam PC판 「CHRONO CROSS: THE RADICAL DREAMERS EDITION」 비공식 한글 패치입니다.

| 버전 | 범위 |
|---|---|
| v0.1.0 | 수록작 「래디컬 드리머즈 -훔칠 수 없는 보석-」 본문 전체 |
| v0.1.1 | 크로노 크로스 본편 대사·메뉴·아이템·기술·몬스터·전투 이벤트 전체 (15,181행, 게임 내 검수 중) |
| v0.1.2 | 본편 타이틀 메뉴 튕김 수정, 주인공 이름 일본어판 기준(세르주·키드·알프), 래디컬 드리머즈 검수 반영 |
| v0.1.3 | ESC 메뉴 `???` 표시 수정, 일시정지 화면 한글, 게임 내 검수 반영 |
| v0.1.4 | 주인공 이름 세르주 → 세르쥬, 래디컬 드리머즈 대사의 주인공 이름을 「세르쥬」로 고정 (입력한 이름은 반영되지 않음) |

> 이 저장소에는 **게임 데이터가 들어 있지 않습니다.** 실행 파일·데이터 파일·원문 대본·이미지·원본 글꼴은 포함하지 않으며,
> 패치는 사용자의 정품 게임 파일에서 원문을 읽어 한국어 문장과 조합합니다.

## 설치 방법 (일반 사용자)

### v0.1.4 (본편 + 래디컬 드리머즈) — 파일 덮어쓰기
0. [Releases](../../releases) 에서 최신 `CCRDE_KR_v<버전>_overwrite.zip` 을 받습니다.
1. 게임을 완전히 종료하고 게임 폴더(`CHRONOCROSS.exe` 가 있는 곳)를 엽니다.
2. (권장) `data` 폴더의 `lang.dat`, `font.dat`, `ui.dat`, `radicaldreamers.dat` 를 다른 곳에 백업합니다.
3. 패치 압축을 풀고 안의 `data` 폴더를 게임 폴더에 덮어씁니다.
4. 게임 언어를 **English** 로 둔 채 실행합니다.

되돌리기: 백업한 파일을 다시 덮어쓰거나 Steam 의 "게임 파일 무결성 확인".
세이브 데이터는 바꾸지 않습니다. 다만 패치를 지울 계획이면 세이브를 따로 백업해 두는 것을 권합니다.

### v0.1.0 (래디컬 드리머즈) — 패처

1. [Releases](../../releases) 에서 `CCRDE_KR_v<버전>.zip` 을 받습니다.
2. 게임을 완전히 종료합니다.
3. zip 의 압축을 풉니다. (폴더째로. `patch` 폴더가 함께 있어야 합니다.)
4. **`한글패치_적용.bat`** 을 더블클릭합니다.
   - Steam 라이브러리에서 게임 폴더를 자동으로 찾습니다.
   - "게임 폴더를 찾지 못했습니다" 가 나오면 압축을 푼 폴더를 통째로 게임 폴더
     (`RADICALDREAMERS.exe` 가 있는 곳. Steam 에서 게임 우클릭 → 관리 → 로컬 파일 보기) 안에 넣고 다시 실행합니다.
   - Windows SmartScreen 경고가 뜨면 "추가 정보 → 실행".
5. "한글 패치를 적용했습니다." 가 나오면 완료입니다.
6. 게임 언어를 **English** 로 둔 채 실행하고 런처에서 **RADICAL DREAMERS** 를 고릅니다.
   (한국어 문장은 영어 자리에 들어가 있습니다.)

**되돌리기**: `원본_복구.bat` 실행 (패치 때 만든 `data\radicaldreamers.dat.kr_backup` 으로 복구).
또는 Steam → 게임 우클릭 → 속성 → 설치된 파일 → 게임 파일 무결성 확인.

**업데이트**: 새 버전의 `한글패치_적용.bat` 을 그대로 실행하면 됩니다.

### 대상 파일

| 파일 | 원본 SHA-256 |
|---|---|
| `data\radicaldreamers.dat` | `a6c8179b37eca646e741c395504d8714e2701cef027308556d8f5906be09a142` |

원본이 다르면(게임 업데이트 등) 패처는 아무것도 바꾸지 않고 멈춥니다. 결과 파일도 해시가 맞을 때만 교체합니다.
패처는 Windows 기본 PowerShell 로 동작하며 추가 프로그램이 필요 없습니다.

### 알려진 문제
- 이름 입력 화면과 기본 이름(Serge), 조작법 안내 화면 등 그림 글자는 영어 그대로입니다.
- 본편: `Lv`, `Sta.` 같은 짧은 HUD 표기는 화면 배치 때문에 영어로 두었습니다. 그림 글자(타이틀 등)는 영어입니다.

자세한 변경 내역은 [CHANGELOG.md](CHANGELOG.md).

## 오역·버그 제보

[Issues](../../issues) 에 남겨 주세요. 장면(어느 시나리오, 어떤 상황)과 현재 문구, 제안 문구를 적어 주시면 됩니다.

## 직접 빌드하기 (개발자)

필요: Python 3.11+, `pip install fonttools pycryptodome`, 정품 게임

```
py -X utf8 tools/extract_rd.py        # 최초 1회: 게임 폴더의 radicaldreamers.dat → 00_original/ 백업, 압축 해제, 글꼴 복호화
py -X utf8 tools/build_rdfont.py      # 한글 글꼴 병합 (20_source/fonts/rdfont.json)
py -X utf8 tools/build_rd.py --release  # 검증 + 30_build/data/radicaldreamers.dat
py -X utf8 tools/make_patch.py        # 배포 레시피 50_patch/patch/rd.ops + rd.bin
py -X utf8 tools/release.py 0.1.0     # 40_release/CCRDE_KR_v0.1.0.zip
```
본편(v0.1.1 이후):
```
py -X utf8 tools/export_cc.py              # 최초 1회: lang.dat → 20_source/trans/cc 시트 (해시만)
py -X utf8 tools/build_cc.py --release     # 검증 + 30_build/data/lang.dat, font.dat, ui.dat (한글 글리프 추가)
py -X utf8 tools/pack_overwrite.py 0.1.4   # 40_release/CCRDE_KR_v0.1.4_overwrite.zip (덮어쓰기판, Releases 첨부용)
py -X utf8 tools/make_review.py 0.1.4      # 40_release/CCRDE_KR_v0.1.4_review.html (원문 대조·편집 검수 페이지)
py -X utf8 tools/apply_review.py <내보낸.json>  # 검수 페이지에서 내보낸 수정을 시트에 반영
```
게임 폴더 위치는 `tools/paths.py` 의 `GAME` 에서 바꿉니다. `tools/install.py` 는 빌드 결과를 게임 폴더에 바로 넣습니다
(`install.py restore` 로 원본 복구).

### 번역 데이터에 원문이 없는 이유
`20_source/trans/rd/*.json`, `20_source/trans/cc/*.json` 의 각 행은 한국어 번역(`ko`)과 원문 대신 **원문 해시(`jh` 일본어, `eh` 영어)** 만 가집니다.
빌드할 때 사용자의 `radicaldreamers.dat` 에서 원문을 읽어 해시로 대조한 뒤 사용하므로, 대본을 싣지 않고도
같은 결과물(바이트 단위 동일)을 만들 수 있습니다.

### 패치 방식
`radicaldreamers.dat` 는 ZIP 입니다. `tools/make_patch.py` 는 원본 ZIP 을 바꾸지 않은 항목은 그대로 복사하고,
`translate.txt` 는 원본에서 영어 칸만 한국어로 바꿔 끼우며, 글꼴(ENFONT 3종, AES 암호화)은 원본 글꼴과의 차분으로
한글 글리프만 담는 레시피를 만듭니다. `patch_kit/apply.ps1` 이 이 레시피를 그대로 실행합니다.

### 폴더
| 폴더 | 내용 | 저장소 |
|---|---|---|
| `00_original/` | 원본 백업 (직접 준비) | ✗ |
| `10_extracted/` | 원본에서 풀어 낸 파일 (분석용) | ✗ |
| `20_source/` | `trans/` 번역, `fonts/` 한글 글꼴(나눔명조)과 병합 설정 | ✓ |
| `30_build/` | 빌드 결과 | ✗ |
| `40_release/` | 배포 zip | ✗ (Releases 로 배포) |
| `50_patch/` | 패치 레시피 | ✗ |
| `patch_kit/` | 패처 (apply.ps1, .bat, 사용자용 README.txt) | ✓ |
| `tools/` | 빌드·추출 도구 | ✓ |
| `docs/` | 진행 상황, 용어집 | ✓ |

## 라이선스
- 도구 코드: MIT (`LICENSE`)
- 한국어 번역문·설정: CC BY-NC-SA 4.0 (`LICENSE`)
- 글꼴: 나눔명조·나눔스퀘어라운드, SIL Open Font License 1.1 (`20_source/fonts/nanummyeongjo/OFL.txt`);
  Neo둥근모, SIL Open Font License 1.1 (`20_source/fonts/neodgm/LICENSE.txt`)
- 원본 게임: 권리자 소유 — [NOTICE.md](NOTICE.md)
