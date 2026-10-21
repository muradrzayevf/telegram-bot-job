"""Keyword filters: is a vacancy IT / cybersecurity related, and is it an internship."""
import re

# Physical security / guard jobs that contain "security"/"turva" but are not IT.
EXCLUDE = [
    r"turvat[öo]{1,2}taja", r"julgestust[öo]{1,2}taja", r"turvamees", r"valvur",
    r"security guard", r"security officer", r"охранник", r"turvakontrol",
    r"\bG4S\b", r"turvameeskond", r"objektivalvur", r"patrull",
]

CYBER = [
    r"cyber", r"k[üu]ber", r"infosec", r"information security", r"infoturbe", r"infoturve",
    r"it[- ]security", r"it[- ]turva",
    r"security (engineer|analyst|specialist|architect|consultant|researcher|operations|lead|manager|intern|trainee|team)",
    r"\bsoc\b", r"penetration", r"pentest", r"pen[- ]test", r"ethical hack", r"red team", r"blue team",
    r"threat", r"vulnerab", r"\bsiem\b", r"forensic", r"\bciso\b", r"\bgrc\b", r"application security",
    r"appsec", r"devsecops", r"cloud security", r"network security", r"security operations",
    r"кибер", r"информационной безопасност", r"turvaanal[üu]{1,2}tik", r"turbespetsialist",
    r"iso ?27001", r"\bnis2\b", r"incident response", r"malware", r"cryptograph", r"kr[üu]ptograaf",
    r"identity (and|&) access", r"\biam\b", r"zero trust", r"osint", r"security clearance",
]

IT = [
    r"\bit\b", r"\bit-", r"infotehnoloog", r"informaatik", r"software", r"tarkvara", r"developer", r"arendaja",
    r"programm", r"engineer", r"devops", r"\bsre\b", r"site reliability", r"cloud", r"pilve",
    r"sysadmin", r"system[s]? admin", r"s[üu]{1,2}steemiadmin", r"v[õo]rguadmin", r"network", r"v[õo]rgu",
    r"data (engineer|scientist|analyst|architect)", r"andmeanal[üu]{1,2}tik", r"andmeteadlane", r"andmeinsener",
    r"machine learning", r"\bml\b", r"\bai\b", r"tehisintellekt", r"artificial intelligence",
    r"frontend", r"front-end", r"backend", r"back-end", r"full[- ]?stack", r"\bqa\b", r"quality assurance",
    r"test(er|ija|imis)", r"automation", r"\bjava\b", r"python", r"\.net\b", r"c#", r"c\+\+", r"golang",
    r"javascript", r"typescript", r"react", r"angular", r"node\.?js", r"kotlin", r"swift", r"android", r"\bios\b",
    r"database", r"andmebaas", r"\bsql\b", r"\bdba\b", r"linux", r"windows (server|admin)", r"kubernetes", r"docker",
    r"helpdesk", r"help desk", r"service desk", r"it[- ]tugi", r"it[- ]support", r"technical support", r"tehniline tugi",
    r"it[- ]spetsialist", r"it[- ]specialist", r"it[- ]juht", r"it[- ]manager", r"it[- ]analyst", r"it[- ]anal[üu]{1,2}tik",
    r"system[s]? (engineer|analyst|architect)", r"s[üu]{1,2}steemianal[üu]{1,2}tik", r"solution architect",
    r"lahenduste arhitekt", r"scrum master", r"product owner", r"tech lead", r"\bcto\b", r"embedded", r"firmware",
    r"\bfpga\b", r"hardware engineer",
    r"разработчик", r"программист", r"системный администратор", r"тестировщик", r"инженер[- ]программист",
    r"blockchain", r"web ?(developer|arendaja)", r"wordpress", r"salesforce", r"\bsap\b", r"\berp\b", r"bi developer",
    r"power bi", r"ux/ui", r"ui/ux", r"ux designer", r"ui designer", r"digi- ja andme",
]

INTERNSHIP = [
    r"\bintern\b", r"internship", r"praktika", r"praktikant", r"trainee", r"\bstudent\b", r"t[üu]{1,2}dengi",
    r"стаж[её]р", r"стажировк", r"suvepraktika", r"summer intern", r"graduate program", r"apprentice",
]


def _any(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def is_excluded(text: str) -> bool:
    return _any(EXCLUDE, text)


def is_cyber(text: str) -> bool:
    return _any(CYBER, text) and not is_excluded(text)


def is_it(text: str) -> bool:
    return (_any(IT, text) or _any(CYBER, text)) and not is_excluded(text)


def is_internship(text: str) -> bool:
    return _any(INTERNSHIP, text)


def classify(title: str, extra: str = "", assume_it: bool = False, assume_internship: bool = False):
    """Return (keep, cyber, internship).

    The title decides everything; `extra` (site keywords/tags) can only add an IT match.
    Descriptions are deliberately not used for cyber/internship, they mention "security"
    and "students" far too often."""
    if is_excluded(title):
        return False, False, False
    cyber = is_cyber(title)
    keep = assume_it or is_it(title) or is_it(extra) or cyber
    internship = assume_internship or is_internship(title)
    return keep, cyber, internship
