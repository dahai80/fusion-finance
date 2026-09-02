from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

logger.warning(
    "SANCTIONS_LIST is a stale hardcoded sample, NOT a real OFAC/EU/UN/HMT feed. "
    "Do not rely on this for production compliance screening."
)

SANCTIONS_LIST = [
    {"name": "North Korea Trade Corp", "country": "KP", "type": "entity", "program": "DPRK"},
    {"name": "Iran National Oil Company", "country": "IR", "type": "entity", "program": "IRAN"},
    {"name": "Bank of Russia", "country": "RU", "type": "entity", "program": "RUSSIA"},
    {"name": "Syrian Arab Republic", "country": "SY", "type": "country", "program": "SYRIA"},
    {"name": "Military Industry Corp", "country": "MM", "type": "entity", "program": "BURMA"},
    {"name": "Korea Mining Development", "country": "KP", "type": "entity", "program": "DPRK"},
    {"name": "Islamic Revolutionary Guard", "country": "IR", "type": "entity", "program": "IRAN"},
    {"name": "Volgograd Defense Plant", "country": "RU", "type": "entity", "program": "RUSSIA"},
    {"name": "Daesh", "country": "", "type": "terrorist", "program": "TERRORISM"},
    {"name": "Al-Qaida", "country": "", "type": "terrorist", "program": "TERRORISM"},
]

_MIN_THRESHOLD = 0.3


@dataclass
class SanctionsMatch:
    query: str = ""
    matched_name: str = ""
    matched_entry: dict = field(default_factory=dict)
    match_type: str = ""
    score: float = 0.0


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    collapsed = "".join(c for c in nfkd if not unicodedata.combining(c))
    return collapsed.casefold().strip()


class SanctionsEngine:
    def __init__(self, sanctions_list: list[dict] | None = None):
        self.sanctions = sanctions_list or SANCTIONS_LIST
        logger.warning(
            "SanctionsEngine initialized with %d entries from a stale sample list, not real OFAC data.",
            len(self.sanctions),
        )

    def screen(self, entity: str, threshold: float = 0.6) -> list[SanctionsMatch]:
        if threshold < _MIN_THRESHOLD:
            logger.warning(
                "Sanctions screen threshold %.2f below floor %.2f, clamping to floor.",
                threshold,
                _MIN_THRESHOLD,
            )
            threshold = _MIN_THRESHOLD
        logger.info("Sanctions screen request: entity='%s', threshold=%.2f", entity, threshold)
        if not entity or not entity.strip():
            return []
        entity_norm = _normalize(entity)
        matches: list[SanctionsMatch] = []
        for entry in self.sanctions:
            name_norm = _normalize(entry["name"])
            exact = entity_norm == name_norm
            contains = entity_norm in name_norm or name_norm in entity_norm
            levenshtein_score = self._levenshtein_ratio(entity_norm, name_norm)
            keyword_score = self._keyword_match(entity_norm, name_norm)
            alias_score = self._alias_match(entity_norm, name_norm)
            score = max(
                1.0 if exact else 0.0,
                0.85 if contains else 0.0,
                levenshtein_score,
                keyword_score,
                alias_score,
            )
            match_type = (
                "exact"
                if exact
                else "contains"
                if contains
                else "fuzzy"
                if levenshtein_score >= threshold
                else "keyword"
                if keyword_score >= threshold
                else "alias"
                if alias_score >= threshold
                else ""
            )
            if score >= threshold:
                matches.append(
                    SanctionsMatch(
                        query=entity,
                        matched_name=entry["name"],
                        matched_entry=entry,
                        match_type=match_type,
                        score=round(score, 4),
                    )
                )
        matches.sort(key=lambda m: m.score, reverse=True)
        logger.info(
            "Sanctions screen result: entity='%s', matches=%d, top_score=%s",
            entity,
            len(matches),
            matches[0].score if matches else "n/a",
        )
        return matches

    def screen_batch(self, entities: list[str], threshold: float = 0.6) -> dict[str, list[SanctionsMatch]]:
        results = {}
        for e in entities:
            results[e] = self.screen(e, threshold)
        logger.info("Batch screen: %d entities", len(entities))
        return results

    def add_entry(self, entry: dict) -> None:
        self.sanctions.append(entry)
        logger.info("Added sanctions entry: %s", entry.get("name", ""))

    @staticmethod
    def _levenshtein_ratio(s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        len1, len2 = len(s1), len(s2)
        if abs(len1 - len2) > max(len1, len2) * 0.5:
            return 0.0
        prev = list(range(len2 + 1))
        for i in range(1, len1 + 1):
            curr = [i] + [0] * len2
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            prev = curr
        dist = prev[len2]
        return 1.0 - dist / max(len1, len2)

    @staticmethod
    def _keyword_match(query: str, target: str) -> float:
        q_words = set(query.split())
        t_words = set(target.split())
        if not q_words or not t_words:
            return 0.0
        overlap = len(q_words & t_words)
        return overlap / max(len(q_words), len(t_words))

    @staticmethod
    def _alias_match(query: str, target: str) -> float:
        q_tokens = [t for t in query.split() if t]
        t_tokens = [t for t in target.split() if t]
        if not q_tokens or not t_tokens:
            return 0.0
        matched = 0
        for qt in q_tokens:
            for tt in t_tokens:
                if qt == tt or qt in tt or tt in qt:
                    matched += 1
                    break
        return matched / max(len(q_tokens), len(t_tokens))
