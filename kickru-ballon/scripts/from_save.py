"""kickru 세이브 덤프(second-life-football-legends-v2) -> 7장 스키마.

세이브 구조(관측): 키 값 = JSON 문자열 배열, 각 원소를 한 번 더 JSON.parse -> {"life": {...}}.
시즌 기록 = life.history[], 발롱 순위 = history[].ballonRank (없으면 후보 탈락=NC),
수상 = history[].awards[] (발롱도르 수상 시 category=="발롱도르", value/benchmark 포함).

사용:
  python3 scripts/from_save.py data/raw/dump.json data/real [--position ID=POS] [--switch ID=SEASON:POS]

세이브에는 '현재' 포지션만 있고 시즌별 포지션은 없다. 다르게 알고 있으면
--position 으로 시작 포지션을, --switch 로 전환 시즌부터의 포지션을 덮어쓴다.
프로 시즌(path=="professional") 중 'YYYY/YY' 형식의 시즌만 변환한다.
"""
import json
import os
import sys

from common import SEASON_RE, die, load

UCL = "UEFA 챔피언스리그"
UCL_MAP = {
    "우승": "winner", "준우승": "final", "준결승 탈락": "semi", "8강 탈락": "quarter",
    "16강 탈락": "round_of_16", "리그 페이즈 탈락": "league_phase_exit",
    "플레이오프 탈락": "playoff_exit", "조별리그 탈락": "group_exit",
}
LEAGUES = ("라리가", "분데스리가", "세리에 A", "세리에 B", "프리미어리그", "챔피언십",
           "리그 1", "에레디비시", "프리메이라리가", "브라질레이랑 세리 A", "브라질레이랑 세리 B",
           "K리그 1")
AWARD_TOKENS = {"MVP": "MVP", "득점왕": "top_scorer", "도움왕": "assist_leader", "베스트 11": "best11"}


def rank_from_result(res):
    if res == "우승":
        return 1
    if res and res.endswith("위"):
        head = res.split("위")[0].split()[-1]
        return int(head) if head.isdigit() else None
    return None


def convert_life(life, source, position, switch):
    core_id = life["core"]["id"]
    seasons, skipped = [], []
    for h in life["history"]:
        label = h["seasonLabel"]
        if h.get("path") != "professional" or not SEASON_RE.match(label):
            skipped.append(label)
            continue
        # 요약 화면의 합계 = 클럽 stats + 선택된 대표팀 대회 stats (친선 friendlies 제외).
        # Ikarus 2045/46 으로 확인: 클럽 22G17A + 월드컵 2G6A = 24G23A, 평점 7.32 (시드와 일치).
        st = dict(h["stats"])
        selected = [n for n in h.get("nationals", []) if n.get("selected") and isinstance(n.get("stats"), dict)]
        for n in selected:
            for k in ("apps", "starts", "goals", "assists", "ratingSum"):
                st[k] = st.get(k, 0) + n["stats"].get(k, 0)
        apps = st.get("apps")
        rating = round(st["ratingSum"] / apps, 2) if apps and "ratingSum" in st else None
        intl_event = intl_result = None
        if selected:
            intl_event = {"worldCup": "worldcup"}.get(selected[0].get("id"), selected[0].get("id"))
            intl_result = selected[0].get("result")

        league_name = league_res = ucl_res = None
        for r in h["reports"]:
            if r.get("scope") != "club":
                continue
            if r["name"] == UCL:
                ucl_res = r.get("result")
            elif r["name"] in LEAGUES:
                league_name, league_res = r["name"], r.get("result")

        awards, ballon_award = [], None
        for a in h["awards"]:
            if a.get("category") == "발롱도르":
                ballon_award = a
            tok = AWARD_TOKENS.get(a.get("category"))
            if tok and league_name and a["name"].startswith(league_name) and tok not in awards:
                awards.append(tok)

        if ballon_award:
            status, rank = "won", 1
        elif h.get("ballonRank") is not None:
            status, rank = "ranked", h["ballonRank"]
        else:
            status, rank = "not_candidate", None

        pos = position
        if switch and label >= switch[0]:
            pos = switch[1]
        note = ""
        if ucl_res and ucl_res not in UCL_MAP:
            note = f"UCL 원문 결과: {ucl_res}"
        seasons.append(dict(
            season=label, age=h.get("age"), team=h.get("team"), league=league_name, position=pos,
            ovr_start=None, ovr_end=None,  # OVR 위치는 아직 미확인 (core.player 안에 있을 가능성)
            apps=apps, starts=st.get("starts"), goals=st.get("goals"), assists=st.get("assists"),
            avg_rating=rating, league_rank=rank_from_result(league_res),
            ucl_result=UCL_MAP.get(ucl_res), cup_result=None, intl_event=intl_event, intl_result=intl_result,
            awards=awards, ballon_status=status, ballon_rank=rank, note=note,
            source=f"{source}:{core_id}",
            ballon_value=ballon_award["value"] if ballon_award else None,
            ballon_benchmark=ballon_award.get("benchmark") if ballon_award else None,
        ))
    wins = sorted({a["awardYear"] for a in life["careerAwards"] if a.get("category") == "발롱도르"})
    return dict(character_id=core_id, name=life["core"]["player"].get("name"), position=position,
                nationality=life["core"]["player"].get("nationality"), expected_wins=wins,
                seasons=seasons), skipped


def parse_overrides(argv):
    pos, sw, rest = {}, {}, []
    it = iter(argv)
    for a in it:
        if a in ("--position", "--switch"):
            k, _, v = next(it).partition("=")
            if a == "--position":
                pos[k] = v
            else:
                s, _, p = v.partition(":")
                sw[k] = (s, p)
        else:
            rest.append(a)
    return pos, sw, rest


def main(argv):
    pos_over, sw_over, rest = parse_overrides(argv)
    if len(rest) != 2:
        die(__doc__)
    dump = load(rest[0])
    raw = next(iter(dump["keys"].values())) if len(dump["keys"]) == 1 else \
        dump["keys"].get("second-life-football-legends-v2")
    if raw is None:
        die("second-life-football-legends-v2 키가 덤프에 없음")
    os.makedirs(rest[1], exist_ok=True)
    source = f"dump:{dump.get('origin')}:{dump.get('dumped_at')}"
    for el in json.loads(raw):
        life = json.loads(el)["life"] if isinstance(el, str) else el["life"]
        cid = life["core"]["id"]
        pos = pos_over.get(cid, life["core"]["player"].get("position"))
        out, skipped = convert_life(life, source, pos, sw_over.get(cid))
        path = os.path.join(rest[1], f"{cid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"{cid} ({out['name']}, {pos}): 프로 {len(out['seasons'])}시즌 -> {path}; "
              f"제외 {len(skipped)}시즌(학교/아카데미/형식); 수상연도 {out['expected_wins']}")


if __name__ == "__main__":
    main(sys.argv[1:])
