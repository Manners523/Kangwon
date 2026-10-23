---
name: kickru-ballon-collect
description: kickru.com(벤치에서 발롱까지)의 내 세이브 데이터를 브라우저 localStorage에서 읽기 전용으로 덤프해 발롱도르 분석용 JSON으로 만든다. "kickru 세이브 덤프", "발롱도르 데이터 수집", "localStorage 키 확인" 요청에 사용. 게임을 대신 플레이하지 않는다.
---

# kickru 세이브 수집 (읽기 전용)

사용자의 실제 Chrome 탭에서 **자신의 기기 localStorage**를 읽어 JSON 덤프를 만든다.
분석은 이 스킬이 아니라 같은 폴더의 `scripts/`(파이썬)가 한다. Chrome 쪽에는 파이썬 실행 환경이 없을 수 있다.

## 하지 말 것 (이 스킬의 범위 밖)
- 게임 조작: 버튼 클릭, 시즌 진행, 이적/육성 선택. **자동 플레이 금지.**
  자동화는 사용자가 `https://kickru.com/terms`를 직접 읽고 허용 여부를 확인한 뒤에야 별도로 논의한다.
- 서버 요청: `/api/`(robots.txt가 disallow)와 공개 랭킹 API 호출, 일일 랭킹 제출.
- localStorage **쓰기**: `setItem`, `removeItem`, `clear` 호출 금지. 세이브가 지워지면 되돌릴 수 없다.
- 인증/계정으로 보이는 키(`token`, `auth`, `session`, `jwt`, `email`, `password` 등)의 값을 덤프하거나 출력하는 것.

## 절차
1. 사용자가 `kickru.com` 탭을 열어 둔 상태인지 확인한다. localStorage는 같은 출처(origin)에서만 읽힌다.
   없으면 사용자에게 열어 달라고 요청한다.
2. **키 목록만** 먼저 본다 (값은 읽지 않는다). 페이지에서 JavaScript를 실행할 수 있으면:
   ```js
   Object.keys(localStorage).map(k => [k, localStorage.getItem(k).length])
   ```
   실행 도구가 없으면 사용자에게 DevTools → Application → Local Storage → kickru.com 을 보여 달라고 한다.
3. 목록을 사용자에게 보여주고 **덤프할 키를 확인받는다.** 인증 계열 키는 제외한다.
4. 확인받은 키만 덤프한다 (`KEYS`를 해당 키 배열로 바꾼다):
   ```js
   JSON.stringify({
     origin: location.origin,
     dumped_at: new Date().toISOString(),
     keys: Object.fromEntries(KEYS.map(k => [k, localStorage.getItem(k)]))
   })
   ```
5. 결과 문자열을 사용자에게 주고 `kickru-ballon/data/raw/dump_YYYYMMDD.json`으로 저장하게 한다.
   Chrome에서 파일을 쓸 수 없으면 사용자가 복사해 저장한다. `data/raw/`는 git에 올라가지 않는다.
6. 다음 단계(분석 환경에서 사용자가 실행):
   ```
   python3 scripts/ingest.py inspect data/raw/dump_YYYYMMDD.json
   ```
   출력된 구조를 보고 매핑 파일을 작성한 뒤 `ingest.py convert` → `validate.py` → `explore.py` 순서로 진행한다.

## 알려진 구조 (2026-10-23 관측)
메인 세이브 키는 `second-life-football-legends-v2` (약 74만 자). 그 외 `kickru-ranking-*`, `bdo-seen:*` 등은 분석에 필요 없으니 덤프하지 않는다.
값은 JSON 문자열 배열이며, 원소를 한 번 더 파싱하면 `life.history[]`에 시즌 기록과 `ballonRank`가 있다.
변환은 `python3 scripts/from_save.py data/raw/dump_*.json data/real`.

## 신뢰도
위 구조는 한 번의 덤프에서 관측한 것이라 게임 업데이트로 바뀔 수 있다.
키가 없거나 시즌 기록이 보이지 않으면, 그 사실을 그대로 보고하고 가이드의 "커리어 파일 보관"(내보내기) 기능을 확인하게 한다.
추측으로 필드를 채우지 않는다. 읽을 수 없는 값은 null이다.
