"""화면 id + 화면 -> 해야 할 일. 브라우저에 의존하지 않는 순수 함수라 기록 화면으로 테스트할 수 있다.

반환 Decision:
  steps  : 순서대로 실행할 Step 들 (클릭/입력). 대상은 '일치 조건'(match)이고, 드라이버가 실행 직전에 화면을 다시 읽어 찾는다.
  wait   : 아무것도 누르지 않고 잠시 기다린다 (연출 진행 중, 사람의 서명 대기 등).
  stop   : 사람에게 넘기고 멈춘다.
  log    : 선택지 전체와 고른 값 (분석용).
"""
import re
from dataclasses import dataclass, field

import screens as sc

SAFE_UNKNOWN_WORDS = ("확인", "다음", "계속")  # --explore 에서 UNKNOWN 화면에 한해 누를 수 있는 버튼 글자


@dataclass
class Step:
    kind: str                 # click | type
    text: str = None          # 버튼 첫 줄이 정확히 일치
    cls: str = None           # 클래스 부분문자열
    tag: str = None
    nth: int = 0              # 조건에 맞는 것 중 n 번째
    value: str = None         # type 일 때 입력할 글자
    text_re: str = None       # 첫 줄 정규식 (text 대신)


@dataclass
class Decision:
    steps: list = field(default_factory=list)
    wait: float = 0.0
    stop: str = None
    log: dict = field(default_factory=dict)


def first_line(e):
    return (e.get("text") or "").split("\n")[0].strip()


def wage_manwon(text):
    """'연봉 5.4억 원' -> 54000, '연봉 3,000만 원' -> 3000 (만 원 단위). 못 읽으면 None."""
    m = re.search(r"연봉\s*([\d,.]+)\s*(억|만)", text or "")
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    return v * 10000 if m.group(2) == "억" else v


def click(text=None, **kw):
    return Step("click", text=text, **kw)


