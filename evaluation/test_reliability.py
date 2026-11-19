"""Regression checks for mixed requests and evidence validation."""
import json
import unittest

from campus.knowledge import Knowledge, requested_sections
from campus.live import Live
from campus.service import Offline, Session, Turn, invoke_tool


class ReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = Knowledge()

    def test_mixed_material_requests(self):
        queries = [
            "\u6821\u56ed\u5361\u4e22\u4e86\u9700\u8981\u54ea\u4e9b\u6750\u6599\uff0c\u53bb\u54ea\u91cc\u529e\uff1f",
            "\u5b66\u751f\u8bc1\u4e22\u4e86\u8981\u5e26\u4ec0\u4e48\uff0c\u54ea\u4e2a\u7a97\u53e3\u529e\u7406\uff0c\u5468\u672b\u5f00\u653e\u5417\uff1f",
            "\u6821\u56ed\u5361\u8865\u529e\u9700\u8981\u54ea\u4e9b\u6750\u6599\uff0c\u8d39\u7528\u662f\u591a\u5c11\uff1f",
        ]
        for mode in ("rag", "full"):
            for query in queries:
                with self.subTest(mode=mode, query=query):
                    turn = Offline(self.kb, mode).ask(query, Session())
                    self.assertIn("\u7f3a\u5c11\uff1a", turn.answer)
                    read = self.kb.read(turn.citations[0]["guide_id"])
                    available = {row["section"] for row in read["evidence"]}
                    expected = requested_sections(query) & available
                    actual = {row["section"] for row in turn.citations}
                    self.assertTrue(expected <= actual)
                    self.assertIn("\u6240\u9700\u6750\u6599", actual)
                    self.assertEqual(turn.answer.count("\u6765\u6e90\uff08\u6a21\u62df\u8d44\u6599\uff09"), 1)

    def test_live_materials_use_checked_results_and_details(self):
        for mode in ("rag", "full"):
            with self.subTest(mode=mode):
                live = object.__new__(Live)
                live.knowledge, live.mode = self.kb, mode
                turn = Turn("\u6821\u56ed\u5361\u4e22\u4e86\u9700\u8981\u54ea\u4e9b\u6750\u6599\uff0c\u53bb\u54ea\u91cc\u529e\uff1f", mode, "fixture_http", "test")
                invoke_tool(self.kb, turn, "check_materials", guide_id="campus-card",
                            provided_items=[], conditions={})
                answer = live._validated_answer(turn, "ignored")
                self.assertIn("\u7f3a\u5c11\uff1a", answer)
                self.assertIn("\u529e\u7406\u5730\u70b9", answer)
                self.assertEqual({row["section"] for row in turn.citations},
                                 {"\u6240\u9700\u6750\u6599", "\u529e\u7406\u5730\u70b9"})

    def response(self, answer, refs):
        turn = Turn("\u5b66\u751f\u8bc1\u8865\u529e", "full", "fixture_http", "test")
        row = {"ref": "test-ref", "guide_name": "Fixture", "guide_id": "student-id",
               "section": "\u529e\u7406\u8d39\u7528", "version": "1.0.0",
               "text": "\u8d39\u7528\u4e3a20\u5143\u3002\u5f00\u653e\u65f6\u95f4\u4e3a08:30\u3002"}
        turn.evidence[row["ref"]] = row
        live = object.__new__(Live)
        live._validated_answer(turn, json.dumps({"status": "answer", "answer": answer, "refs": refs}))
        return turn

    def test_accepts_citations_before_and_after_punctuation(self):
        for answer in ("\u8d39\u7528\u4e3a20\u5143\u3002[[test-ref]]", "\u8d39\u7528\u4e3a20\u5143[[test-ref]]\u3002"):
            self.assertIsNone(self.response(answer, ["test-ref"]).error)

    def test_rejects_missing_inline_reference(self):
        self.assertEqual(self.response("\u8d39\u7528\u4e3a20\u5143\u3002", ["test-ref"]).error, "EvidenceValidationError")

    def test_rejects_uncited_sentence(self):
        self.assertEqual(self.response("\u8d39\u7528\u4e3a20\u5143[[test-ref]]\u3002\u5f53\u5929\u529e\u597d\u3002", ["test-ref"]).error,
                         "EvidenceValidationError")

    def test_rejects_unknown_reference(self):
        self.assertEqual(self.response("\u8d39\u7528\u4e3a20\u5143[[unknown]]\u3002", ["test-ref"]).error,
                         "EvidenceValidationError")

    def test_rejects_unsupported_fee_and_time(self):
        for answer in ("\u8d39\u7528\u4e3a99\u5143[[test-ref]]\u3002", "\u5f00\u653e\u65f6\u95f4\u4e3a09:30[[test-ref]]\u3002"):
            self.assertEqual(self.response(answer, ["test-ref"]).error, "EvidenceValidationError")


if __name__ == "__main__":
    unittest.main()
