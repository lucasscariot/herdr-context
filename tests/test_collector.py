import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("collector", Path(__file__).parents[1] / "mods/context-agents/collector.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


class ContextCollectorTests(unittest.TestCase):
    def test_claude_footer_includes_only_context_not_weekly_limits(self):
        result = c.parse_screen("model · medium   context 81% (810k/1M)   5h 25% · week 10%", "claude-code")
        self.assertEqual(result["percent"], 81)
        self.assertEqual(result["capacity"], 1000000)
        self.assertIsNone(c.parse_screen("week 81% · 5h 90%", "claude-code"))

    def test_cursor_footer(self):
        self.assertEqual(c.parse_screen("  Auto Balance · 63.2% · 82 files edited     Run Everything", "cursor")["percent"], 63.2)
        self.assertIsNone(c.parse_screen("coverage 98%", "cursor"))

    def test_codex_remaining_footer(self):
        self.assertEqual(c.parse_screen("12% context left", "codex")["percent"], 88)
        self.assertEqual(c.parse_screen("0% context left", "codex")["percent"], 100)

    def test_old_screen_content_and_grok_compaction_are_not_meters(self):
        screen = "context 95% (190k/200k)\n" + "\n".join(["current screen"] * 20)
        self.assertIsNone(c.parse_screen(screen, "claude-code"))
        self.assertIsNone(c.parse_screen("Context 80% full. Compacting…\nContext compacted: 206.0k → 25.8k tokens", "grok"))

    def test_current_request_not_cumulative_tokens_and_compaction_reset(self):
        event = {"type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"total_tokens": 410000}, "total_token_usage": {"total_tokens": 12000000}, "model_context_window": 400000}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(json.dumps(event) + "\n{partial")
            self.assertAlmostEqual(c.codex_usage(path)["percent"], 102.5)
            with path.open("a") as stream: stream.write("\n" + json.dumps({"type": "compacted", "payload": {}}) + "\n")
            self.assertIsNone(c.codex_usage(path))
            event["payload"]["info"]["last_token_usage"]["total_tokens"] = 10000
            with path.open("a") as stream: stream.write(json.dumps(event) + "\n")
            self.assertEqual(c.codex_usage(path)["percent"], 2.5)

    def test_session_selection_does_not_cross_agents_in_same_project(self):
        threads = [
            {"id": "one", "name": "Task A", "source": "cli"},
            {"id": "two", "name": "Task B", "source": "cli"},
            {"id": "guardian", "name": "Task A", "source": '{"subagent":{}}'},
        ]
        self.assertEqual(c.select_thread({"title": "Task A | repo"}, threads)["id"], "one")
        self.assertEqual(c.select_thread({"title": "⠇ Task A | repo"}, threads)["id"], "one")
        self.assertEqual(c.select_thread({"title": "[ . ] Action Required | Task A | repo"}, threads)["id"], "one")
        self.assertEqual(c.select_thread({"title": "unavailable"}, threads, ["/one.jsonl", "/guardian.jsonl"])["id"], "one")
        self.assertIsNone(c.select_thread({"title": "unknown | repo"}, threads))
        threads.append({"id": "three", "name": "Task A", "source": "cli"})
        self.assertIsNone(c.select_thread({"title": "Task A | repo"}, threads))

    def test_remote_codex_never_uses_local_database_match(self):
        terminal = {"address": "server/t1", "app": "codex", "title": "Task | repo"}
        with patch.object(c, "select_thread", side_effect=AssertionError("local matching attempted")), patch.object(c.subprocess, "run", side_effect=OSError):
            self.assertIsNone(c.collect_one(terminal, [], "hc")["percent"])


if __name__ == "__main__":
    unittest.main()