def decide(sid, screen, policy):
    li = sc.find_buttons(screen, cls="t-li")

    if sid == "NOTICE_DIALOG":
        return Decision([click("확인", cls="t-primary")])
    if sid == "LANDING":
        return Decision([click("새로운 인생 시작하기")], log={"action": "new_career"})
    if sid == "CREATE_AVATAR":
        return Decision([click("이 아바타로 할게요")])
    if sid == "CREATE_PROFILE":
        return Decision([Step("type", tag="input", nth=0, value=policy.career_name), click("다음")],
                        log={"career_name": policy.career_name, "note": "포지션/국적/학교는 기본값"})
    if sid == "CREATE_STYLE":
        n = len(sc.find_buttons(screen, cls="su-cand"))
        i = policy.style_index if 0 <= policy.style_index < n else policy.rng.randrange(n)
        names = [first_line(e) for e in sc.find_buttons(screen, cls="su-cand")]
        return Decision([click(cls="su-cand", nth=i), click("이 스타일로 할게요")],
                        log={"options": names, "picked": names[i]})
    if sid == "CREATE_FOCUS":
        make = sc.find_button(screen, text="선수 만들기", enabled=False)
        if make is not None and not make.get("disabled"):
            # 이미 무언가 선택되어 활성화된 상태: 다시 누르면 선택이 해제될 수 있으니 확정만 누른다
            return Decision([click("선수 만들기")], log={"picked": "(이미 선택됨)"})
        return Decision([click(a, tag="button") for a in policy.focus] + [click("선수 만들기")],
                        log={"picked": list(policy.focus)})
    if sid == "CREATE_CONFIRM":
        return Decision([Step("click", text_re=r"시즌 시작$")])
    if sid == "SEASON_INTRO":
        return Decision([Step("click", text_re=r"시즌 보내기$")])
    if sid == "SEASON_ADVANCE":
        return Decision([Step("click", text_re=r"시즌 보내기$")])
    if sid == "SEASON_END":
        return Decision([click("확인", cls="t-primary")])
    if sid == "TAB_PLAYER":
        return Decision([click("홈", cls="t-tab")])
    if sid == "HOME":
        for e in li:
            if re.search(r"제안이 .*왔어요|전환점이 찾아왔어요", first_line(e)):
                return Decision([click(first_line(e), cls="t-li")], log={"pending": first_line(e)})
        return Decision(stop="홈에서 처리할 대기 항목도 시즌 보내기 버튼도 보이지 않음")

    if sid == "TURNING_POINT_OPEN":
        return Decision([click("이야기 확인하기")])
    if sid == "TURNING_POINT_CHOICE":
        title = next((l for l in sc.lines(screen) if "전환점" in l), "")
        opts = [e for e in sc.find_buttons(screen, cls="t-choice")]
        names = [first_line(e) for e in opts]
        if policy.turning_point == "first":
            i = 0
        elif policy.turning_point == "last":
            i = len(opts) - 1
        else:
            i = policy.rng.randrange(len(opts))
        return Decision([click(cls="t-choice", nth=i)],
                        log={"options": names, "picked": names[i], "rule": policy.turning_point})
    if sid == "CHOICE_RESULT":
        return Decision([click("다음", cls="primary wide")])

    if sid in ("CONTRACT_LIST", "CONTRACT_NEXT_PATH"):
        offers = [{"label": first_line(e), "detail": (e.get("text") or "").replace("\n", " "),
                   "wage_manwon": wage_manwon(e.get("text"))} for e in li]
        if not offers:
            return Decision(stop="계약 화면인데 선택 항목을 찾지 못함")
        if sid == "CONTRACT_NEXT_PATH":
            school = [o for o in offers if "진급" in o["label"]]
            clubs = [o for o in offers if "진급" not in o["label"]]
            pick = (clubs[0] if clubs and policy.youth_path == "club" else (school or clubs)[0])
        else:
            stay = [o for o in offers if o["label"].startswith("소속팀에 남기")]
            others = [o for o in offers if not o["label"].startswith("소속팀에 남기")]
            if policy.contract == "best_offer" and others:
                ranked = sorted(others, key=lambda o: o["wage_manwon"] or 0, reverse=True)
                pick = ranked[0]
            else:
                pick = (stay or others)[0]
        return Decision([click(pick["label"], cls="t-li")],
                        log={"options": offers, "picked": pick["label"], "rule": policy.contract})
    if sid == "CONTRACT_NEED_SIGNATURE":
        return Decision(wait=3.0, log={"note": "직접 서명 대기 (사람이 서명 칸에 그린다)"})
    if sid == "CONTRACT_SIGNING":
        return Decision(wait=1.5)
    if sid == "CONTRACT_CONFIRM":
        return Decision([click("계약하기", cls="t-primary")], log={"action": "sign_contract"})

    if sid == "NATIONAL_CALLUP":
        return Decision([click("대표팀 합류" if policy.nt_callup == "join" else "소속팀에 집중")],
                        log={"picked": policy.nt_callup})
    if sid == "NATIONAL_RESULT":
        return Decision([click("정규시즌 진행")])
    if sid == "NATIONAL_RESULT_WAIT":
        return Decision(wait=1.5)

    if sid == "MATCH_KICKOFF":
        return Decision([click("결과만 보기" if policy.match_view == "result_only" else "결승전 시작")])
    if sid == "MATCH_LIVE":
        return Decision([click("중계 건너뛰기")])
    if sid == "MATCH_HALFTIME":
        return Decision([click("건너뛰기")])
    if sid == "MATCH_FULLTIME":
        return Decision([click("결과 확인")])

    if sid == "BALLON_AWARD":
        return Decision([click("건너뛰기", cls="bdo-skip")],
                        log={"award_text": " / ".join(sc.lines(screen)[:8])})

    if sid == sc.UNKNOWN:
        return Decision(stop="인식하지 못한 화면")
    return Decision(stop=f"규칙 없는 화면 id: {sid}")


def explore_safe_click(screen):
    """UNKNOWN 화면에서 --explore 일 때만: 차단 목록에 걸리지 않는 '확인/다음/계속' 버튼 하나. 없으면 None."""
    for e in sc.buttons(screen):
        if sc.is_blocked(e) or e.get("disabled"):
            continue
        if first_line(e) in SAFE_UNKNOWN_WORDS:
            return Decision([click(first_line(e), cls=(e.get("cls") or None))], log={"explore": True})
    return None
