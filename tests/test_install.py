import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("installer", Path(__file__).parents[1] / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_clone_changes_only_agent_and_tab_mod_references(self):
        original = {"children": [{"content": {"mod": "agents"}, "size": {"px": 268}}, {"children": [{"content": {"mod": "tabs"}}, {"content": {"mod": "insights"}}]}], "theme": "paper"}
        result = installer.with_context(original)
        self.assertEqual(original["children"][0]["content"]["mod"], "agents")
        self.assertEqual(result["children"][0]["content"]["mod"], "context-agents")
        self.assertEqual(result["children"][0]["size"], {"px": 268})
        self.assertEqual(result["children"][1]["children"][1]["content"]["mod"], "insights")
        self.assertEqual(result["theme"], "paper")

    def test_incompatible_layout_is_rejected(self):
        with self.assertRaises(ValueError): installer.with_context({"content": {"mod": "win98"}})

    def test_mods_use_identical_context_thresholds_and_freshness_rules(self):
        root = Path(__file__).parents[1] / "mods"
        self.assertEqual((root / "context-agents/model.js").read_text(), (root / "context-tabs/model.js").read_text())
