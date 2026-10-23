# bot/ 사용법

현재 들어 있는 것은 **화면 기록 도구(recon.py)** 와 **속도 제한 모듈(limits.py)** 뿐이다.
게임을 대신 플레이하는 드라이버는 아직 없다. 화면 기록을 본 뒤에 만든다.

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
