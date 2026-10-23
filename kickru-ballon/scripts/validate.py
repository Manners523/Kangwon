"""스키마·정합성 검사.

사용: python3 -I scripts/validate.py data/seed/*.json
오류가 있으면 종료 코드 1. 경고는 종료 코드에 영향을 주지 않는다.
"""
import sys

from common import SEASON_KEYS, STATUSES, UCL_VALUES, ballon_year, die, load

MAX_RANK = 50  # 관측 최대 29위. 후보 컷은 미검증이라 여유를 둔 상한.


def check_character(c):
    errors, warnings = [], []
    cid = c.get("character_id", "?")
    seasons = c.get("seasons") or []
    if not seasons:
        errors.append(f"{cid}: seasons 비어 있음")

    won_years = []
    prev_year = None
    for s in seasons:
        tag = f"{cid} {s.get('season')}"
        missing = [k for k in SEASON_KEYS if k not in s]
        if missing:
            errors.append(f"{tag}: 필드 누락 {missing} (결측은 키를 지우지 말고 null)")
            continue

        year = ballon_year(s["season"])
        if year is None:
            errors.append(f"{tag}: 시즌 형식 오류 (예: 2036/37)")
            continue
        if prev_year is not None and year != prev_year + 1:
            warnings.append(f"{tag}: 시즌이 연속이 아님 (이전 {prev_year})")
        prev_year = year

        status, rank = s["ballon_status"], s["ballon_rank"]
        if status not in STATUSES:
            errors.append(f"{tag}: ballon_status={status!r}")
        elif status == "won":
            won_years.append(year)
            if rank != 1:
                errors.append(f"{tag}: won 인데 rank={rank}")
        elif status == "ranked":
            if rank is None:
                if not s["note"]:
                    errors.append(f"{tag}: ranked 인데 rank 없음, note도 없음")
            elif not (2 <= rank <= MAX_RANK):
                errors.append(f"{tag}: ranked rank={rank} (2~{MAX_RANK} 기대)")
        elif rank is not None:
            errors.append(f"{tag}: {status} 인데 rank={rank}")

        r = s["avg_rating"]
        if r is not None and not (0 < r <= 10):
            errors.append(f"{tag}: avg_rating={r}")
        for k in ("goals", "assists", "apps", "starts"):
            v = s[k]
            if v is not None and (not isinstance(v, int) or v < 0):
                errors.append(f"{tag}: {k}={v}")
        if s["ucl_result"] is not None and s["ucl_result"] not in UCL_VALUES:
            errors.append(f"{tag}: ucl_result={s['ucl_result']!r}")
        if s["awards"] is not None and not isinstance(s["awards"], list):
            errors.append(f"{tag}: awards 는 list 또는 null")

        # 문서에서 월드컵은 2038·2042·2046 (시즌 종료 연도 % 4 == 2). 가설이므로 경고만.
        if s["intl_event"] == "worldcup" and year % 4 != 2:
            warnings.append(f"{tag}: 월드컵인데 종료 연도 {year} % 4 != 2")

        o_s, o_e = s["ovr_start"], s["ovr_end"]
        if o_s is not None and o_e is not None and abs(o_e - o_s) > 15:
            warnings.append(f"{tag}: OVR 변화 {o_s}->{o_e} 가 큼 (오독 확인)")

    expected = c.get("expected_wins")
    if expected is not None and sorted(expected) != sorted(won_years):
        errors.append(f"{cid}: 수상 연도 불일치 기대={sorted(expected)} 실제={sorted(won_years)}")
    return errors, warnings


def main(paths):
    if not paths:
        die("사용법: validate.py <json>...")
    n_err = 0
    for p in paths:
        c = load(p)
        errors, warnings = check_character(c)
        n_err += len(errors)
        print(f"{p}: 오류 {len(errors)}, 경고 {len(warnings)}")
        for m in errors:
            print(f"  [오류] {m}")
        for m in warnings:
            print(f"  [경고] {m}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
