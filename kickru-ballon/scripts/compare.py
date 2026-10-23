"""시드(수작업) vs 원본 세이브 변환본 대조.

사용: python3 scripts/compare.py data/seed/ikarus.json data/real/career-575943787.json
시드의 null 은 '모름'이므로 비교하지 않는다. 값이 있고 다르면 불일치로 출력한다.
"""
import sys

from common import die, load

FIELDS = ("goals", "assists", "avg_rating", "ballon_status", "ballon_rank", "league_rank", "ucl_result")
TOL = {"avg_rating": 0.011}  # 시드는 소수 2자리 표기


def differs(f, a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and f in TOL:
        return abs(a - b) > TOL[f]
    return a != b


def main(seed_path, real_path):
    seed, real = load(seed_path), load(real_path)
    real_by = {s["season"]: s for s in real["seasons"]}
    n_cmp = n_diff = 0
    only_seed = []
    for s in seed["seasons"]:
        r = real_by.get(s["season"])
        if r is None:
            only_seed.append(s["season"])
            continue
        for f in FIELDS:
            if s[f] is None:
                continue
            n_cmp += 1
            if differs(f, s[f], r[f]):
                n_diff += 1
                print(f"  {s['season']} {f}: 시드={s[f]!r} 원본={r[f]!r}")
    seed_seasons = {s["season"] for s in seed["seasons"]}
    only_real = [x for x in real_by if x not in seed_seasons]
    print(f"{seed['character_id']} vs {real['character_id']}: 비교 {n_cmp}칸, 불일치 {n_diff}")
    if only_seed:
        print(f"  시드에만 있는 시즌: {only_seed}")
    print(f"  원본에만 있는 시즌({len(only_real)}): {only_real}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        die(__doc__)
    main(*sys.argv[1:])
