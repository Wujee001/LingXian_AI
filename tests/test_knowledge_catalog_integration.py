# -*- coding: utf-8 -*-
"""泠弦智谱知识库—318类目录回归测试，编写：@zjx (2026-10-27)。

可从项目根目录执行：
  python -m unittest discover -s tests -p test_knowledge_catalog_integration.py -v
"""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from service.knowledge_catalog import get_knowledge, knowledge_counts, list_knowledge
from service.parser import char_parse
from service.attribute_parser import parse_attributes
from api.knowledge import library, detail, search


class KnowledgeCatalogRegressionTests(unittest.TestCase):
    def test_coverage(self):
        self.assertEqual(knowledge_counts(), {
            "total": 318, "legacy_detail": 25, "registry_candidate": 293
        })
        self.assertEqual(len(list_knowledge()), 318)

    def test_legacy_meaning_unchanged(self):
        item = get_knowledge("da_9_gou_4")
        self.assertEqual(item["knowledge_status"], "legacy_detail")
        self.assertEqual(item["left_hand"]["finger"], "大指")
        self.assertIn("四弦九徽", item["meaning"])

    def test_new_key_does_not_fake_fingering(self):
        item = get_knowledge("tui_7")
        self.assertEqual(item["knowledge_status"], "registry_candidate")
        self.assertTrue(item["needs_meaning_review"])
        self.assertIsNone(item["right_hand"])
        self.assertIsNone(item["left_hand"])
        self.assertIsNone(item["is_san"])
        self.assertIn("待", item["meaning"])
        self.assertEqual(char_parse("tui_7")["knowledge_status"], "registry_candidate")

    def test_unregistered_key_not_invented(self):
        self.assertIsNone(get_knowledge("not_a_class"))
        self.assertEqual(char_parse("not_a_class")["knowledge_status"], "unknown_key")

    def test_library_and_search(self):
        self.assertEqual(library(None)["count"], 318)
        self.assertEqual(library("已有释义")["count"], 25)
        self.assertEqual(library("待复核")["count"], 293)
        self.assertEqual(detail("tui_7")["data"]["knowledge_status"], "registry_candidate")
        found = search("tui_7")
        self.assertGreaterEqual(found["count"], 1)
        # 所有候选的共同占位语句不能导致关键词检索污染。
        self.assertLess(search("复")["count"], 100)

    def test_stage2_fields_are_not_faked_into_class_id(self):
        r = parse_attributes({
            "rh": "gou", "string": "4", "lh": "da", "hui_base": "9",
            "hui_frac": "0", "mod": "NA", "tone": "an", "strings": "NA"
        })
        self.assertIsNone(r["class_key"])
        self.assertEqual(r["knowledge_status"], "field_candidate")
        self.assertFalse(r["is_confirmed"])
        self.assertIn("勾", r["meaning"])


if __name__ == "__main__":
    unittest.main()
