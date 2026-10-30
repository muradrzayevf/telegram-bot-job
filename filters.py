"""Keyword filters: is a vacancy IT / cybersecurity related, and is it an internship.

Every list holds regular expressions matched case-insensitively against the vacancy title
(IT patterns are also tried against the site's own tags in `extra`). Edit the lists to tune.
"""
import re

# Hard exclusions. Physical security / guard jobs that contain "security" or "turva", and
# engineering disciplines that are not IT. A title matching one of these is never sent.
EXCLUDE = [
    r"turvat[öo]{1,2}taja", r"julgestust[öo]{1,2}taja", r"turvamees", r"valvur",
    r"security guard", r"security officer", r"охранник", r"turvakontrol",
    r"\bG4S\b", r"turvameeskond", r"objektivalvur", r"patrull",
    r"\bhvac\b", r"mechanical engineer", r"mehaanikainsener", r"civil engineer", r"ehitusinsener",
    r"electrical engineer", r"elektriinsener", r"structural engineer", r"process engineer",
    r"production engineer", r"tootmisinsener", r"quality engineer", r"kvaliteediinsener",
    r"keevitus", r"\bcnc\b",
]

# Soft exclusions. Roles that job sites file under IT, or that hit an IT keyword, but are
# sales / finance / HR / teaching work rather than IT work ("B2B IT teenuste müügijuht",
# "Tax Technology Manager"). Delete an entry if you do want those.
NON_IT = [
    r"m[üu]{1,2}gi", r"\bsales\b", r"account manager", r"treasury", r"\btax\b", r"raamatupida",
    r"accountant", r"personali", r"\bhr\b", r"recruit", r"v[äa]rbami", r"turundus", r"marketing",
    r"[õo]petaja", r"noorsoot[öo]{1,2}", r"juris", r"lawyer", r"legal counsel", r"klienditeenindaja",
    r"customer service", r"copywriter",
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
    r"\bit\b", r"\bit-", r"infotehnoloog", r"informaatik", r"software", r"tarkvara", r"developer",
    # "arendaja" only as a whole word or an IT compound: "Tarkvaraarendaja" yes, "Tootearendaja"
    # (product developer in a textile factory) and "Kinnisvaraarendaja" (real estate) no.
    r"(?<![a-zäöüõ])(vanem|noorem)?arendaja", r"(tarkvara|veebi|mobiili|rakendus\w*|s[üu]{1,2}steemi|liidese)arenda",
    r"programmeer", r"engineer", r"devops", r"\bsre\b", r"site reliability", r"cloud", r"pilve",
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


def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_EXCLUDE, _NON_IT, _CYBER, _IT, _INTERNSHIP = (_compile(x) for x in (EXCLUDE, NON_IT, CYBER, IT, INTERNSHIP))


def _any(compiled, text):
    return bool(text) and any(p.search(text) for p in compiled)


def is_excluded(text: str) -> bool:
    return _any(_EXCLUDE, text)


def is_non_it(text: str) -> bool:
    return _any(_NON_IT, text)


def is_cyber(text: str) -> bool:
    return _any(_CYBER, text) and not is_excluded(text)


def is_it(text: str) -> bool:
    return (_any(_IT, text) or _any(_CYBER, text)) and not is_excluded(text)


def is_internship(text: str) -> bool:
    return _any(_INTERNSHIP, text)


def classify(title: str, extra: str = "", assume_it: bool = False, assume_internship: bool = False):
    """Return (keep, cyber, internship).

    The title decides everything; `extra` (the site's own tags) can only add an IT match,
    and `assume_it` / `assume_internship` carry the site's own categorisation. EXCLUDE and
    NON_IT titles are dropped even when the site filed them under IT."""
    if is_excluded(title) or is_non_it(title):
        return False, False, False
    cyber = _any(_CYBER, title)
    keep = cyber or assume_it or _any(_IT, title) or is_it(extra)
    internship = assume_internship or _any(_INTERNSHIP, title)
    return keep, cyber, internship
