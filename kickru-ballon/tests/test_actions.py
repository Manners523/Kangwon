"""결정 로직 테스트 (기록 화면 사용). 브라우저 불필요."""
import json
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bot"))

import actions as ac  # noqa: E402
import driver  # noqa: E402
import screens as sc  # noqa: E402
from policy import Policy  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "screens")


def fixtures():
    with open(os.path.join(FIX, "expected.json"), encoding="utf-8") as f:
        exp = json.load(f)
    for name, sid in sorted(exp.items()):
        with open(os.path.join(FIX, name), encoding="utf-8") as f:
            yield name, sid, json.load(f)


class DecideTests(unittest.TestCase):
    def test_every_fixture_has_a_decision_and_no_step_hits_a_blocked_element(self):
        n_steps = 0
        for name, sid, scr in fixtures():
            d = ac.decide(sid, scr, Policy())
            self.assertTrue(d.steps or d.wait or d.stop, (name, sid))
            for st in d.steps:
                el = driver.resolve(st, scr)
                if el is None:
                    continue  # 앞 단계 클릭 후에야 나타나는 요소(예: 확인 버튼)는 여기서 못 찾을 수 있다
                n_steps += 1
                self.assertFalse(sc.is_blocked(el), (name, sid, st, el.get("text")))
        self.assertGreater(n_steps, 20)

    def test_focus_confirm_popup_is_not_taken_for_focus_screen(self):
        # 실제 사고: 선수 만들기 후 확인 팝업이 뜨면 뒤 화면 제목이 남아 CREATE_FOCUS 로 오분류되어 무한 반복
        scr = json.load(open(os.path.join(FIX, "010.json"), encoding="utf-8"))
        sid, _ = sc.classify(scr)
        self.assertEqual(sid, "CREATE_CONFIRM")
        d = ac.decide(sid, scr, Policy())
        el = driver.resolve(d.steps[0], scr)
        self.assertEqual(el["text"], "고1 시즌 시작")

    def test_focus_selection_is_idempotent(self):
        before = json.load(open(os.path.join(FIX, "009.json"), encoding="utf-8"))
        d = ac.decide("CREATE_FOCUS", before, Policy())
        self.assertEqual([s.text for s in d.steps], ["슈팅", "피지컬", "선수 만들기"])
        after = json.loads(json.dumps(before))
        for e in after["interactive"]:
            if e.get("text") == "선수 만들기":
                e["disabled"] = False  # 선택이 되어 확정 버튼이 켜진 상태
        d2 = ac.decide("CREATE_FOCUS", after, Policy())
        self.assertEqual([s.text for s in d2.steps], ["선수 만들기"])  # 다시 눌러 선택을 해제하지 않는다

    def test_unknown_stops(self):
        d = ac.decide(sc.UNKNOWN, {"text": "x", "interactive": []}, Policy())
        self.assertTrue(d.stop)
        self.assertFalse(d.steps)

    def test_signature_screen_waits_for_human(self):
        for _, sid, scr in fixtures():
            if sid == "CONTRACT_NEED_SIGNATURE":
                d = ac.decide(sid, scr, Policy())
                self.assertGreater(d.wait, 0)
                self.assertFalse(d.steps)

    def test_wage_parser(self):
        self.assertEqual(ac.wage_manwon("1군 주전 · 연봉 5.4억 원"), 54000)
        self.assertEqual(ac.wage_manwon("육성팀 배정 · 연봉 3,000만 원"), 3000)
        self.assertIsNone(ac.wage_manwon("연봉 없음"))

    def test_contract_policies(self):
        scr = next(s for _, sid, s in fixtures() if sid == "CONTRACT_LIST")
        stay = ac.decide("CONTRACT_LIST", scr, Policy(contract="stay"))
        self.assertTrue(stay.log["picked"].startswith("소속팀에 남기"))
        best = ac.decide("CONTRACT_LIST", scr, Policy(contract="best_offer"))
        self.assertFalse(best.log["picked"].startswith("소속팀에 남기"))
        self.assertGreater(len(best.log["options"]), 1)  # 오퍼 목록이 로그에 남는다

    def test_turning_point_rules_and_seed_reproducible(self):
        scr = next(s for _, sid, s in fixtures() if sid == "TURNING_POINT_CHOICE")
        first = ac.decide("TURNING_POINT_CHOICE", scr, Policy(turning_point="first"))
        last = ac.decide("TURNING_POINT_CHOICE", scr, Policy(turning_point="last"))
        self.assertEqual(first.log["picked"], first.log["options"][0])
        self.assertEqual(last.log["picked"], last.log["options"][-1])
        a = [ac.decide("TURNING_POINT_CHOICE", scr, Policy(seed=7)).log["picked"] for _ in range(1)]
        b = [ac.decide("TURNING_POINT_CHOICE", scr, Policy(seed=7)).log["picked"] for _ in range(1)]
        self.assertEqual(a, b)

    def test_explore_clicks_only_safe_words(self):
        safe = {"text": "?", "interactive": [
            {"tag": "button", "text": "지금 은퇴하기", "cls": "t-btn t-grey t-retire-now", "disabled": False},
            {"tag": "button", "text": "확인", "cls": "t-btn t-primary", "disabled": False}]}
        d = ac.explore_safe_click(safe)
        self.assertEqual(d.steps[0].text, "확인")
        unsafe = {"text": "?", "interactive": [
            {"tag": "button", "text": "구매하기", "cls": "t-btn t-primary", "disabled": False}]}
        self.assertIsNone(ac.explore_safe_click(unsafe))

    def test_stable_hash_ignores_digits(self):
        self.assertEqual(driver.stable_hash("골 12 도움 5"), driver.stable_hash("골 7 도움 9"))


if __name__ == "__main__":
    unittest.main()
