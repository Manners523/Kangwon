import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bot"))

import limits  # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


class LimitsTests(unittest.TestCase):
    def cfg(self, **kw):
        c = limits.load_limits()
        c.update(kw)
        return c

    def test_shipped_config_is_valid_and_conservative(self):
        c = limits.load_limits()
        self.assertEqual(c["max_parallel_browsers"], 1)
        self.assertGreaterEqual(c["min_seconds_between_actions"], 2)

    def test_null_value_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            c = limits.load_limits()
            c["max_careers_per_day"] = None
            with open(p, "w") as f:
                json.dump(c, f)
            with self.assertRaises(SystemExit):
                limits.load_limits(p)

    def test_min_gap_enforced(self):
        fc = FakeClock()
        p = limits.Pacer(self.cfg(action_jitter_seconds=0), fc.now, fc.sleep, lambda: 0)
        p.wait()
        p.wait()
        self.assertAlmostEqual(fc.t, 2.5)

    def test_per_minute_cap(self):
        fc = FakeClock()
        p = limits.Pacer(self.cfg(min_seconds_between_actions=1, action_jitter_seconds=0,
                                  max_actions_per_minute=5, pause_every_n_actions=0), fc.now, fc.sleep, lambda: 0)
        stamps = []
        for _ in range(11):
            p.wait()
            stamps.append(fc.t)
        # 어떤 60초 창에도 5개를 넘지 않는다
        for i, t0 in enumerate(stamps):
            self.assertLessEqual(sum(1 for t in stamps[i:] if t - t0 < 60), 5)

    def test_daily_budget(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "b.json")
            cfg = self.cfg(max_careers_per_day=2)
            b = limits.DailyCareerBudget(cfg, path, today="2030-01-01")
            self.assertTrue(b.start_career())
            self.assertTrue(b.start_career())
            self.assertFalse(b.start_career())
            self.assertEqual(b.remaining(), 0)
            nxt = limits.DailyCareerBudget(cfg, path, today="2030-01-02")
            self.assertEqual(nxt.remaining(), 2)


if __name__ == "__main__":
    unittest.main()
