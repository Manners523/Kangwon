# kickru-ballon

"벤치에서 발롱까지"(https://kickru.com/)의 발롱도르 판정을 **관측 데이터로 추정**하기 위한 1단계 도구입니다.
게임을 대신 플레이하지 않습니다.

## 구성

| 경로 | 역할 |
|---|---|
| `SKILL.md` | Chrome에서 쓰는 수집 스킬 (localStorage 읽기 전용 덤프) |
| `data/seed/*.json` | 직접 옮겨 적은 시드 (Ikarus 13행, 데이터A 16행. 순위 확인 시즌은 이보다 적음) |
| `data/raw/` | 수집한 덤프 (git 제외) |
| `scripts/validate.py` | 스키마·정합성 검사 |
| `scripts/explore.py` | 포지션별 기술통계, 순위 상관 |
| `scripts/ingest.py` | 덤프 구조 확인(`inspect`)과 변환(`convert`) |
| `tests/` | `python3 -m unittest discover -s tests` |

파이썬 3 표준 라이브러리만 씁니다 (3.13에서 확인).

## 실행

```
python3 scripts/validate.py data/seed/*.json
python3 scripts/explore.py data/seed/*.json
python3 -m unittest discover -s tests
```

`python3 -I`는 스크립트 폴더를 import 경로에서 빼므로 쓰지 마세요. 대신 데이터가 있는 폴더가 아니라 이 폴더에서 실행합니다.

## 스키마와 결측

문서 7장 스키마에 `position`(시즌별, 전환 시즌 구분용), `source`를 더했습니다.
결측은 **0이 아니라 null**이며 분석에서 제외합니다. `ballon_status`는 `won / ranked / not_candidate / unknown`입니다.

- `not_candidate`(NC)는 점수 0이 아니라 "후보 컷 밖"입니다. 순위는 null이며, 순위 상관에서는 가정을 명시한 별도 표로만 다룹니다.
- 시드는 화면을 보고 옮긴 값이라 오독 가능성이 있습니다 (`source: seed:docx-3`). 실제 세이브와 대조되면 `source`가 바뀝니다.

## 시드 데이터에서 확인된 것 / 확인 안 된 것

확인된 것(데이터 자체의 사실):
- 수상 연도 6개가 문서와 일치: Ikarus 2037·2040·2041·2045, 데이터A 2033·2036.
- UCL 우승이 수상의 **충분조건이 아님**: Ikarus 34/35는 리그·UCL 우승인데 8위.

확인 안 된 것(이 데이터로 판별 불가):
- 후보 컷, 상대평가 여부(H9), 월드컵 효과(H6), 포지션별 기준.
- 회귀·가중치. 표본이 캐릭터당 10여 시즌이라 하지 않았습니다.

데이터 안의 의문점:
- Ikarus 42/43은 평점 7.64, G+A 59인데 NC입니다. 같은 캐릭터의 8위(7.48)나 26위(7.32)보다 지표가 좋습니다.
  리그 2위가 원인일 수 있으나(H8, 가설) 표본 1개라 단정할 수 없고, 오기록일 가능성도 있습니다. 실제 세이브와 먼저 대조하세요.
- 문서 7장 예시의 "2036/37 나이 29"와 3장의 "46/47에 38세"는 서로 맞지 않습니다(10시즌 차이라면 39세). 그래서 `age`는 비웠습니다.

## 다음 단계의 조건

1. 사용자가 Chrome에서 localStorage 키 구조를 확인해 `ingest.py inspect` 결과를 가져온다.
2. 시드를 원본과 대조해 `source`를 갱신한다.
3. 자동 플레이는 `https://kickru.com/terms`를 사용자가 확인한 뒤에만 검토한다.

## Chrome 스킬로 쓰기

`SKILL.md`가 스킬 본체입니다. Claude in Chrome이 이 폴더를 어떻게 불러오는지(업로드 형식 등)는 이 환경에서 확인하지 못했습니다.
스킬 업로드가 필요하면 `SKILL.md`만 담은 폴더를 압축해 쓰세요. 분석 스크립트는 Chrome 쪽에서 실행되지 않을 수 있습니다.
