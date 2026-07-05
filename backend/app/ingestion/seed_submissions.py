"""Generate ~60 synthetic citizen development-request submissions across real Bagalkot
villages (Phase 2 step 2), then run each through the NLP pipeline (translate -> classify
-> extract place -> fuzzy-match to LGD village -> geocode -> embed) and persist to the
`submission` table.

Scenarios are deliberately clustered: several submissions describe the SAME underlying
issue (same village + theme) with different phrasing/language/channel, to exercise the
Phase 2 step 4 deduplication clustering. A handful are singletons (corroboration_count
will end up 1) to keep the demo honest — not every real report has corroboration.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.submission import Channel, Submission, Theme
from app.services import nlp
from app.services.embeddings import embed_many

# Each scenario: (village_name, theme, [(text, language, channel), ...])
# Villages are real Bagalkot LGD villages (verified against lgd_village).
SCENARIOS: list[tuple[str, Theme, list[tuple[str, str, Channel]]]] = [
    ("Kaladgi", Theme.water, [
        ("There is no drinking water in Kaladgi village for the last 3 days, the borewell has stopped working.", "en", Channel.text),
        ("ಕಾಲಡಗಿ ಗ್ರಾಮದಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ ಇದೆ, ಕೊಳವೆ ಬಾವಿ ಕೆಟ್ಟಿದೆ.", "kn", Channel.voice),
        ("No water supply since 3 days in Kaladgi, borewell motor is not working, please repair urgently.", "en", Channel.voice),
        ("Kaladgi village mein pipeline se paani nahi aa raha, borewell kharab hai.", "en", Channel.photo),
    ]),
    ("Ingalagi", Theme.road, [
        ("The main road in Ingalagi village has big potholes, very difficult for two wheelers after rain.", "en", Channel.text),
        ("ಇಂಗಳಗಿ ಗ್ರಾಮದ ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿಗಳಿವೆ, ಮಳೆಗಾಲದಲ್ಲಿ ಓಡಾಡಲು ಕಷ್ಟವಾಗಿದೆ.", "kn", Channel.voice),
        ("Road full of potholes near Ingalagi village bus stop, accidents happening frequently.", "en", Channel.photo),
    ]),
    ("Mullur", Theme.school, [
        ("Government school in Mullur village has only one teacher for all classes, we need more teachers.", "en", Channel.text),
        ("ಮುಳ್ಳೂರು ಗ್ರಾಮದ ಶಾಲೆಯಲ್ಲಿ ಶಿಕ್ಷಕರ ಕೊರತೆ ಇದೆ, ಒಬ್ಬರೇ ಶಿಕ್ಷಕರು ಎಲ್ಲಾ ತರಗತಿ ನೋಡಿಕೊಳ್ಳುತ್ತಾರೆ.", "kn", Channel.voice),
    ]),
    ("Metgud", Theme.health, [
        ("No doctor available at the Primary Health Centre in Metgud village for the past two weeks.", "en", Channel.text),
    ]),
    ("Khajagal", Theme.electricity, [
        ("Frequent power cuts in Khajagal village, sometimes 6-7 hours no current in a day.", "en", Channel.text),
        ("ಖಜಗಲ್ ಗ್ರಾಮದಲ್ಲಿ ಆಗಾಗ್ಗೆ ವಿದ್ಯುತ್ ಕಡಿತ, ದಿನಕ್ಕೆ 6-7 ಗಂಟೆ ಕರೆಂಟ್ ಇರುವುದಿಲ್ಲ.", "kn", Channel.voice),
        ("Power cut problem continuing in Khajagal, transformer seems overloaded, please check.", "en", Channel.photo),
    ]),
    ("Hunnur", Theme.sanitation, [
        ("Garbage is not collected regularly in Hunnur village, waste is piling up near the main street.", "en", Channel.text),
        ("ಹುನ್ನೂರ ಗ್ರಾಮದಲ್ಲಿ ಕಸ ಸಂಗ್ರಹಣೆ ಸರಿಯಾಗಿ ಆಗುತ್ತಿಲ್ಲ, ಮುಖ್ಯ ರಸ್ತೆಯ ಬಳಿ ಕಸ ರಾಶಿ ಬಿದ್ದಿದೆ.", "kn", Channel.voice),
    ]),
    ("Chikkur", Theme.water, [
        ("Drinking water in Chikkur village is contaminated, many people got stomach infections last week.", "en", Channel.text),
        ("ಚಿಕ್ಕೂರು ಗ್ರಾಮದಲ್ಲಿ ಕುಡಿಯುವ ನೀರು ಕಲುಷಿತವಾಗಿದೆ, ಅನೇಕ ಜನರಿಗೆ ಹೊಟ್ಟೆ ಸಮಸ್ಯೆ ಆಗಿದೆ.", "kn", Channel.voice),
        ("Water quality in Chikkur is very bad, tastes bad and smells bad, please test it.", "en", Channel.text),
        ("Contaminated water supply in Chikkur village causing health issues for children.", "en", Channel.photo),
        ("ಚಿಕ್ಕೂರಿನಲ್ಲಿ ನೀರಿನ ಗುಣಮಟ್ಟ ಸರಿಯಿಲ್ಲ, ಮಕ್ಕಳಿಗೆ ಆರೋಗ್ಯ ಸಮಸ್ಯೆ ಆಗುತ್ತಿದೆ.", "kn", Channel.voice),
    ]),
    ("Gothe", Theme.road, [
        ("Road connecting Gothe village to the highway got washed out after the last rains.", "en", Channel.text),
        ("ಗೋಠೆ ಗ್ರಾಮದ ರಸ್ತೆ ಮಳೆಯಿಂದಾಗಿ ಹಾಳಾಗಿದೆ, ಸಂಚಾರ ಕಷ್ಟವಾಗಿದೆ.", "kn", Channel.voice),
    ]),
    ("Navalgi", Theme.school, [
        ("The government school in Navalgi village does not have separate toilets for girls.", "en", Channel.text),
    ]),
    ("Rugi", Theme.health, [
        ("Ambulance takes more than an hour to reach Rugi village in emergencies, we need a closer facility.", "en", Channel.text),
        ("ರೂಗಿ ಗ್ರಾಮಕ್ಕೆ ಆಂಬ್ಯುಲೆನ್ಸ್ ಬರಲು ಒಂದು ಗಂಟೆಗಿಂತ ಹೆಚ್ಚು ಸಮಯ ತೆಗೆದುಕೊಳ್ಳುತ್ತದೆ.", "kn", Channel.voice),
        ("Emergency health response is too slow for Rugi village residents.", "en", Channel.photo),
    ]),
    ("Hangandi", Theme.electricity, [
        ("Transformer near Hangandi village burnt down two days ago and has not been replaced yet.", "en", Channel.text),
    ]),
    ("Krishnapur", Theme.sanitation, [
        ("Open drainage in Krishnapur village overflows every monsoon, spreading disease.", "en", Channel.text),
        ("ಕೃಷ್ಣಾಪುರ ಗ್ರಾಮದಲ್ಲಿ ತೆರೆದ ಚರಂಡಿ ಮಳೆಗಾಲದಲ್ಲಿ ಉಕ್ಕಿ ಹರಿಯುತ್ತದೆ.", "kn", Channel.voice),
        ("Drainage water from Krishnapur is entering houses during heavy rain, urgent action needed.", "en", Channel.photo),
        ("ಕೃಷ್ಣಾಪುರದಲ್ಲಿ ಚರಂಡಿ ಸಮಸ್ಯೆಯಿಂದ ಮನೆಗಳಿಗೆ ನೀರು ನುಗ್ಗುತ್ತಿದೆ.", "kn", Channel.voice),
    ]),
    ("Simikeri", Theme.water, [
        ("Hand pump in Simikeri village has been broken for a month, women have to walk far for water.", "en", Channel.text),
        ("ಸಿಮಿಕೇರಿ ಗ್ರಾಮದ ಹ್ಯಾಂಡ್ ಪಂಪ್ ಒಂದು ತಿಂಗಳಿನಿಂದ ಕೆಟ್ಟಿದೆ.", "kn", Channel.voice),
    ]),
    ("Kabbalageri", Theme.road, [
        ("No streetlights on the approach road to Kabbalageri village, unsafe at night.", "en", Channel.text),
    ]),
    ("Chimmalagi", Theme.other, [
        ("Chimmalagi village needs a community hall for local meetings and functions.", "en", Channel.text),
        ("ಚಿಮ್ಮಲಗಿ ಗ್ರಾಮಕ್ಕೆ ಸಮುದಾಯ ಭವನ ಬೇಕಾಗಿದೆ.", "kn", Channel.voice),
    ]),
    ("Kaladgi", Theme.school, [
        ("Classrooms are overcrowded in Kaladgi village school, need additional rooms.", "en", Channel.text),
    ]),
    ("Tariwal", Theme.water, [
        ("Water quality complaints from Tariwal village residents, water is turbid and unsafe.", "en", Channel.text),
        ("ತಾರಿವಾಳ ಗ್ರಾಮದಲ್ಲಿ ನೀರಿನ ಗುಣಮಟ್ಟ ಸಮಸ್ಯೆ, ನೀರು ಕೊಳಕಾಗಿದೆ.", "kn", Channel.voice),
        ("Turbid water supply reported by many households in Tariwal.", "en", Channel.photo),
    ]),
    ("Dharmnagar", Theme.road, [
        ("Road to Dharmnagar village is blocked by construction debris for over a week.", "en", Channel.text),
        ("ಧರ್ಮನಗರ ಗ್ರಾಮದ ರಸ್ತೆ ನಿರ್ಮಾಣ ಅವಶೇಷಗಳಿಂದ ಮುಚ್ಚಿಹೋಗಿದೆ.", "kn", Channel.voice),
    ]),
    ("Girisagar", Theme.electricity, [
        ("Low voltage in Girisagar village is damaging water pump motors of farmers.", "en", Channel.text),
        ("ಗಿರಿಸಾಗರ ಗ್ರಾಮದಲ್ಲಿ ಕಡಿಮೆ ವೋಲ್ಟೇಜ್ ಸಮಸ್ಯೆಯಿಂದ ಪಂಪ್ ಮೋಟಾರ್ ಹಾಳಾಗುತ್ತಿದೆ.", "kn", Channel.voice),
        ("Voltage fluctuation damaging farm equipment in Girisagar, need a new transformer.", "en", Channel.photo),
    ]),
    ("Mullur", Theme.sanitation, [
        ("Public toilet complex in Mullur village is broken and unusable.", "en", Channel.text),
    ]),
    ("Chikkur", Theme.school, [
        ("School building roof in Chikkur village leaks badly during rains, damaging books.", "en", Channel.text),
        ("ಚಿಕ್ಕೂರು ಶಾಲೆಯ ಚಾವಣಿ ಮಳೆಗಾಲದಲ್ಲಿ ಸೋರುತ್ತದೆ.", "kn", Channel.voice),
    ]),
    ("Khajagal", Theme.health, [
        ("Primary Health Centre near Khajagal village frequently runs out of basic medicines.", "en", Channel.text),
        ("ಖಜಗಲ್ ಬಳಿಯ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ಔಷಧಿಗಳ ಕೊರತೆ ಇದೆ.", "kn", Channel.voice),
    ]),
    ("Hunnur", Theme.other, [
        ("Requesting funding for a new community hall in Hunnur village for panchayat meetings.", "en", Channel.text),
    ]),
    ("Metgud", Theme.water, [
        ("Overhead water tank in Metgud village is leaking and wasting a lot of water.", "en", Channel.text),
        ("ಮೆಟಗುಡ ಗ್ರಾಮದ ಓವರ್ ಹೆಡ್ ಟ್ಯಾಂಕ್ ಸೋರುತ್ತಿದೆ, ಬಹಳ ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ.", "kn", Channel.voice),
    ]),
    ("Rugi", Theme.road, [
        ("Road in Rugi village was promised to be tarred last year but still remains a mud road.", "en", Channel.text),
        ("ರೂಗಿ ಗ್ರಾಮದ ರಸ್ತೆಗೆ ಕಳೆದ ವರ್ಷ ಡಾಂಬರು ಹಾಕುವುದಾಗಿ ಹೇಳಿದ್ದರು, ಇನ್ನೂ ಮಣ್ಣಿನ ರಸ್ತೆಯೇ ಇದೆ.", "kn", Channel.voice),
    ]),
    ("Simikeri", Theme.electricity, [
        ("Streetlight near Simikeri village school has not worked for months, unsafe for children in evening.", "en", Channel.text),
    ]),
    ("Hangandi", Theme.school, [
        ("Classes in Hangandi village school are overcrowded, more than 60 students in one room.", "en", Channel.text),
        ("ಹನಗಂಡಿ ಶಾಲೆಯಲ್ಲಿ ಒಂದೇ ಕೊಠಡಿಯಲ್ಲಿ 60ಕ್ಕೂ ಹೆಚ್ಚು ವಿದ್ಯಾರ್ಥಿಗಳಿದ್ದಾರೆ.", "kn", Channel.voice),
    ]),
]


def build_submissions() -> list[dict]:
    rows = []
    for village_name, theme, texts in SCENARIOS:
        for raw_text, language, channel in texts:
            rows.append({"village_hint": village_name, "theme_hint": theme, "raw_text": raw_text, "language": language, "channel": channel})
    return rows


def run() -> None:
    rows = build_submissions()
    print(f"generated {len(rows)} synthetic submissions across {len(SCENARIOS)} scenarios")

    with SessionLocal() as db:
        translated_texts = []
        for r in rows:
            r["translated_text"] = nlp.translate(r["raw_text"], r["language"])
            translated_texts.append(r["translated_text"])

        print("embedding all submissions (loading sentence-transformers model, first call is slow)...")
        embeddings = embed_many(translated_texts)

        n_classified_matching_hint = 0
        n_place_matched = 0
        submissions: list[Submission] = []
        for r, emb in zip(rows, embeddings):
            theme = nlp.classify_theme(r["translated_text"])
            if theme == r["theme_hint"]:
                n_classified_matching_hint += 1

            place_text = nlp.extract_place_mention(r["translated_text"])
            village_code, match_score = nlp.match_place_to_village(db, place_text)
            if village_code is None:
                place_text, village_code, match_score = nlp.gazetteer_match(db, r["translated_text"])
            if village_code is not None:
                n_place_matched += 1
            lat, lng = nlp.village_lat_lng(db, village_code)

            submissions.append(
                Submission(
                    channel=r["channel"],
                    raw_text=r["raw_text"],
                    language=r["language"],
                    translated_text=r["translated_text"],
                    theme=theme,
                    place_text=place_text,
                    resolved_lgd_code=village_code,
                    place_match_score=match_score,
                    lat=lat,
                    lng=lng,
                    embedding=emb,
                )
            )

        db.add_all(submissions)
        db.commit()

        print(f"\ninserted {len(submissions)} submissions")
        print(f"theme classifier agreed with scenario's intended theme: {n_classified_matching_hint}/{len(rows)} ({n_classified_matching_hint / len(rows):.1%})")
        print(f"place extraction + fuzzy-match resolved a village: {n_place_matched}/{len(rows)} ({n_place_matched / len(rows):.1%})")


if __name__ == "__main__":
    run()
