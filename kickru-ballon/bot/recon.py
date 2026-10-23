"""화면 기록 도구 (읽기 전용). 자동 플레이 드라이버를 짜기 전에 실제 DOM 을 보기 위한 것.

사용자가 열린 브라우저에서 직접 게임을 진행한다. 이 스크립트는 화면이 바뀔 때마다
  - 보이는 텍스트, 상호작용 요소(버튼/링크/입력/선택) 목록, 스크린샷, (선택) HTML
을 data/recon/<run>/NNN_*/ 에 저장한다.
클릭, 입력, 이동, localStorage 접근, 추가 서버 요청을 하지 않는다 (DOM 읽기만).

실행 (사용자 PC):
  pip install playwright && playwright install chromium
  python3 bot/recon.py --url https://kickru.com/ --profile .pw-profile

인자:
  --interval 초   화면 변화 확인 주기 (기본 1.5, 최소 0.5). 로컬 DOM 읽기라 서버 요청은 없다.
  --html          전체 HTML 도 저장 (용량 큼).
  --max N         저장할 화면 최대 수 (기본 1000).
종료: 터미널에서 Ctrl+C.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

INTERACTIVE_JS = r"""
() => {
  const sel = 'button, a[href], input, select, textarea, canvas, [role=button], [role=tab], [role=menuitem], [onclick], [tabindex]';
  const seen = new Set();
  const out = [];
  const nodes = [];
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  const push = (el) => {
    if (seen.has(el) || !vis(el)) return;
    seen.add(el);
    const r = el.getBoundingClientRect();
    const data = {};
    for (const a of el.attributes) if (a.name.startsWith('data-')) data[a.name] = a.value;
    nodes.push(el);
    out.push({
      idx: out.length,
      tag: el.tagName.toLowerCase(),
      text: (el.innerText || el.value || '').trim().slice(0, 120),
      id: el.id || null,
      cls: (el.className && el.className.toString().slice(0, 120)) || null,
      role: el.getAttribute('role'),
      aria: el.getAttribute('aria-label'),
      type: el.getAttribute('type'),
      href: el.tagName === 'A' ? el.getAttribute('href') : null,
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      data,
      box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    });
  };
  document.querySelectorAll(sel).forEach(push);
  // 클릭 가능해 보이는 div/span (cursor:pointer)
  document.querySelectorAll('div, span, li, label').forEach(el => {
    if (getComputedStyle(el).cursor === 'pointer') push(el);
  });
  window.__kbEls = nodes;  // 클릭 대상 해석용 (페이지 JS 전역 변수일 뿐 DOM 은 바뀌지 않는다)
  return out.slice(0, 300);
}
"""

TEXT_JS = "() => document.body ? document.body.innerText : ''"


def signature(page):
    text = page.evaluate(TEXT_JS)
    # 시계/숫자 애니메이션이 서명을 계속 바꾸지 않도록 숫자는 뭉갠다
    stable = re.sub(r"\d+", "#", text)
    return page.url + "|" + hashlib.sha1(stable.encode("utf-8")).hexdigest()


def snapshot(page, outdir, n, with_html):
    d = os.path.join(outdir, f"{n:03d}")
    os.makedirs(d, exist_ok=True)
    meta = {
        "n": n, "url": page.url, "title": page.title(),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "viewport": page.viewport_size,
        "text": page.evaluate(TEXT_JS),
        "interactive": page.evaluate(INTERACTIVE_JS),
    }
    with open(os.path.join(d, "screen.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    page.screenshot(path=os.path.join(d, "screen.png"))
    if with_html:
        with open(os.path.join(d, "page.html"), "w", encoding="utf-8") as f:
            f.write(page.content())
    return meta


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="https://kickru.com/")
    ap.add_argument("--profile", default=".pw-profile")
    ap.add_argument("--out", default=os.path.join("data", "recon"))
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--headless", action="store_true", help="테스트용. 평소에는 창을 보며 직접 진행한다.")
    ap.add_argument("--chrome", default=os.environ.get("KICKRU_CHROME"), help="브라우저 실행 파일 경로(선택)")
    ap.add_argument("--duration", type=float, default=0, help="초. 0이면 Ctrl+C까지")
    args = ap.parse_args(argv)
    args.interval = max(0.5, args.interval)

    from playwright.sync_api import sync_playwright

    run = time.strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(args.out, run)
    os.makedirs(outdir, exist_ok=True)
    print(f"저장 위치: {outdir}  (Ctrl+C 로 종료)")
    last, n = None, 0
    with sync_playwright() as p:
        kw = {"headless": args.headless, "viewport": {"width": 1280, "height": 900}}
        if args.chrome:
            kw["executable_path"] = args.chrome
        ctx = p.chromium.launch_persistent_context(args.profile, **kw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)
        start = time.time()
        try:
            while n < args.max and (not args.duration or time.time() - start < args.duration):
                try:
                    sig = signature(page)
                    if sig != last:
                        n += 1
                        meta = snapshot(page, outdir, n, args.html)
                        print(f"[{n:03d}] {meta['url']}  버튼 {len(meta['interactive'])}개  "
                              f"{meta['text'][:40].strip()!r}")
                        last = sig
                except Exception as e:  # 페이지 전환 중 evaluate 실패는 다음 주기에 재시도
                    print(f"  (건너뜀: {type(e).__name__})", file=sys.stderr)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass
        ctx.close()
    print(f"{n}개 화면 저장 완료: {outdir}")


if __name__ == "__main__":
    main(sys.argv[1:])
