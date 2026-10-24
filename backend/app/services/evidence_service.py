"""Evidence matching: which profile entries support each job requirement.

Labels:
  supported           an experience, project, education, certification, or
                      achievement entry mentions the requirement
  needs_confirmation  only the skills list mentions it, or every entry that
                      mentions it only describes helping ("helped with X")
  not_found           nothing in the profile mentions it

Matching is token-based, so "Java" never matches "JavaScript", "C" never
matches "C#", and the skill "R" never matches "React".
"""

import re
from dataclasses import dataclass, field

from app.domain.resume_draft import JDData

SUPPORTED = "supported"
NEEDS_CONFIRMATION = "needs_confirmation"
NOT_FOUND = "not_found"
_RANK = {NOT_FOUND: 0, NEEDS_CONFIRMATION: 1, SUPPORTED: 2}

_TOKEN = re.compile(r"\.?[a-z0-9][a-z0-9.+#-]*")
_ALIASES = {
    "js": "javascript", "ts": "typescript", "node": "node.js", "nodejs": "node.js",
    "reactjs": "react", "react.js": "react", "postgres": "postgresql", "k8s": "kubernetes",
    "golang": "go", "py": "python", "nextjs": "next.js", "vuejs": "vue", "vue.js": "vue",
    "endpoint": "api",
}
# Bullets that only describe helping are evidence of exposure, not of the skill itself:
# "Helped the team with the Kubernetes deployment". Helping other people with a skill
# ("Help students debug JavaScript") still shows the skill, so only these phrasings count.
_HEDGED = re.compile(
    r"\b(?:help(?:ed|ing)?|assist(?:ed|ing)?|support(?:ed|ing)?)\s+(?:the\s+team\s+)?(?:with|in|on)\b"
    r"|\bhelped\s+the\s+team\b|\bparticipated\s+in\b|\binvolved\s+in\b|\bexposure\s+to\b|\bshadowed\b",
    re.IGNORECASE,
)
_ALTERNATIVES = re.compile(r"\s*,\s*(?:or\s+)?|\s+or\s+", re.IGNORECASE)


def _canonical(token: str) -> str:
    token = token.rstrip(".-")
    token = _ALIASES.get(token, token)
    # Treat simple plurals alike on both sides: "APIs" matches "API".
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = _ALIASES.get(token[:-1], token[:-1])
    return token


def tokens(text: str) -> list[str]:
    return [_canonical(t) for t in _TOKEN.findall(text.lower()) if t.rstrip(".-")]


def contains_term(text_tokens: list[str], term: str) -> bool:
    term_tokens = tokens(term)
    if not term_tokens:
        return False
    n = len(term_tokens)
    return any(text_tokens[i:i + n] == term_tokens for i in range(len(text_tokens) - n + 1))


@dataclass
class Evidence:
    id: str
    kind: str  # bullet | experience | project | education | certification | achievement | skill
    text: str
    _tokens: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self):
        self._tokens = tokens(self.text)


@dataclass
class RequirementMatch:
    requirement: str
    importance: str  # required | preferred
    label: str
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requirement": self.requirement,
            "importance": self.importance,
            "label": self.label,
            "evidence": [{"id": e.id, "kind": e.kind, "text": e.text} for e in self.evidence],
        }


def collect_evidence(profile) -> list[Evidence]:
    evidence = []
    for exp in profile.experience:
        evidence.append(Evidence(exp.id, "experience", f"{exp.role} at {exp.company}"))
        evidence += [Evidence(b.id, "bullet", b.bullet_text) for b in exp.bullets]
    for proj in profile.projects:
        parts = [proj.project_title, proj.description or "", proj.tech_stack or ""]
        evidence.append(Evidence(proj.id, "project", " | ".join(p for p in parts if p)))
        evidence += [Evidence(b.id, "bullet", b.bullet_text) for b in proj.bullets]
    for edu in profile.education:
        evidence.append(Evidence(edu.id, "education", " ".join(p for p in [edu.degree, edu.field_of_study or ""] if p)))
    for cert in profile.certifications:
        evidence.append(Evidence(cert.id, "certification", " ".join(p for p in [cert.name, cert.issuing_organization or ""] if p)))
    for ach in profile.achievements:
        evidence.append(Evidence(ach.id, "achievement", " ".join(p for p in [ach.title, ach.description or ""] if p)))
    evidence += [Evidence(s.id, "skill", s.skill_name) for s in profile.skills]
    return evidence


def alternatives(requirement: str) -> list[str]:
    """'Python, Java, or C++' → ['Python', 'Java', 'C++']; 'CI/CD' stays whole."""
    return [part.strip() for part in _ALTERNATIVES.split(requirement) if part.strip()]


def match_requirement(requirement: str, importance: str, evidence: list[Evidence]) -> RequirementMatch:
    terms = alternatives(requirement)
    hits = [e for e in evidence if any(contains_term(e._tokens, term) for term in terms)]
    demonstrated = [e for e in hits if e.kind != "skill"]
    if any(not _HEDGED.search(e.text) for e in demonstrated):
        return RequirementMatch(requirement, importance, SUPPORTED, demonstrated)
    if demonstrated:
        return RequirementMatch(requirement, importance, NEEDS_CONFIRMATION, demonstrated)
    if hits:
        return RequirementMatch(requirement, importance, NEEDS_CONFIRMATION, hits)
    return RequirementMatch(requirement, importance, NOT_FOUND, [])


def coverage(profile, jd: JDData) -> list[RequirementMatch]:
    evidence = collect_evidence(profile)
    required = [match_requirement(r, "required", evidence) for r in jd.must_have_skills]
    preferred = [match_requirement(r, "preferred", evidence) for r in jd.nice_to_have_skills]
    return required + preferred


def best_label(labels: list[str]) -> str:
    return max(labels, key=_RANK.__getitem__, default=NOT_FOUND)
