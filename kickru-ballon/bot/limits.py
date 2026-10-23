"""속도 제한. 드라이버의 모든 클릭/입력/이동은 Pacer.wait() 를 거쳐야 한다.

config.json 의 값이 null 이거나 없으면 실행을 거부한다. 읽기 전용 recon.py 는 해당 없음(조작을 하지 않음).
"""
import json
import os
import random
import time
from collections import deque

REQUIRED = ("max_parallel_browsers", "min_seconds_between_actions", "action_jitter_seconds",
            "max_actions_per_minute", "max_careers_per_day", "pause_every_n_actions", "pause_seconds")
HERE = os.path.dirname(os.path.abspath(__file__))


def load_limits(path=None):
    with open(path or os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    bad = [k for k in REQUIRED if not isinstance(cfg.get(k), (int, float)) or cfg[k] < 0]
    if bad:
        raise SystemExit(f"config.json 제한 값이 비었거나 잘못됨: {bad}")
    if cfg["max_parallel_browsers"] != 1:
        raise SystemExit("max_parallel_browsers 는 1 만 지원한다 (동시 실행 미구현)")
    if cfg["min_seconds_between_actions"] < 1 or cfg["max_actions_per_minute"] < 1:
        raise SystemExit("제한 값이 0 이거나 너무 작다")
    return cfg


class Pacer:
    def __init__(self, cfg, clock=time.monotonic, sleep=time.sleep, rng=random.random):
        self.cfg, self.clock, self.sleep, self.rng = cfg, clock, sleep, rng
        self.recent = deque()  # 최근 1분 액션 시각
        self.last = None
        self.total = 0

    def wait(self):
        """다음 액션 직전에 호출. 필요한 만큼 잠든 뒤 반환한다."""
        c = self.cfg
        now = self.clock()
        if self.last is not None:
            gap = c["min_seconds_between_actions"] + self.rng() * c["action_jitter_seconds"]
            if now - self.last < gap:
                self.sleep(gap - (now - self.last))
                now = self.clock()
        while self.recent and now - self.recent[0] >= 60:
            self.recent.popleft()
        if len(self.recent) >= c["max_actions_per_minute"]:
            self.sleep(60 - (now - self.recent[0]))
            now = self.clock()
            while self.recent and now - self.recent[0] >= 60:
                self.recent.popleft()
        self.total += 1
        if c["pause_every_n_actions"] and self.total % int(c["pause_every_n_actions"]) == 0:
            self.sleep(c["pause_seconds"])
            now = self.clock()
        self.recent.append(now)
        self.last = now


class DailyCareerBudget:
    """하루 커리어 수 제한. 날짜별 카운트를 파일에 저장해 재실행해도 유지한다."""

    def __init__(self, cfg, path=".career_budget.json", today=None):
        self.limit, self.path = int(cfg["max_careers_per_day"]), path
        self.today = today or time.strftime("%Y-%m-%d")

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            return d.get("count", 0) if d.get("date") == self.today else 0
        except (OSError, ValueError):
            return 0

    def remaining(self):
        return max(0, self.limit - self._read())

    def start_career(self):
        """커리어 시작 직전에 호출. 한도를 넘었으면 False."""
        n = self._read()
        if n >= self.limit:
            return False
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"date": self.today, "count": n + 1}, f)
        return True
