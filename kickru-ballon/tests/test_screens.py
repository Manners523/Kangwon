"""화면 분류기 테스트. 픽스처는 2026-10-23 사용자가 기록한 실제 화면(유형별 대표)이다.

주의: 규칙을 이 기록으로 만들었기 때문에, 여기서 통과하는 것만으로는 분류기가 맞다는 증거가 아니다.
실제 사이트 위에서의 검증은 driver --dry-run 으로 한다.
"""
import glob
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bot"))

import screens  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "screens")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


class ClassifyTests(unittest.TestCase):
    def test_fixtures_match_expected_ids(self):
        with open(os.path.join(FIX, "expected.json"), encoding="utf-8") as f:
            expected = json.load(f)
        self.assertGreaterEqual(len(expected), 30)
        for name, want in expected.items():
            got, _ = screens.classify(load(name))
            self.assertEqual(got, want, name)

    def test_unknown_for_gibberish(self):
        self.assertEqual(screens.classify({"text": "알 수 없는 화면", "interactive": []})[0], screens.UNKNOWN)
        self.assertEqual(screens.classify({"text": "", "interactive": []})[0], screens.UNKNOWN)

    def test_signature_step_needs_human(self):
        # 직접 서명이 필요한 화면은 드라이버가 누를 수 있는 '계약하기'가 없다
        with open(os.path.join(FIX, "expected.json"), encoding="utf-8") as f:
            fx = [n for n, v in json.load(f).items() if v == "CONTRACT_NEED_SIGNATURE"]
        self.assertTrue(fx)
        for n in fx:
            self.assertIsNone(screens.find_button(load(n), text="계약하기"))


class BlockedTests(unittest.TestCase):
    def test_blocked_elements(self):
        blocked = [
            {"tag": "button", "text": "지금 은퇴하기", "cls": "t-btn t-grey t-retire-now"},
            {"tag": "button", "text": "💸\n개발자 서버비 내주기", "cls": "t-support"},
            {"tag": "button", "text": "46", "cls": "rx-like"},
            {"tag": "button", "text": "국가대표 은퇴 선언", "cls": "t-nat-retire"},
            {"tag": "button", "text": "현역 입대", "cls": "t-btn t-grey"},
            {"tag": "button", "text": "상무 지원", "cls": "t-btn t-weak"},
            {"tag": "button", "text": "이적 요청", "cls": "t-btn t-weak t-btn-sm"},
            {"tag": "button", "text": "💬 의견 보내기", "cls": "t-btn t-weak"},
            {"tag": "a", "text": "이용약관", "cls": ""},
        ]
        for e in blocked:
            self.assertTrue(screens.is_blocked(e), e)

    def test_normal_buttons_not_blocked(self):
        for e in ({"tag": "button", "text": "2034/35 시즌 보내기", "cls": "t-btn t-primary"},
                  {"tag": "button", "text": "확인", "cls": "t-btn t-primary"},
                  {"tag": "button", "text": "소속팀에 남기\n잔류", "cls": "t-li"},
                  {"tag": "button", "text": "새로운 방식을 익힌다", "cls": "t-choice"}):
            self.assertFalse(screens.is_blocked(e), e)

    def test_every_blocked_fixture_element_is_flagged_consistently(self):
        # 픽스처 전체에서 은퇴/후원/좋아요 요소가 하나도 빠짐없이 차단 목록에 걸린다
        seen = 0
        for p in glob.glob(os.path.join(FIX, "[0-9]*.json")):
            for e in load(os.path.basename(p))["interactive"]:
                cls, text = e.get("cls") or "", e.get("text") or ""
                if "t-retire-now" in cls or "t-support" in cls or "rx-like" in cls or "지금 은퇴하기" in text:
                    seen += 1
                    self.assertTrue(screens.is_blocked(e), (p, e))
        self.assertGreater(seen, 0)


if __name__ == "__main__":
    unittest.main()
