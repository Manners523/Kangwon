"""시드/수집 데이터 공통 로더. 표준 라이브러리만 사용한다."""
import json
import re
import sys

SEASON_RE = re.compile(r"^(\d{4})/(\d{2})$")
STATUSES = ("won", "ranked", "not_candidate", "unknown")
UCL_VALUES = (
    "winner", "final", "semi", "quarter", "round_of_16",
    "league_phase_exit", "not_qualified",
)
SEASON_KEYS = (
    "season", "age", "team", "league", "position", "ovr_start", "ovr_end",
    "apps", "starts", "goals", "assists", "avg_rating", "league_rank",
    "ucl_result", "cup_result", "intl_event", "intl_result", "awards",
    "ballon_status", "ballon_rank", "note", "source",
)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ballon_year(season):
    """시즌 종료 연도 (문서 2장: 2032/33 -> 2033). 형식이 틀리면 None."""
    m = SEASON_RE.match(season or "")
    if not m:
        return None
    start = int(m.group(1))
    end2 = int(m.group(2))
    return start + 1 if (start + 1) % 100 == end2 else None


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)
