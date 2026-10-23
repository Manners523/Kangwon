# 인수인계: kickru 발롱도르 프로젝트 (새 세션용)

작성: 2026-10-24. 이전 세션은 클라우드 컨테이너에서 돌아 사용자 PC·kickru.com에 접근하지 못했다.
새 세션은 **사용자 PC(Windows)에서 도는 로컬 세션**이어야 한다. 그러면 드라이버를 직접 실행하고, 멈춘 화면 파일을 직접 읽고, 코드를 고쳐 다시 돌릴 수 있다.

## 0. 먼저 읽을 것
- 사용자 선호: **한국어**. 사용자의 전제와 논리를 적극적으로 검토하고, 근거가 약하거나 방향이 잘못되면 말해 달라고 했다. 확실하지 않은 내용은 "확인 안 됨"으로 분명히 표시. 사용자는 행정학과 학부생이며 과제 작성에도 Claude를 쓴다(이 프로젝트는 개인 재미·학습용).
- 사용자는 코딩 초보다. 명령어는 PowerShell 기준으로, 한 번에 하나씩, 위치(어느 폴더에서)까지 적어 줄 것. 파일을 직접 바꾸게 하거나 여러 번 왕복시키는 것을 싫어한다.
- 브랜치: `claude/great-albattani-2npld4` (저장소 `Manners523/Kangwon`, 공개). 작업 폴더는 저장소 안의 `kickru-ballon/`. 기존 블록깨기(`index.html`, `README.md`)는 무관, 건드리지 말 것.
- 커밋 끝에 붙이는 줄: `Co-Authored-By: ...` 형식은 새 세션의 지침을 따를 것.

