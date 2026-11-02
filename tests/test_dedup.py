import unittest

from dedup import fingerprint, norm_company, norm_title


class DedupTests(unittest.TestCase):
    def test_company_noise_removed(self):
        self.assertEqual(norm_company("Elektrilevi OÜ"), norm_company("Elektrilevi"))
        self.assertEqual(norm_company("Cybernetica AS"), norm_company("Cybernetica"))
        self.assertEqual(norm_company("Sihtasutus CR14"), norm_company("CR14 SA"))
        self.assertEqual(norm_company("SEB, Tallinn"), norm_company("SEB"))
        self.assertEqual(norm_company("Tripod Grupp OÜ"), norm_company("Tripod"))

    def test_title_normalisation(self):
        self.assertEqual(norm_title("Küberturbe tootejuht"), norm_title("KUBERTURBE   TOOTEJUHT"))
        self.assertEqual(norm_title("Senior Backend Engineer – Contacts"), "senior backend engineer contacts")

    def test_fingerprint_matches_across_sources(self):
        a = {"company": "Elektrilevi OÜ", "title": "Elektrilevi käidutehnoloogia küberturbe praktikant"}
        b = {"company": "Elektrilevi", "title": "Elektrilevi käidutehnoloogia küberturbe praktikant"}
        self.assertEqual(fingerprint(a), fingerprint(b))
        self.assertTrue(fingerprint(a).startswith("dup:"))

    def test_different_jobs_differ(self):
        a = {"company": "Wise", "title": "Senior Software Engineer - Rules Platform"}
        b = {"company": "Wise", "title": "Senior Software Engineer - Contacts"}
        self.assertNotEqual(fingerprint(a), fingerprint(b))

    def test_missing_data_gives_none(self):
        self.assertIsNone(fingerprint({"company": "", "title": "Developer"}))
        self.assertIsNone(fingerprint({"company": "OÜ", "title": "Developer"}))
        self.assertIsNone(fingerprint({"title": "Developer"}))


if __name__ == "__main__":
    unittest.main()
