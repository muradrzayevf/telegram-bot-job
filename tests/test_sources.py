import unittest
from datetime import date

from sources import clean, cvkeskus, tootukassa, linkedin, cv_ee

CVKESKUS_HTML = """
<a class="jobad-url" href="/it-tarkvara-arendusjuht-eestis-hansasoft-ou-1059415">
  <div><span>VIP 1</span><div><span>
      2 näd. tagasi
  </span></div>
  <h2>IT Tarkvara arendusjuht</h2>
  <div><span class="job-company">HANSASOFT OÜ</span>
       <div>Eesti
                        /
                            Hübriid</div></div></div>
</a>
<a class="jobad-url" href="/no-id-here">junk</a>
"""

LINKEDIN_HTML = """
<li><div data-entity-urn="urn:li:jobPosting:4321">
  <h3 class="base-search-card__title">  Back-End Software Engineer </h3>
  <h4 class="base-search-card__subtitle">Scoro</h4>
  <span class="job-search-card__location">Tallinn, Harjumaa, Estonia</span>
  <time datetime="2026-10-29T10:00:00">1 day ago</time>
</div></li>
<li><div data-entity-urn="urn:li:something:1">ignored</div></li>
"""


class HelperTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(clean("Eesti\n     /\n   Hübriid"), "Eesti / Hübriid")
        self.assertEqual(clean(None), "")


class CvKeskusTests(unittest.TestCase):
    def test_parse(self):
        jobs = cvkeskus._parse(CVKESKUS_HTML)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["id"], "1059415")
        self.assertEqual(j["title"], "IT Tarkvara arendusjuht")
        self.assertEqual(j["company"], "HANSASOFT OÜ")
        self.assertEqual(j["location"], "Eesti / Hübriid")
        self.assertEqual(j["url"], "https://www.cvkeskus.ee/it-tarkvara-arendusjuht-eestis-hansasoft-ou-1059415")
        self.assertRegex(j["published"], r"^\d{4}-\d{2}-\d{2}$")

    def test_relative_to_date(self):
        today = date(2026, 10, 30)
        f = lambda s: cvkeskus.relative_to_date(s, today)
        self.assertEqual(f("täna"), "2026-10-30")
        self.assertEqual(f("20 tundi tagasi"), "2026-10-30")
        self.assertEqual(f("eile"), "2026-10-29")
        self.assertEqual(f("päev tagasi"), "2026-10-29")
        self.assertEqual(f("3 p. tagasi"), "2026-10-27")
        self.assertEqual(f("nädal tagasi"), "2026-10-23")
        self.assertEqual(f("2 näd. tagasi"), "2026-10-16")
        self.assertEqual(f(""), "")
        self.assertEqual(f("something odd"), "something odd")


class TootukassaTests(unittest.TestCase):
    def test_short_location(self):
        addrs = ["Harju maakond, Tallinn, Kesklinna linnaosa, Tõnismägi 11a, 10119",
                 "Harju maakond, Tallinn, Mustamäe linnaosa, X 1",
                 "Ida-Viru maakond, Jõhvi vald, Voka alevik, Metsa tn 2"]
        self.assertEqual(tootukassa.short_location(addrs), "Tallinn / Jõhvi vald")
        self.assertEqual(tootukassa.short_location(addrs[:1], remote=True), "Tallinn · kodus töötamine")
        self.assertEqual(tootukassa.short_location([], remote=True), "kodus töötamine")
        self.assertEqual(tootukassa.short_location(None), "")

    def test_norm_drops_tagline_and_trims_date(self):
        j = tootukassa._norm({"id": 7, "nimetus": "IT spetsialist", "asutusNimi": "Firma OÜ",
                              "ametinimetusTapsustus": "Tule meie kogukonna arendajaks!",
                              "kinnitamineKp": "2026-10-28T12:00:00", "aadressid": [], "alias": "it-spets"})
        self.assertEqual(j["extra"], "")
        self.assertEqual(j["published"], "2026-10-28")
        self.assertEqual(j["url"], "https://www.tootukassa.ee/et/toopakkumised/it-spets")


class LinkedInTests(unittest.TestCase):
    def test_parse(self):
        jobs = linkedin._parse(LINKEDIN_HTML)
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["id"], "4321")
        self.assertEqual(j["title"], "Back-End Software Engineer")
        self.assertEqual(j["published"], "2026-10-29")
        self.assertEqual(j["url"], "https://www.linkedin.com/jobs/view/4321/")


class CvEeTests(unittest.TestCase):
    def test_location(self):
        self.assertEqual(cv_ee._location({"remoteWorkType": "ON_SITE"}), "Eesti")
        self.assertEqual(cv_ee._location({"remoteWorkType": "HYBRID", "remoteWork": True}), "Eesti · hübriid")
        self.assertEqual(cv_ee._location({"remoteWorkType": "FULL_REMOTE"}), "Eesti · kaugtöö")
        self.assertEqual(cv_ee._location({"remoteWork": True}), "Eesti · hübriid")

    def test_norm(self):
        j = cv_ee._norm({"id": 5, "positionTitle": "QA Engineer", "employerName": "X AS",
                         "publishDate": "2026-10-28T10:00:00+00:00", "keywords": ["python", "qa"]}, True)
        self.assertEqual(j["published"], "2026-10-28")
        self.assertEqual(j["extra"], "python qa")
        self.assertTrue(j["assume_it"])
        self.assertFalse(j["assume_internship"])


if __name__ == "__main__":
    unittest.main()