## 1. 목표와 현재 위치
최종 목표(사용자): "벤치에서 발롱까지"(https://kickru.com/, 브라우저 축구 인생 게임)를 **대신 플레이해서 데이터를 쌓고, 발롱도르를 최대한 많이 수상**하는 프로그램.

| 단계 | 상태 |
|---|---|
| 1. 데이터 파이프라인(세이브 변환·검증·탐색) | 완료, 테스트 통과 |
| 2. 감독형 자동 플레이 드라이버 | 구현됨, **실제 사이트에서 첫 시즌 도중 멈추는 문제를 디버깅 중** |
| 3. 정책 무작위 배정 실험 | 미착수 (`docs/experiment-design.md` 초안만) |

## 2. 지금 막힌 곳 (가장 먼저 할 일)
`.\run.bat --name exp-002 --max-actions 40` 실행 결과:
`[001] NOTICE_DIALOG` -> `LANDING` -> `CREATE_AVATAR` -> `CREATE_PROFILE` -> `CREATE_STYLE` -> `CREATE_FOCUS` -> `CREATE_CONFIRM`(고1 시즌 시작)까지 정상.
그 다음 멈춤: **`HOME - 홈에서 처리할 대기 항목도 시즌 보내기 버튼도 보이지 않음`**
화면 저장: 사용자 PC의 `kickru-ballon\data\recon\unknown_20261024_004253\` (`screen.json`, `screen.png`).

해야 할 일:
1. 위 폴더를 읽는다(로컬 세션이면 직접 읽을 수 있다). 홈에 무엇이 있는지 확인한다.
2. 가설(미검증): (a) 시즌 시뮬레이션 진행 중이라 하단 `시즌 보내기`가 아직 없다 -> 기다리면 됨, (b) `시즌 보내기`는 시즌/선수 탭에만 있다 -> 탭 이동 규칙 필요, (c) 홈에 모르는 항목이 있다.
   기록(첫 세션의 `cf0e9b16-199.zip` 300화면)에서는 홈 하단에 활성 `N 시즌 보내기` 버튼이 있었고, 대기 중인 제안/전환점이 있으면 그 버튼이 없었다. 시즌 시뮬레이션 중 홈 모습은 기록에 없다.
3. `bot/actions.py` 의 `HOME` 처리와 `bot/screens.py` 를 고치고, 그 화면을 `tests/fixtures/screens/` 에 넣어 회귀 테스트로 만든다. (이전 사고도 이렇게 고쳤다: `CREATE_CONFIRM`)
4. 다시 `python bot\driver.py --name exp-002 --max-actions 40` 로 실행.

## 3. 사용자 환경
- Windows, Python 3.15.1 (`C:\Users\manne\AppData\Local\Python\pythoncore-3.15-64\python.exe`), `pip install playwright` 완료(전역 설치, 가상환경 없음), `python -m playwright install chromium` 완료. 명령은 `python ...` (`python3` 아님).
- 코드 폴더(ZIP으로 풀어 둔 것, git 저장소 아님): `C:\Users\manne\Documents\Kangwon-claude-great-albattani-2npld4 (1)\Kangwon-claude-great-albattani-2npld4\kickru-ballon` (경로에 공백과 괄호가 있다). 다른 복사본이 `C:\Users\manne\Downloads\Kangwon-claude-great-albattani-2npld4\...` 에도 있다. 진짜 세이브는 `.pw-profile` 에 있다.
- git 미설치. 로컬 세션을 쓰려면 git 설치 후 `git clone -b claude/great-albattani-2npld4 https://github.com/Manners523/Kangwon.git` 를 권한다.
- **중요**: `run.bat`/`update.ps1` 은 실행할 때마다 GitHub 브랜치의 최신 코드로 `bot\*.py` 등을 **덮어쓴다**. 로컬 세션에서 코드를 고치는 동안은 `run.bat` 을 쓰지 말고 `python bot\driver.py ...` 를 직접 실행할 것(로컬 수정이 사라진다). 고친 코드를 사용자가 `run.bat` 으로 받게 하려면 먼저 push 해야 한다.
- 사용자는 `.pw-profile` 폴더를 지우면 새 캐릭터로 시작한다는 것을 안다. 현재 세이브는 첫 시즌 시작 직후 상태(`exp-002`).

## 4. 코드 지도 (`kickru-ballon/`)
| 경로 | 역할 |
|---|---|
| `bot/driver.py` | Playwright 드라이버. 화면 읽기 -> 분류 -> 결정 -> 클릭. `--dry-run`, `--explore`, `--max-actions`, STOP 파일 |
| `bot/screens.py` | 순수 함수 `classify(screen)` (화면 id 28종 + UNKNOWN), `is_blocked()` 차단 목록 |
| `bot/actions.py` | `decide(sid, screen, policy)` -> Decision(steps/wait/stop/log) |
| `bot/policy.py` | 정책 값(전환점 선택 random/first/last, 계약 stay/best_offer, 대표팀 join/decline, 경기 result_only/watch, seed) |
| `bot/limits.py` | `Pacer`(액션 간격·분당 한도·주기적 휴식), `DailyCareerBudget`, `config.json` |
| `bot/recon.py` | 읽기 전용 화면 기록기(`screen.json`+png). 요소에 `idx` 부여, `window.__kbEls` 보관 |
| `scripts/from_save.py` | 세이브 덤프 -> 스키마 변환(`data/real/`). 대표팀 기록 합산, OVR, 선택 로그(`decisions`) 포함 |
| `scripts/validate.py` `explore.py` `compare.py` `ingest.py` `common.py` | 검증·탐색·시드 대조·범용 변환 |
| `data/seed/` | 사용자가 손으로 옮긴 2캐릭터(Ikarus ST 13행, 데이터A CAM 16행) |
| `data/real/` | 실제 세이브에서 변환한 시즌 기록 |
| `tests/` | `python -m unittest discover -s tests` -> 32개 통과(마지막 확인 시점) |
| `tests/fixtures/screens/` | 기록 화면 대표 46개 + `expected.json` |
| `docs/experiment-design.md`, `docs/inquiry-draft.md` | 실험 설계 초안, 운영팀 문의문 초안 |
| `run.bat`, `update.ps1` | 사용자용 자동 업데이트 실행기(영문만 사용: PowerShell 5.1 이 BOM 없는 .ps1 을 ANSI 로 읽는다) |
| `SKILL.md` | Claude in Chrome 용 localStorage 읽기 전용 수집 절차 |

주의: `python3 -I` 는 스크립트 폴더를 import 경로에서 빼서 쓰지 말 것. 스크립트는 저장소의 `kickru-ballon/` 에서 실행.

## 5. 안전 원칙 (유지할 것)
- **허용 목록 방식**: 인식된 화면만 조작. 모르는 화면은 클릭하지 않고 멈춰 화면을 저장한다(`data/recon/unknown_*`, 자동 ZIP). 추측 클릭 금지.
- **절대 누르지 않는 것**: `지금 은퇴하기`, `국가대표 은퇴 선언`, `💸 개발자 서버비 내주기`(결제로 보임), `의견 보내기`, 댓글 좋아요(`rx-like`), 푸터/외부 링크, `현역 입대`, `상무 지원`, `이적 요청`, `임대 요청`. (`screens.is_blocked`)
- 가려진 요소(팝업 뒤)는 누르지 않는다(`elementFromPoint` 검사). 같은 화면 id 6번 연속 액션 시 멈춤. 대상이 안 보이면 4번 재확인 후 멈춤. 비활성 버튼은 기다림.
- **직접 서명**: 첫 유스 계약에서 `아래 칸에 마우스나 손가락으로 직접 서명해 주세요` 화면이 나온다. 드라이버는 누르지 않고 기다리며 **사람이 그리게** 한다. 이후 계약은 저장된 서명(`준비됨`).
- 세이브 접근은 `localStorage.getItem` 읽기만. 쓰기·삭제 금지. `/api/` 호출 금지(robots.txt 가 disallow 한다고 문서에 적혀 있음, 직접 확인은 못 함).
- 속도: `bot/config.json` 은 **이전 세션이 임의로 정한 보수적 값**(최소 2.5초 + 지터 1.5초, 분당 15, 하루 3커리어)이다. 운영팀 답변에 적힌 실제 한도가 아니다.

## 6. 미검증·불확실 사항 (사실처럼 쓰지 말 것)
- **운영팀 허가**: 사용자가 "허가가 나왔다"고 구두로 알렸고, 랭킹 등록은 허용, 속도·횟수 제한은 "명시됨"이라고 했다. **답변 원문과 제한 값은 확인하지 못했다.** 약관(`/terms`) 내용도 사용자의 요약만 있다(자동화 조항 없음, 제3조 "조작 기록의 반복 등록, 과도한 자동 요청" 금지, 은퇴 기록은 랭킹에 자동 등록). 문의 주소는 사용자 보고로 `support@kickru.com`(미확인).
- 랭킹: 실험 커리어가 랭킹에 쌓이지 않게 게임 내 설정에서 끄는 것을 권했으나 설정 위치를 확인하지 못했다.
- 윈도우용 `run.bat`/`update.ps1`, 탐색기 열기(`explorer /select`)는 이전 세션에서 실행해 보지 못했다(사용자 보고로 `run.bat` 업데이트는 동작: `Updated. Version: 36cdf68`).
- 분류기 규칙은 사용자가 직접 기록한 커리어 1개(300화면)로 만들었다. 기록에 없는 화면: 상점 구매, 오퍼 수락 상세 일부, 은퇴 이후/새 커리어, 부상, 병역 선택 결과, 주장 제안, 포지션 전환 제안, 임대, 연봉 협상 팝업, 시즌 시뮬레이션 중 홈. 한국 국적(기본)이라 병역 화면에서 멈출 가능성이 크다.
- **발롱도르 판정 공식은 알려져 있지 않다.** 수상 항목에 `value`/`benchmark` 가 있으나 의미 미확인(MVP 는 value < benchmark 인데도 수상 항목에 있다). 비수상 시즌에는 값이 없다.
- 표본: 캐릭터 2개 프로 34시즌. "발롱도르 극대화"는 이 데이터로는 보장 불가. 정책 효과를 가르려면 무작위 배정 실험이 필요하고, 하루 3커리어 한도에서는 100커리어에 한 달 이상 걸린다(추정).

## 7. 세이브·게임에서 확인된 사실
- localStorage 키 `second-life-football-legends-v2` 하나가 세이브(약 74만 자). 값은 JSON 문자열 배열, 원소를 한 번 더 `JSON.parse`. 커리어 2개(이카루스=Ikarus, 데이터A).
- 시즌 기록 `life.history[]`, 시즌별 발롱 순위 `ballonRank`(없으면 후보 탈락 NC), 수상은 `awards[]`(`category: 발롱도르`). 선택 기록 `life.storyLog[]`. OVR `core.history[y].overall`(시즌 y 시작 시점으로 보임).
- 요약 화면의 골·도움·평점 = 클럽 `stats` + 선택된 대표팀 대회 `nationals[].stats`(친선 제외), 평균 평점 = `ratingSum/apps`.
- 오퍼 목록(구단·연봉)은 세이브에는 없지만 계약 화면의 `t-li` 에 보인다 -> 드라이버 로그(`data/runs/*.jsonl`)에 남게 해 두었다.
- 화면 DOM: SPA(`/` 하나). 안정적인 클래스 `t-btn t-primary`(주 행동), `t-btn t-grey`, `su-cand`, `t-choice`, `t-li`, `primary wide`, `t-tab`, `bdo-skip`, `pk-trigger`(드롭다운), 팝업은 `data-slot="dialog-content"`(뒤 화면 텍스트가 그대로 남는다 -> 오분류 주의).
- 시드 데이터 오독 정정: Ikarus 35/36 UCL 은 8강, 43/44 는 2위.

## 8. 이후 계획
1. 홈 멈춤 해결 -> 한 커리어가 끝까지 도는지(또는 어디서 멈추는지) 확인. 모르는 화면마다 규칙+픽스처+테스트 추가.
2. 커리어 종료 시 세이브 덤프 -> `from_save.py` -> `validate.py` -> `explore.py`.
3. 파일럿(1~수 커리어)으로 소요 시간·분산 측정 -> 필요한 표본 수 재추정.
4. 정책 무작위 배정 실험(`docs/experiment-design.md`). 정책 변수 후보: 전환점 선택, 이적 방침, 대표팀 소집, 상점, 집중 육성. 숨은 속성(`hiddenCurve`, `potentialGrade`, `developmentStyle`, `hiddenDurability`)은 커리어마다 달라 무작위 배정으로 상쇄해야 한다.
5. 허가 답변의 실제 제한 값으로 `bot/config.json` 교체.

## 9. 새 세션 시작 프롬프트 (그대로 붙여 넣기)
```
kickru-ballon/HANDOFF.md 를 먼저 읽고 이어서 진행해 줘. 지금 막힌 곳은 드라이버가 첫 시즌 시작 직후 HOME 화면에서 멈추는 문제야(2번 항목).
data\recon\unknown_20261024_004253 폴더를 직접 읽고 원인을 확인한 뒤, 규칙과 테스트를 추가하고 python bot\driver.py --name exp-002 --max-actions 40 으로 다시 돌려 봐.
안전 원칙(5번)은 지키고, 모르는 화면에서는 멈춰. run.bat 은 쓰지 말고 python bot\driver.py 를 직접 실행해(로컬 수정이 덮어써져).
```
