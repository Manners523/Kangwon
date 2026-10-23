"""가짜 덤프로 ingest -> validate 흐름을 확인한다. 실제 kickru 포맷이 아니다."""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ingest  # noqa: E402
import validate  # noqa: E402
from common import ballon_year, load  # noqa: E402
from explore import spearman  # noqa: E402

SEEDS = [os.path.join(ROOT, "data", "seed", n) for n in ("ikarus.json", "data_a.json")]

FAKE_SAVE = {"career": {"seasons": [
    {"label": "2030/31", "stats": {"goals": 10}, "ballon": {"rank": None, "result": "NC"}},
    {"label": "2031/32", "stats": {"goals": 20}, "ballon": {"rank": 1, "result": "WON"}},
]}}
FAKE_DUMP = {"origin": "https://example.invalid", "dumped_at": "2000-01-01T00:00:00Z",
             "keys": {"save": json.dumps(FAKE_SAVE)}}
FAKE_MAP = {"key": "save", "seasons_path": "career.seasons",
            "character": {"character_id": "fake", "position": "ST", "nationality": None},
            "fields": {"season": "label", "goals": "stats.goals",
                       "ballon_status": "ballon.result", "ballon_rank": "ballon.rank"},
            "value_maps": {"ballon_status": {"WON": "won", "NC": "not_candidate"}}}


class SeedTests(unittest.TestCase):
    def test_seeds_validate(self):
        for p in SEEDS:
            errors, _ = validate.check_character(load(p))
            self.assertEqual(errors, [], p)

    def test_ballon_year(self):
        self.assertEqual(ballon_year("2032/33"), 2033)
        self.assertEqual(ballon_year("1999/00"), 2000)
        self.assertIsNone(ballon_year("2032/34"))

    def test_validator_catches_wrong_win_years(self):
        c = copy.deepcopy(load(SEEDS[0]))
        c["expected_wins"] = [2037]
        errors, _ = validate.check_character(c)
        self.assertTrue(any("수상 연도 불일치" in e for e in errors))

    def test_validator_catches_won_with_bad_rank(self):
        c = copy.deepcopy(load(SEEDS[1]))
        for s in c["seasons"]:
            if s["ballon_status"] == "won":
                s["ballon_rank"] = 3
                break
        errors, _ = validate.check_character(c)
        self.assertTrue(any("won 인데" in e for e in errors))

    def test_spearman_known_values(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertIsNone(spearman([1, 1, 1], [1, 2, 3]))


class IngestTests(unittest.TestCase):
    def test_inspect_and_convert(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {n: os.path.join(d, n) for n in ("dump", "map", "out")}
            for name, obj in (("dump", FAKE_DUMP), ("map", FAKE_MAP)):
                with open(paths[name], "w", encoding="utf-8") as f:
                    json.dump(obj, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ingest.inspect(paths["dump"])
                ingest.convert(paths["dump"], paths["map"], paths["out"])
            self.assertIn("career", buf.getvalue())

            out = load(paths["out"])
            self.assertEqual([s["ballon_status"] for s in out["seasons"]],
                             ["not_candidate", "won"])
            self.assertIsNone(out["seasons"][0]["assists"])  # 결측은 0이 아니라 null
            errors, _ = validate.check_character(out)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
