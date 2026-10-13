# CHRONO CROSS: THE RADICAL DREAMERS EDITION 한글화 — 상태

목표: v0.1.0 = Radical Dreamers 한글화, v0.1.1 = Chrono Cross 본편 한글화. 순서대로 적용.
대상: Steam PC판 (BuildId 8116082). 패치는 data/*.dat만 교체하고 exe는 건드리지 않는다.

## 폴더
| 경로 | 내용 |
|---|---|
| `CHRONO CROSS  THE RADICAL DREAMERS EDITION/` | 테스트용 게임 설치본 (install.py가 data를 덮어씀) |
| `00_original/` | 원본 백업 + `manifest.json`(설치본 전체 SHA-256) |
| `10_extracted/rd/` | radicaldreamers.dat 풀어 놓은 것, `fonts/` 복호화 폰트 |
| `20_source/trans/rd/` | 번역 시트 `rd_000`–`rd_030.json` (7,719행, 원문 대신 해시 jh/eh만) |
| `20_source/batches/` | 번역 묶음 (apply_batch.py로 시트에 병합) |
| `20_source/fonts/` | 한글 폰트(나눔명조, OFL) + `rdfont.json` 병합 설정 |
| `30_build/` | 빌드 산출물 |
| `40_release/` | 배포 zip (`tools/release.py <버전>`) |
| `50_patch/` | 패치 레시피 `patch/rd.ops·rd.bin` (make_patch.py 생성) |
| `patch_kit/` | 패처 소스: apply.ps1 + .bat 2개 + 사용자용 README.txt (release.py가 zip에 담음) |
| `90_test/shots/` | 실행 확인 스크린샷 |

## 빌드 순서
```
py -X utf8 tools/extract_rd.py      # 최초 1회: 원본 백업, 압축 해제, 폰트 복호화
py -X utf8 tools/export_rd.py       # 최초 1회: 번역 시트 생성
py -X utf8 tools/apply_batch.py 20_source/batches/rd_bNNN.json
py -X utf8 tools/build_rdfont.py    # 폰트 설정이 바뀌었을 때
py -X utf8 tools/build_rd.py        # 검증 + radicaldreamers.dat 생성 (--release: 미번역 행이 있으면 실패)
py -X utf8 tools/make_patch.py      # 배포 레시피 생성 + 30_build의 dat를 패처 결과물과 동일하게 교체
py -X utf8 tools/install.py         # 게임 폴더에 설치 (restore: 원본 복구)
py -X utf8 tools/release.py 0.1.0   # 40_release/CCRDE_KR_v0.1.0.zip
```

## Radical Dreamers 구조 (확인됨)
- `data/*.dat`는 일반 ZIP. `radicaldreamers.dat` 안에 `translate.txt`(UTF-16LE TSV: Address/JP/EN/FR/IT/DE/ES, 7,719행)와 폰트.
- `ENFONT/ENFONTI/ENFONTN.DAT`(TTF), `JPFONT.DAT`(CFF OTF)는 AES-128-CBC. 키 = SHA-256(GUID 문자열)[:16], IV = [16:].
  시드는 exe .rdata 0x5ea5e0 (`tools/rdcrypt.py`). 복호화→재암호화 바이트 일치 확인.
- 영어 모드는 비례폭 폰트로 띄어쓰기 단위 자동 줄바꿈. 한국어는 **EN 열을 교체**한다.
- 행은 문장 조각으로 이어 붙는 경우가 있다(줄바꿈 없이 끝나는 행). 한국어도 EN 열의 앞뒤 공백·줄바꿈 모양을 따른다(빌드가 검사).
- `{}` = 이탤릭, `•` = 선택지, `[NAME]` = 주인공 이름.

## 진행
- [x] 구조 조사, 폰트 복호화, 한글 폰트 병합(11,223자)
- [x] 빌드 파이프라인 (검증: [NAME] 개수, {} 짝, 끝 줄바꿈, 폰트에 없는 글자)
- [x] 런타임: 게임 화면에서 한글 렌더링 확인 (2026-10-13, 90_test/shots/v010_*.png). 게임은 PostMessage 입력을 무시 → gamectl fkey(실제 키, 포커스 잠깐 가져옴, GAMECTL_KEEP=1이면 유지; 포커스 잃으면 게임이 최소화됨)
- [x] 번역: 7,719 / 7,719행 (rd_b000–b059)
- [ ] 그래픽 텍스트(타이틀 부제, 이름 입력 안내 등) 조사
- [ ] 이름 입력 화면 / 기본 이름 "Serge" (exe 내부 — 미해결)
- [x] 배포 패치(50_patch): 원본 dat를 ZIP 레벨에서 재조립하는 레시피 방식. 원본 게임 데이터 미포함,
      translate.txt·폰트는 STORED로 기록 → 결과 바이트 고정, SHA-256 검증. 가짜 게임 폴더에서 적용/복구 확인.
      v0.1.0 zip 5.8MB (40_release/CCRDE_KR_v0.1.0.zip). 결과 dat sha256 7d1bd153…
- [ ] 정식 Steam판 검증 (테스트 설치본에 steamclient.dll/flt.ini가 있어 정식판 radicaldreamers.dat 해시 a6c8179b…가 같은지 미확인)
- [x] translate.txt STORED dat 게임에서 정상 동작 확인
- [x] 공개 저장소 github.com/shk-game-kr-translation/chronocross-kr (tools/check_public.py, 글꼴은 원본 대비 차분)

## 미해결 / 사람 결정 필요
- 고유명사 표기 방침 (docs/glossary.md, 현재 일본어 원문 기준 가안)
- 한글 폰트 선택 (현재 나눔명조 ExtraBold, 실제 화면 확인 후 결정)
- 기본 이름 "Serge" 처리 방식
