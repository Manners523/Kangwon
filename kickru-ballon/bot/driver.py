"""감독형 자동 플레이 드라이버.

  python bot/driver.py --name exp-001 --max-actions 40          # 첫 점검: 40 액션만
  python bot/driver.py --name exp-001                           # 이어서 계속
  python bot/driver.py --dry-run                                # 현재 화면을 판단만 하고 종료 (클릭 없음)

안전 장치 (모두 기본 켜짐):
  - 화면을 인식하지 못하면(UNKNOWN) 클릭하지 않고 화면을 data/recon/unknown_*/ 에 저장한 뒤 멈춘다.
  - screens.is_blocked() 에 걸리는 요소(은퇴/후원/좋아요/병역/이적·임대 요청 등)는 누르지 않는다.
  - 모든 조작은 limits.Pacer 를 거친다 (bot/config.json). 새 커리어 시작은 하루 한도를 확인한다.
  - 작업 폴더에 STOP 파일을 만들거나 Ctrl+C 를 누르면 현재 액션 뒤에 멈춘다.
  - 같은 화면에서 진행이 안 되면 멈춘다.
  - 직접 서명 화면은 누르지 않고 기다린다. 창에서 직접 서명하면 이어서 진행한다.
종료할 때 이 사이트의 세이브 키 하나를 읽기 전용으로 data/raw/dump_*.json 에 저장한다 (쓰기 없음).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

import actions as ac
import limits
import recon
import screens as sc
from policy import Policy

SAVE_KEY = "second-life-football-legends-v2"
MAX_WAITS = 200      # wait 결정이 연속으로 이 횟수를 넘으면 멈춘다 (서명 대기 약 10분)
MAX_REPEATS = 6      # 클릭했는데 화면이 그대로인 횟수 한도


class Halt(Exception):
    pass


class NotReady(Exception):
    """대상은 있는데 비활성이다 (연출/시뮬레이션 진행 중). 멈추지 않고 기다린다."""


# 같은 화면 id 에서 연속으로 액션을 한 횟수 한도. 지문(해시)이 번갈아 바뀌어도 잡는다.
MAX_SAME_SID = 6
SAME_SID_EXEMPT = {"MATCH_LIVE": 40, "SEASON_ADVANCE": 15}


def read_screen(page):
    return {"url": page.url, "text": page.evaluate(recon.TEXT_JS), "interactive": page.evaluate(recon.INTERACTIVE_JS)}


def stable_hash(text):
    """숫자(연속된 자리 전체)를 무시한 화면 지문. 점수·시계가 바뀌어도 같은 화면으로 본다."""
    return hashlib.sha1(re.sub(r"\d+", "#", text).encode("utf-8")).hexdigest()[:12]


def resolve(step, screen):
    """Step 의 일치 조건에 맞는 요소를 화면에서 찾는다. 없으면 None."""
    tag = step.tag or ("input" if step.kind == "type" else None)
    hits = []
    for e in screen["interactive"]:
        if tag is None and e["tag"] not in ("button", "a"):
            continue
        if tag is not None and e["tag"] != tag:
            continue
        first = (e.get("text") or "").split("\n")[0].strip()
        if step.text is not None and first != step.text:
            continue
        if step.text_re is not None:
            if not re.search(step.text_re, first):
                continue
        if step.cls is not None and step.cls not in (e.get("cls") or ""):
            continue
        hits.append(e)
    return hits[step.nth] if step.nth < len(hits) else None


def execute(page, step, pacer, dry):
    el = None
    for _ in range(6):  # 비활성 버튼이 켜지길 잠깐 기다린다
        el = resolve(step, read_screen(page))
        if el is not None and not el["disabled"]:
            break
        time.sleep(0.5)
    else:
        if el is not None:
            raise NotReady(str(step))
        raise Halt(f"클릭 대상을 찾지 못함: {step}")
    if sc.is_blocked(el):
        raise Halt(f"차단 목록 요소라 누르지 않음: {el.get('text')!r} {el.get('cls')!r}")
    shown = (el.get("text") or "").split("\n")[0][:30] or el["tag"]
    label = f"{step.kind} {shown!r}"
    if dry:
        return label
    pacer.wait()
    x, y, visible = page.evaluate(
        "(i) => { const el = window.__kbEls[i]; el.scrollIntoView({block: 'center'});"
        " const r = el.getBoundingClientRect(); const x = r.x + r.width / 2, y = r.y + r.height / 2;"
        " const top = document.elementFromPoint(x, y);"
        " return [x, y, !!top && (el.contains(top) || top.contains(el))]; }", el["idx"])
    if not visible:  # 팝업 등에 가려진 요소는 누르지 않는다
        raise Halt(f"대상이 다른 요소에 가려져 있어 누르지 않음: {shown!r}")
    page.mouse.click(x, y)
    if step.kind == "type":
        page.keyboard.press("Control+A")
        page.keyboard.type(step.value, delay=60)
    return label


def snapshot_unknown(page, screen, outroot, why):
    d = os.path.join(outroot, "unknown_" + time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(d, exist_ok=True)
    meta = dict(screen, captured_at=time.strftime("%Y-%m-%dT%H:%M:%S"), why=why)
    with open(os.path.join(d, "screen.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    try:
        page.screenshot(path=os.path.join(d, "screen.png"))
    except Exception:
        pass
    return d


def dump_save(page, rawdir):
    try:
        val = page.evaluate("(k) => localStorage.getItem(k)", SAVE_KEY)
    except Exception:
        return None
    if not val:
        return None
    os.makedirs(rawdir, exist_ok=True)
    path = os.path.join(rawdir, "dump_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"origin": "https://kickru.com", "dumped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "keys": {SAVE_KEY: val}}, f, ensure_ascii=False)
    return path


def run(page, args, policy, cfg):
    pacer = limits.Pacer(cfg)
    budget = limits.DailyCareerBudget(cfg, os.path.join(args.data, ".career_budget.json"))
    os.makedirs(os.path.join(args.data, "runs"), exist_ok=True)
    logf = open(os.path.join(args.data, "runs", time.strftime("%Y%m%d_%H%M%S") + ".jsonl"), "w", encoding="utf-8")

    def log(rec):
        logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logf.flush()

    log({"event": "start", "policy": policy.as_dict(), "limits": cfg, "explore": args.explore, "dry_run": args.dry_run})
    last_key, repeats, waits, acted = None, 0, 0, 0
    last_sid, same_sid = None, 0
    while acted < args.max_actions:
        if os.path.exists(args.stop_file):
            print("STOP 파일 감지: 종료합니다.")
            return "stop-file"
        screen = read_screen(page)
        sid, evidence = sc.classify(screen)
        key = (sid, stable_hash(screen["text"]))
        dec = ac.decide(sid, screen, policy)
        if dec.stop and sid == sc.UNKNOWN and args.explore:
            dec = ac.explore_safe_click(screen) or dec
        tick = {"event": "tick", "t": time.strftime("%H:%M:%S"), "screen": sid, "evidence": evidence, "log": dec.log}

        if dec.stop:
            d = snapshot_unknown(page, screen, os.path.join(args.data, "recon"), dec.stop)
            print(f"멈춤: {sid} - {dec.stop}\n화면 저장: {d}")
            log(dict(tick, event="halt", reason=dec.stop, snapshot=d))
            return "halt"
        if dec.wait:
            waits = waits + 1 if key == last_key else 1
            if waits > MAX_WAITS:
                print("기다림이 너무 길어 멈춥니다.")
                return "wait-timeout"
            if waits == 1:
                print(f"[대기] {sid} {dec.log.get('note', '')}")
            last_key = key
            if args.dry_run:
                print(f"[dry-run] {sid}: 대기")
                return "dry-run"
            time.sleep(dec.wait)
            continue
        waits = 0
        if sid == "LANDING" and not args.dry_run and not budget.start_career():
            print("오늘의 커리어 시작 한도에 도달했습니다.")
            return "daily-budget"

        labels = []
        try:
            for step in dec.steps:
                labels.append(execute(page, step, pacer, args.dry_run))
        except NotReady as e:
            waits = waits + 1 if key == last_key else 1
            last_key = key
            if waits > MAX_WAITS:
                print("버튼이 계속 비활성이라 멈춥니다.")
                return "wait-timeout"
            if waits == 1:
                print(f"[대기] {sid}: 버튼이 아직 비활성 ({e})")
            time.sleep(1.5)
            continue
        acted += 1
        same_sid = same_sid + 1 if sid == last_sid else 1
        last_sid = sid
        cap = SAME_SID_EXEMPT.get(sid, MAX_SAME_SID)
        if same_sid > cap:
            d = snapshot_unknown(page, read_screen(page), os.path.join(args.data, "recon"),
                                 f"{sid} 에서 {same_sid - 1}번 연속 액션했지만 진행되지 않음")
            print(f"같은 화면({sid})에서 {same_sid - 1}번 연속 액션해 멈춥니다. 화면 저장: {d}")
            log(dict(tick, event="halt", reason="same-sid", snapshot=d))
            return "stuck-sid"
        print(f"[{acted:03d}] {sid:22} -> {'; '.join(labels)}" + (f"   {dec.log.get('picked', '')}" if dec.log.get("picked") else ""))
        log(dict(tick, steps=labels))
        if args.dry_run:
            return "dry-run"

        time.sleep(0.6)
        repeats = repeats + 1 if key == last_key else 0
        last_key = key
        if repeats >= MAX_REPEATS:
            d = snapshot_unknown(page, read_screen(page), os.path.join(args.data, "recon"), "진행 없음")
            print(f"같은 화면이 {MAX_REPEATS}번 반복되어 멈춥니다. 화면 저장: {d}")
            return "stuck"
    return "max-actions"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="https://kickru.com/")
    ap.add_argument("--profile", default=".pw-profile")
    ap.add_argument("--data", default="data")
    ap.add_argument("--stop-file", default="STOP")
    ap.add_argument("--name", default="exp-001", help="캐릭터 이름 (실험 커리어임이 드러나게)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--turning-point", default="random", choices=["random", "first", "last"])
    ap.add_argument("--contract", default="stay", choices=["stay", "best_offer"])
    ap.add_argument("--youth-path", default="club", choices=["club", "school"])
    ap.add_argument("--nt-callup", default="join", choices=["join", "decline"])
    ap.add_argument("--match-view", default="result_only", choices=["result_only", "watch"])
    ap.add_argument("--max-actions", type=int, default=400)
    ap.add_argument("--dry-run", action="store_true", help="현재 화면을 판단만 하고 종료 (클릭 없음)")
    ap.add_argument("--explore", action="store_true",
                    help="UNKNOWN 화면에서 '확인/다음/계속' 버튼만 눌러 본다 (그 외는 멈춤)")
    ap.add_argument("--headless", action="store_true", help="테스트용")
    ap.add_argument("--chrome", default=os.environ.get("KICKRU_CHROME"))
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)

    cfg = limits.load_limits(args.config)
    policy = Policy(name="pilot", seed=args.seed, turning_point=args.turning_point, contract=args.contract,
                    youth_path=args.youth_path, nt_callup=args.nt_callup, match_view=args.match_view,
                    career_name=args.name)

    from playwright.sync_api import sync_playwright
    result = "error"
    with sync_playwright() as p:
        kw = {"headless": args.headless, "viewport": {"width": 1280, "height": 900}}
        if args.chrome:
            kw["executable_path"] = args.chrome
        ctx = p.chromium.launch_persistent_context(args.profile, **kw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)
        time.sleep(2)
        try:
            result = run(page, args, policy, cfg)
        except Halt as e:
            print(f"멈춤: {e}")
            result = "halt"
        except KeyboardInterrupt:
            result = "interrupted"
        finally:
            path = None if args.dry_run else dump_save(page, os.path.join(args.data, "raw"))
            if path:
                print(f"세이브 덤프(읽기 전용): {path}")
            try:
                ctx.close()
            except Exception:  # Ctrl+C 로 브라우저 연결이 먼저 끊긴 경우 등
                pass
    print(f"종료: {result}")


if __name__ == "__main__":
    main(sys.argv[1:])
