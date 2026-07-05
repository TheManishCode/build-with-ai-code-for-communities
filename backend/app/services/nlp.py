"""Lightweight NLP pipeline for citizen submissions.

Deliberately simple, not over-engineered -- pick whichever approach works fastest for each
step rather than over-engineering the model choice:
  - translate(): deep-translator's free Google Translate endpoint (no API key needed;
    this project has no LLM API key configured in its environment). "voice" channel
    submissions are treated as already-transcribed text — this seed/demo pipeline does
    not do real speech-to-text, which would need an actual audio file and an ASR model.
  - classify_theme(): deterministic keyword matching against the translated (English)
    text. Transparent and good enough for a 7-way taxonomy over short citizen reports;
    the harder semantic-similarity problem (dedup) is handled separately with real
    sentence embeddings in app.services.embeddings, where it actually matters.
  - extract_place_mention() / match_place_to_village(): regex heuristic to pull a place
    name candidate out of free text, then rapidfuzz fuzzy-match against the LGD village
    master scoped to Bagalkot district — same approach already used for MPLADs work
    descriptions and Know Your School village names.
"""

from __future__ import annotations

import re

from deep_translator import GoogleTranslator
from rapidfuzz import fuzz, process, utils
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.submission import Theme

BAGALKOT_DISTRICT_CODE = 524
PLACE_MATCH_THRESHOLD = 85

THEME_KEYWORDS: dict[Theme, list[str]] = {
    Theme.water: [
        "water", "borewell", "bore well", "tap", "pipeline", "pipe line", "drinking water",
        "hand pump", "handpump", "tank", "overhead tank", "drought", "fhtc", "well",
    ],
    Theme.road: [
        "road", "street", "pothole", "highway", "bridge", "culvert", "tar road", "mud road",
        "footpath", "pathway",
    ],
    Theme.school: [
        "school", "teacher", "classroom", "students", "education", "anganwadi", "college",
    ],
    Theme.health: [
        "hospital", "clinic", "doctor", "phc", "health center", "health centre", "medicine",
        "ambulance", "nurse", "emergency",
    ],
    Theme.electricity: [
        "power", "electricity", "current", "transformer", "streetlight", "street light",
        "voltage", "power cut", "power outage",
    ],
    Theme.sanitation: [
        "toilet", "drainage", "sewage", "garbage", "waste", "sanitation", "drain", "dump",
        "dumping",
    ],
}

# Primary: "in/at/near <Place>[ village]". Fallback: "<Place> village" anywhere in the
# sentence, regardless of preposition — machine-translated Kannada often produces
# constructions like "The road of Gothe village..." or "Chimmalagi village needs..."
# that the primary pattern misses. NOTE: deliberately NOT using re.IGNORECASE — that flag
# would make the `[A-Z]` capture-start also match lowercase, so generic words after "in"/
# "at" (e.g. "in emergencies", "at night") would be captured as false-positive place names.
# Case-insensitivity for the keyword itself is handled by the explicit alternation below.
PLACE_RE = re.compile(r"\b(?:[Ii]n|[Aa]t|[Nn]ear)\s+([A-Z][A-Za-z.\- ]{2,40}?)(?:\s+[Vv]illage\b|,|\.|$)")
PLACE_FALLBACK_RE = re.compile(r"\b([A-Z][A-Za-z.\-]{2,30})\s+[Vv]illage\b")


def translate(raw_text: str, language: str) -> str:
    """Translate to English if not already. Returns raw_text unchanged for language=='en'."""
    if language == "en":
        return raw_text
    try:
        result = GoogleTranslator(source=language, target="en").translate(raw_text)
        return result or raw_text
    except Exception:
        # Translation is a best-effort convenience field, not a hard dependency of the
        # pipeline (classification/place-matching below fall back to the raw text) — a
        # transient network failure shouldn't abort ingestion of a citizen report.
        return raw_text


def classify_theme(translated_text: str) -> Theme:
    """Score by keyword OCCURRENCE COUNT, not just presence — a text that says "garbage...
    garbage piled up" should out-score an incidental single mention of a keyword from
    another theme (e.g. "near the main road"), rather than an arbitrary tie resolved by
    THEME_KEYWORDS dict order.
    """
    lowered = translated_text.lower()
    scores = {theme: sum(lowered.count(kw) for kw in kws) for theme, kws in THEME_KEYWORDS.items()}
    best_theme, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_theme if best_score > 0 else Theme.other


def extract_place_mention(translated_text: str) -> str | None:
    m = PLACE_RE.search(translated_text)
    if m:
        return m.group(1).strip()
    m = PLACE_FALLBACK_RE.search(translated_text)
    if m:
        return m.group(1).strip()
    return None


def match_place_to_village(db: Session, place_text: str | None) -> tuple[int | None, float | None]:
    """Fuzzy-match place_text against lgd_village.village_name in Bagalkot district.
    Returns (village_code, score) or (None, None) if no place_text or no confident match.
    """
    if not place_text:
        return None, None
    rows = _bagalkot_villages(db)
    names = [r.village_name for r in rows]
    code_by_name = {r.village_name: r.village_code for r in rows}
    result = process.extractOne(place_text, names, scorer=fuzz.WRatio, processor=utils.default_process)
    if result is None:
        return None, None
    name, score, _ = result
    if score < PLACE_MATCH_THRESHOLD:
        return None, None
    return code_by_name[name], float(score)


def _bagalkot_villages(db: Session):
    return db.execute(
        text("SELECT village_code, village_name FROM lgd_village WHERE district_code = :d"),
        {"d": BAGALKOT_DISTRICT_CODE},
    ).all()


def gazetteer_match(db: Session, translated_text: str) -> tuple[str | None, int | None, float | None]:
    """Fallback for text that names a village without "village" nearby (e.g. "Chikkur
    school leaks", "Drainage water from Krishnapur..."): scan for any known Bagalkot
    village name appearing as a whole word in the text, preferring the longest/most
    specific match to avoid short-name false positives. Returns (place_text, village_code,
    score) with score=100.0 (exact gazetteer hit) — or (None, None, None) if nothing found.
    """
    rows = _bagalkot_villages(db)
    # Longest name first so e.g. "Hosa Korti" wins over a shorter substring match.
    candidates = sorted(rows, key=lambda r: len(r.village_name), reverse=True)
    for r in candidates:
        name = r.village_name.strip()
        if len(name) < 4:
            continue  # too short to safely word-match without false positives
        if re.search(r"\b" + re.escape(name) + r"\b", translated_text, re.IGNORECASE):
            return name, r.village_code, 100.0
    return None, None, None


def village_lat_lng(db: Session, village_code: int | None) -> tuple[float | None, float | None]:
    """Look up a village's approximate point location from village_fact.geom, when available."""
    if village_code is None:
        return None, None
    row = db.execute(
        text("SELECT ST_X(geom) AS lng, ST_Y(geom) AS lat FROM village_fact WHERE village_code = :vc AND geom IS NOT NULL"),
        {"vc": village_code},
    ).first()
    if row is None:
        return None, None
    return row.lat, row.lng
