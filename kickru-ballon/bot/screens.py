"""화면 분류기. 브라우저에 의존하지 않는 순수 함수.

입력은 recon.py 가 저장하는 screen.json 과 같은 형식:
  {"text": "<보이는 텍스트>", "interactive": [{"tag","text","cls","disabled",...}, ...]}

분류 결과는 (screen_id, evidence). 규칙에 맞지 않으면 UNKNOWN 이고, 드라이버는 UNKNOWN 에서 멈춘다.
규칙은 2026-10-23 에 사용자가 직접 한 커리어 1개(화면 300개)를 기록한 것에서 만들었다.
기록에 없는 화면(상점 구매, 은퇴 이후, 부상, 병역 결과, 주장·포지션 제안 등)은 일부러 규칙을 만들지 않았다.
"""
import re

UNKNOWN = "UNKNOWN"

# 드라이버가 어떤 경우에도 누르면 안 되는 요소 (클래스 부분 문자열 / 텍스트 정규식).
BLOCKED_CLS = ("t-retire-now", "t-support", "rx-like", "t-nat-retire", "kickru-footer", "t-icon-btn", "t-lang", "t-notice-btn")
BLOCKED_TEXT = re.compile(
    r"지금 은퇴하기|국가대표 은퇴 선언|서버비|의견 보내기|현역 입대|상무 지원|이적 요청|임대 요청|"
    r"개인정보|이용약관|사이트맵|서비스 소개|게임 가이드|support@|연봉 인상 협상 요청"
)

_HIDE = ("벤치에서 발롱까지", "💸", "개발자 서버비 내주기", "시즌")


def lines(screen):
    return [l.strip() for l in screen.get("text", "").split("\n") if l.strip()]


def buttons(screen):
    return [e for e in screen.get("interactive", []) if e.get("tag") in ("button", "a")]


def has_text(screen, s):
    return any(s in l for l in lines(screen))


def find_button(screen, text=None, cls=None, enabled=True):
    """첫 줄 텍스트가 text 와 일치하고 cls 부분문자열을 가진 버튼을 찾는다. 없으면 None."""
    for e in buttons(screen):
        first = (e.get("text") or "").split("\n")[0].strip()
        if text is not None and first != text:
            continue
        if cls is not None and cls not in (e.get("cls") or ""):
            continue
        if enabled and e.get("disabled"):
            continue
        return e
    return None


def find_buttons(screen, cls=None, text_re=None):
    out = []
    for e in buttons(screen):
        first = (e.get("text") or "").split("\n")[0].strip()
        if cls is not None and cls not in (e.get("cls") or ""):
            continue
        if text_re is not None and not re.search(text_re, first):
            continue
        out.append(e)
    return out


def is_blocked(element):
    """차단 목록에 걸리는 요소인지. 드라이버는 클릭 직전에 반드시 이 함수를 거친다."""
    cls = element.get("cls") or ""
    if any(b in cls for b in BLOCKED_CLS):
        return True
    return bool(BLOCKED_TEXT.search((element.get("text") or "")))


