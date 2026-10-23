# bot/ 사용법

- `driver.py`: 자동 플레이 (이 문서 5장)
- `recon.py`: 화면 기록 (읽기 전용, 직접 플레이하며 기록)
- `screens.py` / `actions.py` / `policy.py`: 화면 분류, 결정 규칙, 정책 값
- `limits.py`: 속도 제한 (`config.json`)

## 1. 준비 (사용자 PC, 한 번만)

Python 3.9+ 필요.

```bash
git clone https://github.com/Manners523/Kangwon.git      # 이미 있으면 생략
cd Kangwon
git checkout claude/great-albattani-2npld4
cd kickru-ballon

python3 -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r bot/requirements.txt
playwright install chromium
```

## 2. 화면 기록 (읽기 전용)

```bash
python3 bot/recon.py --url https://kickru.com/ --profile .pw-profile
```

- 창이 하나 열린다. **직접** 새 커리어를 만들고 시즌을 진행한다. 도구는 클릭도 입력도 하지 않는다.
- 화면이 바뀔 때마다 `data/recon/<날짜_시각>/001/`, `002/` ... 에 저장된다.
  - `screen.json`: 보이는 텍스트와 버튼/링크/입력 목록(글자, id, class, 비활성 여부, 위치)
  - `screen.png`: 스크린샷
- 가능한 한 다양한 화면을 지나간다: 홈, 오퍼(이적/재계약), 상점, 집중 육성, 시즌 시뮬레이션,
  선택 이벤트, 시즌 요약, 발롱도르 순위/수상 화면, 은퇴.
- 끝내려면 터미널에서 Ctrl+C (또는 `--max 100`, `--duration 1800` 등으로 자동 종료).
- 옵션: `--interval 1.5`(초, 최소 0.5), `--html`(전체 HTML 저장, 용량 큼), `--profile`(브라우저 프로필 폴더; 같은 폴더를 쓰면 세이브가 유지됨)

저장된 `screen.json` 들을 Claude 세션의 `kickru-ballon/data/recon/` 에 올리면 그걸 보고 드라이버를 짠다.
스크린샷에는 선수 이름 등이 보일 수 있으니 공유 전에 확인한다. `data/recon/` 은 git 에 올라가지 않는다.

## 3. 속도 제한

`bot/config.json` 의 값은 **임의로 정한 보수적 기본값**이다 (허가 답변의 값이 아님).

| 키 | 값 | 의미 |
|---|---|---|
| max_parallel_browsers | 1 | 동시 브라우저 수 (1만 지원) |
| min_seconds_between_actions | 2.5 | 액션 간 최소 간격(초) |
| action_jitter_seconds | 1.5 | 간격에 0~1.5초를 무작위로 더함 |
| max_actions_per_minute | 15 | 어떤 60초 창에서도 이 수를 넘지 않음 |
| pause_every_n_actions | 200 | 이 횟수마다 쉼 |
| pause_seconds | 30 | 쉬는 시간 |
| max_careers_per_day | 3 | 하루 시작 가능한 커리어 수 (파일로 기록, 재실행해도 유지) |

운영팀 답변에 실제 제한이 있으면 그 값 이하로 바꾼다. 값이 비었거나 0 이하이면 드라이버는 실행을 거부한다.
`recon.py` 는 조작을 하지 않아서 이 제한의 대상이 아니다(로컬 DOM 읽기만 한다).

## 4. 테스트

```bash
python3 -m unittest discover -s tests
```

## 5. 자동 플레이 (driver.py)

사람이 플레이할 필요가 없다. 처음 한 번만 **직접 서명**이 필요할 수 있다(고교 -> 유스 첫 계약 화면).
서명 화면이 뜨면 드라이버는 기다린다. 열린 창의 서명 칸에 마우스로 그리고 `계약하기`가 켜지면 자동으로 이어진다.

```
# 1) 점검 실행: 40 액션만 하고 멈춘다. 창을 보면서 이상한 클릭이 없는지 확인한다.
python bot/driver.py --name exp-001 --max-actions 40

# 2) 이상 없으면 이어서 (세이브는 .pw-profile 에 유지된다)
python bot/driver.py --name exp-001 --max-actions 2000
```

- **모르는 화면**을 만나면 클릭하지 않고 멈춘다. `data/recon/unknown_*/screen.json` (+ png)이 저장된다.
  그 폴더를 Claude 세션에 올리면 규칙을 추가한다.
- `--explore`: 모르는 화면에서 `확인/다음/계속` 버튼만 눌러 본다(그 외는 멈춤). 멈추는 횟수가 줄어든다. 첫 점검에는 쓰지 말 것.
- 멈추려면 작업 폴더에 `STOP` 파일을 만들거나 Ctrl+C.
- 버튼이 팝업 등에 **가려져 있으면** 누르지 않고 멈춘다. 같은 화면 id에서 6번 연속 액션해도 진행이 없으면 멈추고 화면을 저장한다.
- 시뮬레이션 중이라 버튼이 비활성이면 멈추지 않고 기다린다(최대 약 5분).
- 누르지 않는 것: 지금 은퇴하기, 국가대표 은퇴 선언, 개발자 서버비 내주기(결제), 의견 보내기, 댓글 좋아요, 푸터 링크, 병역(현역 입대/상무 지원), 이적·임대 요청.
- 종료할 때 세이브 키 하나를 읽기 전용으로 `data/raw/dump_*.json`에 저장한다. 이어서:
  ```
  python scripts/from_save.py data/raw/dump_*.json data/real
  python scripts/validate.py data/real/*.json
  ```
- 기록: `data/runs/*.jsonl`에 화면별 선택지 전체(이적 오퍼의 구단·연봉 포함)와 고른 값이 남는다.
- 정책 옵션: `--turning-point random|first|last`, `--contract stay|best_offer`, `--youth-path club|school`,
  `--nt-callup join|decline`, `--match-view result_only|watch`, `--seed N`. 무작위 항목은 seed로 재현되고 로그에 남는다.
- 캐릭터 이름은 `--name`(기본 `exp-001`). 포지션·국적·학교는 게임 기본값을 쓴다.
- 한국 국적(기본)이면 병역 화면이 나온다. 아직 본 적이 없는 화면이라 드라이버는 거기서 멈출 가능성이 높다.
- 속도: `config.json`. 하루 새 커리어 수 한도는 `data/.career_budget.json`에 기록된다.
