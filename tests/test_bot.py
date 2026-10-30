import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import bot


def job(source, jid, title, company="Firma OÜ", **kw):
    d = {"id": str(jid), "title": title, "company": company, "location": "Tallinn",
         "url": f"https://{source}/{jid}", "published": "2026-10-29", "source": source,
         "extra": "", "assume_it": False}
    d.update(kw)
    return d


def fake_source(name, jobs=None, error=None):
    def fetch():
        if error:
            raise error
        return list(jobs or [])
    return types.SimpleNamespace(NAME=name, fetch=fetch)


class RunOnceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "seen.json"
        self.sent = []
        patches = [
            mock.patch.object(bot, "STATE_FILE", self.state),
            mock.patch.object(bot, "send", side_effect=self._send),
            mock.patch.object(bot.time, "sleep", lambda *_: None),
            mock.patch.object(bot, "ONLY_CYBER", False),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)
        self.send_status = bot.SENT

    def _send(self, text):
        self.sent.append(text)
        return self.send_status

    def seen(self):
        return json.loads(self.state.read_text(encoding="utf-8")) if self.state.exists() else {}

    def run_with(self, *sources, **kw):
        with mock.patch.object(bot, "SOURCES", list(sources)):
            return bot.run_once(**kw)

    def test_sends_new_and_remembers_them(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Security Engineer"), job("cv.ee", 2, "Kokk")])
        self.run_with(src)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("Security Engineer", self.sent[0])
        self.assertIn("cv.ee:1", self.seen())
        self.assertNotIn("cv.ee:2", self.seen())  # non-IT jobs are not remembered, just skipped
        self.sent.clear()
        self.run_with(src)
        self.assertEqual(self.sent, [])

    def test_cross_source_duplicate_sent_once(self):
        a = fake_source("cv.ee", [job("cv.ee", 1, "Küberturbe tootejuht", "Elisa Eesti AS")])
        b = fake_source("CVKeskus", [job("CVKeskus", 9, "Küberturbe tootejuht", "Elisa")])
        self.run_with(a, b)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("cv.ee", self.sent[0])
        self.assertIn("CVKeskus:9", self.seen())
        # ...and a copy showing up on a later run is suppressed too
        c = fake_source("LinkedIn", [job("LinkedIn", 77, "Küberturbe tootejuht", "Elisa Eesti")])
        self.run_with(c)
        self.assertEqual(len(self.sent), 1)

    def test_limit_leaves_rest_for_next_run(self):
        src = fake_source("cv.ee", [job("cv.ee", i, f"Developer {i}") for i in range(3)])
        with mock.patch.object(bot, "MAX_PER_RUN", 2):
            self.run_with(src)
            self.assertEqual(len(self.sent), 3)  # 2 jobs + the "1 more waiting" notice
            self.assertIn("1 more", self.sent[-1])
            self.assertEqual(len([k for k in self.seen() if k.startswith("cv.ee:")]), 2)
            self.sent.clear()
            self.run_with(src)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("Developer", self.sent[0])

    def test_failed_send_is_retried_next_run(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Developer")])
        self.send_status = bot.FAILED
        self.run_with(src)
        self.assertNotIn("cv.ee:1", self.seen())
        self.send_status = bot.SENT
        self.sent.clear()
        self.run_with(src)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("cv.ee:1", self.seen())

    def test_rejected_send_is_not_retried(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Developer")])
        self.send_status = bot.REJECTED
        self.run_with(src)
        self.assertIn("cv.ee:1", self.seen())

    def test_init_marks_without_sending(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Developer")])
        self.run_with(src, init=True)
        self.assertEqual(self.sent, [])
        self.assertIn("cv.ee:1", self.seen())

    def test_dry_run_sends_and_saves_nothing(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Developer")])
        with mock.patch("builtins.print"):
            self.run_with(src, dry_run=True)
        self.assertEqual(self.sent, [])
        self.assertFalse(self.state.exists())

    def test_ordering_internships_then_cyber(self):
        src = fake_source("cv.ee", [job("cv.ee", 1, "Java Developer"), job("cv.ee", 2, "Security Analyst"),
                                    job("cv.ee", 3, "IT praktikant")])
        self.run_with(src)
        self.assertIn("INTERNSHIP", self.sent[0])
        self.assertIn("Security Analyst", self.sent[1])
        self.assertIn("Java Developer", self.sent[2])

    def test_failing_source_does_not_stop_others(self):
        bad = fake_source("LinkedIn", error=RuntimeError("rate limited"))
        good = fake_source("cv.ee", [job("cv.ee", 1, "Developer")])
        results = self.run_with(bad, good)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual([r.name for r in results], ["LinkedIn", "cv.ee"])
        self.assertIn("rate limited", results[0].error)
        self.assertEqual(results[1].error, "")

    def test_empty_source_is_reported_as_unhealthy(self):
        results = self.run_with(fake_source("CVKeskus", []))
        self.assertIn("0 listings", results[0].error)


class FormatTests(unittest.TestCase):
    def test_escapes_and_bold_title(self):
        msg = bot.format_job(job("cv.ee", 1, "System & AI <Security> Engineer"), cyber=True, internship=False)
        self.assertTrue(msg.startswith("🔐 Cybersecurity"))
        self.assertIn("<b>System &amp; AI &lt;Security&gt; Engineer</b>", msg)
        self.assertIn("🔗 https://cv.ee/1", msg)

    def test_internship_whole_message_bold_no_nesting(self):
        msg = bot.format_job(job("cv.ee", 1, "IT praktikant"), cyber=False, internship=True)
        self.assertTrue(msg.startswith("<b>🎓 INTERNSHIP"))
        self.assertTrue(msg.endswith("</b>"))
        self.assertEqual(msg.count("<b>"), 1)

    def test_missing_optional_fields(self):
        j = job("cv.ee", 1, "Dev", company="", location="", published="")
        msg = bot.format_job(j, False, False)
        self.assertNotIn("🏢", msg)
        self.assertNotIn("📍", msg)
        self.assertNotIn("🗓", msg)

    def test_long_title_truncated(self):
        msg = bot.format_job(job("cv.ee", 1, "x" * 1000), False, False)
        self.assertLess(len(msg), 600)


class StateTests(unittest.TestCase):
    def test_save_prunes_old_and_is_readable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "seen.json"
            bot.save_seen({"old": "2000-01-01T00:00:00", "new": "2999-01-01T00:00:00"}, p)
            self.assertEqual(bot.load_seen(p), {"new": "2999-01-01T00:00:00"})
            self.assertFalse((Path(d) / "seen.json.tmp").exists())

    def test_corrupt_state_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "seen.json"
            p.write_text("{not json", encoding="utf-8")
            self.assertEqual(bot.load_seen(p), {})


class HealthTests(unittest.TestCase):
    def test_alerts_once_and_announces_recovery(self):
        notes = []
        h = bot.SourceHealth(alert_after=2)
        bad = [bot.SourceResult("LinkedIn", [], "boom")]
        ok = [bot.SourceResult("LinkedIn", [{"id": 1}])]
        h.update(bad, notes.append)
        self.assertEqual(notes, [])
        h.update(bad, notes.append)
        self.assertEqual(len(notes), 1)
        self.assertIn("LinkedIn", notes[0])
        h.update(bad, notes.append)
        self.assertEqual(len(notes), 1)  # no repeat
        h.update(ok, notes.append)
        self.assertEqual(len(notes), 2)
        self.assertIn("working again", notes[1])
        h.update(ok, notes.append)
        self.assertEqual(len(notes), 2)

    def test_disabled(self):
        notes = []
        h = bot.SourceHealth(alert_after=0)
        for _ in range(5):
            h.update([bot.SourceResult("X", [], "boom")], notes.append)
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
