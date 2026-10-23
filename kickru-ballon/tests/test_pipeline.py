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

import from_save  # noqa: E402
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
    def test_double_encoded_array_and_div(self):
        inner = {"life": {"history": [
            {"seasonLabel": "2030/31", "stats": {"goals": 3, "apps": 10, "ratingSum": 70.0}},
            {"seasonLabel": "2031/32", "stats": {"goals": 1, "apps": 0, "ratingSum": 0}},
        ]}}
        raw = json.dumps([json.dumps(inner), json.dumps({})])
        m = {"key": "save", "seasons_path": "0.life.history",
             "character": {"character_id": "x", "position": "CAM"},
             "fields": {"season": "seasonLabel", "goals": "stats.goals",
                        "avg_rating": {"div": ["stats.ratingSum", "stats.apps"]}}}
        with tempfile.TemporaryDirectory() as d:
            p = {n: os.path.join(d, n) for n in ("dump", "map", "out")}
            for n, o in (("dump", {"origin": "o", "dumped_at": "t", "keys": {"save": raw}}), ("map", m)):
                with open(p[n], "w", encoding="utf-8") as f:
                    json.dump(o, f)
            with contextlib.redirect_stdout(io.StringIO()):
                ingest.convert(p["dump"], p["map"], p["out"])
            s = load(p["out"])["seasons"]
            self.assertEqual(s[0]["avg_rating"], 7.0)
            self.assertIsNone(s[1]["avg_rating"])  # 출장 0 -> 0이 아니라 null

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


def _season(label, ballon_rank=None, ballon_award=False, nationals=None):
    awards = [{"category": "발롱도르", "name": "x 발롱도르", "value": 5.0, "benchmark": 4.0}] if ballon_award else []
    h = {"seasonLabel": label, "year": int(label[:4]), "path": "professional", "age": 25, "team": "T",
         "stats": {"apps": 40, "starts": 40, "goals": 20, "assists": 10, "ratingSum": 300.0},
         "reports": [{"name": "라리가", "scope": "club", "result": "우승"},
                     {"name": "UEFA 챔피언스리그", "scope": "club", "result": "준결승 탈락"}],
         "awards": awards, "nationals": nationals or []}
    if ballon_rank is not None:
        h["ballonRank"] = ballon_rank
    return h


class FromSaveTests(unittest.TestCase):
    def convert(self, history):
        life = {"core": {"id": "c1", "player": {"name": "n", "position": "ST", "nationality": "kr"},
                         "history": [{"year": 2030, "overall": 80}, {"year": 2031, "overall": 83}]},
                "storyLog": [{"year": 2030, "kind": "choice", "title": "t", "picked": "a", "others": ["b"]}],
                "history": history, "careerAwards": [{"category": "발롱도르", "awardYear": 2031}]}
        return from_save.convert_life(life, "src", "ST", None)[0]["seasons"]

    def test_status_mapping(self):
        s = self.convert([_season("2030/31", ballon_award=True), _season("2031/32", ballon_rank=3),
                          _season("2032/33")])
        self.assertEqual([(x["ballon_status"], x["ballon_rank"]) for x in s],
                         [("won", 1), ("ranked", 3), ("not_candidate", None)])
        self.assertEqual(s[0]["ballon_value"], 5.0)
        self.assertEqual(s[0]["ucl_result"], "semi")
        self.assertEqual(s[0]["league_rank"], 1)

    def test_ovr_and_decisions(self):
        s = self.convert([_season("2030/31"), _season("2031/32")])
        self.assertEqual((s[0]["ovr_start"], s[0]["ovr_end"]), (80, 83))
        self.assertIsNone(s[1]["ovr_end"])  # 다음 해 값이 없으면 null
        self.assertEqual(s[0]["decisions"][0]["picked"], "a")
        self.assertEqual(s[1]["decisions"], [])

    def test_national_stats_are_added_to_totals(self):
        nat = [{"selected": True, "id": "worldCup", "result": "준우승 · 2위",
                "stats": {"apps": 10, "starts": 10, "goals": 5, "assists": 0, "ratingSum": 100.0}}]
        s = self.convert([_season("2030/31", nationals=nat)])[0]
        self.assertEqual((s["goals"], s["apps"], s["avg_rating"]), (25, 50, 8.0))
        self.assertEqual(s["intl_event"], "worldcup")

    def test_school_and_odd_labels_skipped(self):
        h = _season("2026")
        h2 = _season("2027/28"); h2["path"] = "school"
        self.assertEqual(self.convert([h, h2]), [])


if __name__ == "__main__":
    unittest.main()