def classify(screen):
    t = "\n".join(lines(screen))

    # 결승/대회 경기 연출
    if re.search(r"· (준?결승|[0-9]+강)", t) and "KICK OFF" in t:
        return "MATCH_KICKOFF", "KICK OFF"
    if re.search(r"· (준?결승|[0-9]+강)", t) and "HALF TIME" in t:
        return "MATCH_HALFTIME", "HALF TIME"
    if re.search(r"· (준?결승|[0-9]+강)", t) and "FULL TIME" in t:
        return "MATCH_FULLTIME", "FULL TIME"
    if re.search(r"· (준?결승|[0-9]+강)", t) and "LIVE" in t:
        return "MATCH_LIVE", "LIVE"

    # 발롱도르 연출
    if find_button(screen, cls="bdo-skip"):
        return "BALLON_AWARD", "bdo-skip"

    # 대표팀
    if find_button(screen, text="대표팀 합류"):
        return "NATIONAL_CALLUP", "대표팀 합류 버튼"
    if "국가대표 대회 결과" in t:
        if find_button(screen, text="정규시즌 진행"):
            return "NATIONAL_RESULT", "국가대표 대회 결과 + 정규시즌 진행 활성"
        if find_button(screen, text="정규시즌 진행", enabled=False):
            return "NATIONAL_RESULT_WAIT", "정규시즌 진행 비활성 (시즌 시뮬레이션 중)"

    # 전환점 / 선택 결과
    if find_buttons(screen, cls="t-choice"):
        return "TURNING_POINT_CHOICE", "t-choice 버튼"
    if "전환점" in t and find_button(screen, text="이야기 확인하기"):
        return "TURNING_POINT_OPEN", "이야기 확인하기"
    if "나의 선택" in t and find_button(screen, text="다음", cls="primary wide"):
        return "CHOICE_RESULT", "나의 선택 + 다음"

    # 계약 흐름 (서명은 사람이 한다)
    if "다음 진로" in t or "계약과 진로" in t:
        if "직접 서명" in t and find_button(screen, text="계약하기", enabled=False) and \
                not find_button(screen, text="계약하기"):
            return "CONTRACT_NEED_SIGNATURE", "직접 서명 + 계약하기 비활성"
        if "서명 중" in t or "서명하는 중" in t:
            return "CONTRACT_SIGNING", "서명 중"
        if find_button(screen, text="계약하기"):
            return "CONTRACT_CONFIRM", "계약하기 활성"
        if "다음 진로" in t:
            return "CONTRACT_NEXT_PATH", "다음 진로 목록"
        return "CONTRACT_LIST", "계약과 진로 목록"

    # 캐릭터 생성 확인 팝업 (집중 육성 화면 위에 겹쳐 뜬다. 뒤 화면의 제목이 그대로 남아 있다)
    if find_button(screen, text="다시 보기") and find_buttons(screen, text_re=r"시즌 시작$"):
        return "CREATE_CONFIRM", "다시 보기 + 시즌 시작 팝업"

    # 공지 팝업 (랜딩 위에 뜬다)
    if "‹ 목록" in t and find_button(screen, text="확인", cls="t-primary"):
        return "NOTICE_DIALOG", "공지 팝업"

    # 캐릭터 생성
    if "이 아바타로 할게요" in t or "선수의 모습을" in t:
        return "CREATE_AVATAR", "아바타 선택"
    if "어떤 선수로" in t:
        return "CREATE_PROFILE", "이름/번호/포지션/발"
    if "플레이 스타일을" in t and find_buttons(screen, cls="su-cand"):
        return "CREATE_STYLE", "su-cand"
    if "집중해서 키울 능력치를" in t:
        return "CREATE_FOCUS", "집중 육성 능력치"
    if find_button(screen, text="새로운 인생 시작하기"):
        return "LANDING", "새로운 인생 시작하기"

    # 시즌 진행
    if re.search(r"시즌을 앞두고 있어요", t):
        return "SEASON_INTRO", "시즌을 앞두고"
    if re.search(r"시즌이 끝났어요", t) and find_button(screen, text="확인", cls="t-primary"):
        return "SEASON_END", "시즌이 끝났어요 + 확인"
    if find_buttons(screen, text_re=r"시즌 보내기$"):
        return "SEASON_ADVANCE", "시즌 보내기 버튼"

    # 하단 탭 화면 (선수 탭에는 누를 것이 없다. 홈 탭으로 돌아가야 한다)
    if lines(screen)[:1] == ["선수"] and "파란색은 집중 육성" in t:
        return "TAB_PLAYER", "선수 탭"

    # 홈
    if "확인할 일" in t or ("통산 경기" in t and find_button(screen, cls="t-retire-now")):
        return "HOME", "홈 카드"

    return UNKNOWN, "일치하는 규칙 없음"
