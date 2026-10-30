import unittest

from filters import classify


class ClassifyTests(unittest.TestCase):
    def keep(self, title, **kw):
        return classify(title, **kw)[0]

    def test_cyber_titles(self):
        for t in ["Security Engineer", "Küberturbe tootejuht", "Infoturbe spetsialist",
                  "SOC Analyst", "Red Teaming Expert", "Information Security Manager"]:
            keep, cyber, _ = classify(t)
            self.assertTrue(keep and cyber, t)

    def test_it_titles(self):
        for t in ["Tarkvaraarendaja", "Java vanemarendaja maksu- ja tollisüsteemide projektidesse",
                  "Full-stack arendaja", "Veebiarendaja", "DevOps insener", "IT kasutajatoe spetsialist",
                  "Senior Backend Engineer – Contacts", "Data Engineer", "Programmeerija"]:
            keep, cyber, _ = classify(t)
            self.assertTrue(keep, t)
            self.assertFalse(cyber, t)

    def test_non_it_developers_are_dropped(self):
        for t in ["TOOTEARENDAJA - TEHNOLOOG", "Kinnisvaraarendaja", "Äriarendaja", "Programmijuht"]:
            self.assertFalse(self.keep(t), t)

    def test_physical_security_and_other_engineering_dropped(self):
        for t in ["Turvatöötaja", "Security Officer", "Project Engineer (HVAC/Energy Efficiency)",
                  "Kvaliteediinsener / Quality Engineer", "Mechanical Engineer"]:
            self.assertFalse(self.keep(t), t)

    def test_non_it_roles_dropped_even_when_site_says_it(self):
        for t in ["Tax Technology Manager", "Treasury Analyst", "B2B IT teenuste ja lahenduste müügijuht",
                  "Kogukonna noorsootöötaja", "Sales Engineer for Cybersecurity Services Team"]:
            self.assertFalse(self.keep(t, assume_it=True), t)

    def test_assume_it_keeps_unrecognised_titles(self):
        self.assertTrue(self.keep("Strateegiaportfelli juht", assume_it=True))
        self.assertFalse(self.keep("Strateegiaportfelli juht"))

    def test_extra_tags_add_it_match_only(self):
        keep, cyber, intern = classify("Spetsialist", extra="python linux")
        self.assertEqual((keep, cyber, intern), (True, False, False))
        keep, cyber, intern = classify("Spetsialist", extra="cyber security")
        self.assertEqual((keep, cyber), (True, False))  # extra never makes it cyber

    def test_internship(self):
        keep, cyber, intern = classify("Elektrilevi käidutehnoloogia küberturbe praktikant")
        self.assertEqual((keep, cyber, intern), (True, True, True))
        keep, cyber, intern = classify("Automation Engineer Trainee")
        self.assertEqual((keep, cyber, intern), (True, False, True))
        self.assertTrue(classify("Anything", assume_it=True, assume_internship=True)[2])

    def test_empty_title(self):
        self.assertEqual(classify(""), (False, False, False))


if __name__ == "__main__":
    unittest.main()
