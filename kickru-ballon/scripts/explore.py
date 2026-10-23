"""기술통계 중심 탐색. 회귀식은 맞추지 않는다 (표본이 너무 작음).

사용: python3 scripts/explore.py data/seed/*.json
캐릭터(=포지션)별로 따로 출력한다. 합쳐서 분석하지 않는다 (문서 4장 교란 요인).
"""
import sys

from common import die, load

MIN_N = 8  # 이보다 적으면 상관을 계산해도 출력만 하고 경고한다.
NC_RANK = 31  # 가정: 후보 컷 밖은 '31위 이하 동률'로 취급 (검열 데이터의 민감도 확인용)


def avg_ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    rx, ry = avg_ranks(xs), avg_ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if dx == 0 or dy == 0 else num / (dx * dy)


def features(s):
    ga = None
    if s["goals"] is not None and s["assists"] is not None:
        ga = s["goals"] + s["assists"]
    awards = s["awards"]
    return {
        "rating": s["avg_rating"],
        "ga": ga,
        "ucl_win": None if s["ucl_result"] is None else s["ucl_result"] == "winner",
        "mvp": None if awards is None else "MVP" in awards,
    }


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def fmt(v, nd=2):
    return "-" if v is None else f"{v:.{nd}f}"


def share(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return f"{sum(vals)}/{len(vals)}" if vals else "-"


def analyze(c):
    cid, pos = c["character_id"], c["position"]
    seasons = c["seasons"]
    labeled = [s for s in seasons if s["ballon_status"] != "unknown"]
    # 포지션이 다르면 골/도움의 가치가 다를 수 있으므로 분석에서 뺀다 (문서 4장).
    other_pos = [s["season"] for s in labeled if (s["position"] or pos) != pos]
    labeled = [s for s in labeled if (s["position"] or pos) == pos]
    rows = []
    for s in labeled:
        f = features(s)
        f.update(season=s["season"], status=s["ballon_status"], rank=s["ballon_rank"],
                 note=s["note"])
        rows.append(f)
    complete = [r for r in rows if r["rating"] is not None and r["ga"] is not None]

    print(f"\n=== {cid} ({pos}) ===")
    print(f"전체 시즌 {len(seasons)} / 수상 결과 확인 {len(labeled)} / "
          f"평점·골·도움 모두 있음 {len(complete)}")
    if other_pos:
        print(f"제외: 다른 포지션 시즌 {other_pos}")

    print("\n[시즌표: 평점 내림차순]  rank=수상 순위, NC=후보 아님")
    print(f"{'season':8} {'결과':>6} {'평점':>5} {'G+A':>4} {'UCL우승':>7} {'MVP':>4}  비고")
    for r in sorted(complete, key=lambda r: -r["rating"]):
        res = "WON" if r["status"] == "won" else (
            "NC" if r["status"] == "not_candidate" else
            (f"{r['rank']}위" if r["rank"] else "?위"))
        ucl = "-" if r["ucl_win"] is None else ("Y" if r["ucl_win"] else "N")
        mvp = "-" if r["mvp"] is None else ("Y" if r["mvp"] else "N")
        print(f"{r['season']:8} {res:>6} {r['rating']:5.2f} {r['ga']:4d} {ucl:>7} {mvp:>4}  {r['note']}")

    print("\n[수상 vs 비수상 평균]")
    groups = (("WON", [r for r in complete if r["status"] == "won"]),
              ("비수상", [r for r in complete if r["status"] != "won"]))
    for name, g in groups:
        print(f"  {name:6} n={len(g):2d}  평점 {fmt(mean([r['rating'] for r in g]))}  "
              f"G+A {fmt(mean([r['ga'] for r in g]), 1)}  "
              f"UCL우승 {share(g, 'ucl_win')}  MVP {share(g, 'mvp')}")

    ranked = [r for r in complete if r["status"] in ("won", "ranked") and r["rank"] is not None]
    print(f"\n[순위와의 Spearman 상관]  (순위 숫자가 작을수록 좋음 → 음수면 '높을수록 상위')")
    for label, pool, cap in (
        ("순위 확인 시즌만", ranked, None),
        (f"NC={NC_RANK}위 동률로 가정 (가정이며 검증 안 됨)",
         [r for r in complete if r["status"] != "unknown" and
          (r["rank"] is not None or r["status"] == "not_candidate")], NC_RANK),
    ):
        rk = [r["rank"] if r["rank"] is not None else cap for r in pool]
        for key in ("rating", "ga"):
            rho = spearman([r[key] for r in pool], rk)
            print(f"  {label}: {key:6} n={len(pool):2d} rho={fmt(rho)}")
        if len(pool) < MIN_N:
            print(f"  경고: n={len(pool)} < {MIN_N}. 해석하지 말 것.")

    print("\n[UCL 우승 시즌의 수상 결과]  (H2 점검: 우승이 수상의 충분조건이 아님을 볼 것)")
    for r in rows:
        if r["ucl_win"]:
            res = "WON" if r["status"] == "won" else ("NC" if r["status"] == "not_candidate"
                                                      else f"{r['rank']}위")
            print(f"  {r['season']}  {res:>4}  평점 {fmt(r['rating'])}  G+A {r['ga']}")


def main(paths):
    if not paths:
        die("사용법: explore.py <json>...")
    for p in paths:
        analyze(load(p))
    print("\n※ 탐색용 기술통계다. p값·회귀 없음. 후보 컷, 상대평가 여부, 포지션별 기준은 이 데이터로 판별 불가.")


if __name__ == "__main__":
    main(sys.argv[1:])
