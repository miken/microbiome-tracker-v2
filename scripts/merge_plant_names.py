#!/usr/bin/env python3
"""
One-time script to merge duplicate and near-duplicate plant names in the database.

Run inside Docker:
  docker exec <container> python3 /app/scripts/merge_plant_names.py [--dry-run]
"""
import sqlite3
import os
import sys

DB_PATH = os.environ.get("DB_PATH", "/app/data/microbiome.db")
DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Master merge list: (variant_normalized, canonical_normalized, canonical_display)
# ---------------------------------------------------------------------------
MERGES = [
    # ── Category 1: Clear spelling errors ──────────────────────────────────
    ("algea",                "algae",              "Algae"),
    ("ashwaganda",           "ashwagandha",         "Ashwagandha"),
    ("ashwaghanda",          "ashwagandha",         "Ashwagandha"),
    ("bannana",              "banana",              "Banana"),
    ("bettroot",             "beet",                "Beet"),
    ("black sezame seed",    "black sesame seed",   "Black sesame seeds"),
    ("brocoli",              "broccoli",            "Broccoli"),
    ("cardamon",             "cardamom",            "Cardamom"),
    ("canatloupe",           "cantaloupe",          "Cantaloupe"),
    ("chickpease",           "chickpea",            "Chickpea"),
    ("chlorofil",            "chlorophyll",         "Chlorophyll"),
    ("chlorophyl",           "chlorophyll",         "Chlorophyll"),
    ("corriander",           "coriander",           "Coriander"),
    ("corriangder",          "coriander",           "Coriander"),
    ("cucmber",              "cucumber",            "Cucumber"),
    ("egglant",              "eggplant",            "Eggplant"),
    ("egg plant",            "eggplant",            "Eggplant"),
    ("faro",                 "farro",               "Farro"),
    ("fave bean",            "fava bean",           "Fava bean"),
    ("giner",                "ginger",              "Ginger"),
    ("jalepeno",             "jalapeno",            "Jalapeño"),
    ("jalapeño",             "jalapeno",            "Jalapeño"),
    ("kakao powder",         "cacao powder",        "Cacao powder"),
    ("kohlaribi",            "kohlrabi",            "Kohlrabi"),
    ("leak",                 "leek",                "Leek"),
    ("macademia nut",        "macadamia nut",       "Macadamia nut"),
    ("nut meg",              "nutmeg",              "Nutmeg"),
    ("paprik powder",        "paprika",             "Paprika"),
    ("pinenapple",           "pineapple",           "Pineapple"),
    ("pomegrade",            "pomegranate",         "Pomegranate"),
    ("pomegrenate",          "pomegranate",         "Pomegranate"),
    ("poppy sead",           "poppy seed",          "Poppy seeds"),
    ("pumkin seed",          "pumpkin seed",        "Pumpkin seeds"),
    ("pumking seed",         "pumpkin seed",        "Pumpkin seeds"),
    ("raddichio",            "radicchio",           "Radicchio"),
    ("rasberry",             "raspberry",           "Raspberry"),
    ("sauekraut",            "sauerkraut",          "Sauerkraut"),
    ("seeweed",              "seaweed",             "Seaweed"),
    ("tomoatoe",             "tomato",              "Tomato"),
    ("tomatoe",              "tomato",              "Tomato"),
    ("cherry tomatoe",       "cherry tomato",       "Cherry tomato"),
    ("tumeric",              "turmeric",            "Turmeric"),
    ("walbut",               "walnut",              "Walnut"),
    ("zuchini",              "zucchini",            "Zucchini"),
    ("sweet potatoe",        "sweet potato",        "Sweet potato"),
    ("potatoe",              "potato",              "Potato"),
    ("purple potatoe",       "purple potato",       "Purple potato"),
    ("russet potatoe",       "russet potato",       "Russet potato"),
    ("yukon potatoe",        "yukon potato",        "Yukon potato"),
    ("fingerling potatoe",   "fingerling potato",   "Fingerling potato"),
    ("shitake mushroom",     "shiitake mushroom",   "Shiitake mushroom"),
    ("shittake",             "shiitake mushroom",   "Shiitake mushroom"),
    ("shittake mushroom",    "shiitake mushroom",   "Shiitake mushroom"),

    # ── Category 2: Normalization bug (ves→f should be ves→ve) ─────────────
    ("chif",                 "chive",               "Chives"),
    ("clof",                 "clove",               "Clove"),
    ("olif",                 "olive",               "Olive"),
    ("garlic chif",          "garlic chive",        "Garlic chives"),
    ("kalamata olif",        "kalamata olive",      "Kalamata olive"),
    ("green olif",           "green olive",         "Green olive"),

    # ── Category 3: Regional / alternate names → US-English canonical ───────
    ("rucola",               "arugula",             "Arugula"),
    ("aubergine",            "eggplant",            "Eggplant"),
    ("pak choi",             "bok choy",            "Bok choy"),
    ("pakchoi",              "bok choy",            "Bok choy"),
    ("dragon fruit",         "pitaya",              "Pitaya"),
    ("dragonfruit",          "pitaya",              "Pitaya"),
    ("garbanzo bean",        "chickpea",            "Chickpea"),
    ("kaki",                 "persimmon",           "Persimmon"),
    ("khaki",                "persimmon",           "Persimmon"),
    ("kurkuma",              "turmeric",            "Turmeric"),
    ("koriander",            "coriander",           "Coriander"),
    ("basilicum",            "basil",               "Basil"),
    ("basilicum spice",      "basil",               "Basil"),
    ("açaí",                 "acai",                "Acai"),

    # ── Category 4: Form variations (same thing, different text) ────────────
    ("chilli",               "chili",               "Chili"),
    ("chilli flake",         "chili flake",         "Chili flakes"),
    ("red chilli",           "red chili",           "Red chili"),
    ("red chilli pepper",    "red chili pepper",    "Red chili pepper"),
    ("paprika powder",       "paprika",             "Paprika"),
    ("smoked paprika powder","smoked paprika",       "Smoked paprika"),
    ("lemon grass",          "lemongrass",          "Lemongrass"),
    ("passionfruit",         "passion fruit",       "Passion fruit"),
    ("flaxseed",             "flax seed",           "Flax seeds"),
    ("microgreen",           "micro green",         "Micro greens"),
    ("beansprout",           "bean sprout",         "Bean sprouts"),
    ("soybean",              "soy bean",            "Soy beans"),
    ("blackcurrant",         "black currant",       "Black currant"),
    ("blackurrant",          "black currant",       "Black currant"),
    ("redcurrant",           "red currant",         "Red currant"),
    ("zaatar",               "za'atar",             "Za'atar"),
    ("bulgar",               "bulgur",              "Bulgur"),
    ("bulgar wheat",         "bulgur",              "Bulgur"),
    ("bulgur wheat",         "bulgur",              "Bulgur"),
    ("cous cous",            "couscous",            "Couscous"),
    ("cuscous",              "couscous",            "Couscous"),
    ("wakame seaweed",       "wakame",              "Wakame"),
    ("kombu seaweed",        "kombu",               "Kombu"),
    ("shiitake",             "shiitake mushroom",   "Shiitake mushroom"),
    ("shiso leaf",           "shiso",               "Shiso"),
    ("mandarine",            "mandarin",            "Mandarin"),
    ("pecan nut",            "pecan",               "Pecan"),
    ("cashew nut",           "cashew",              "Cashew"),
    ("rosmaryn",             "rosemary",            "Rosemary"),
    ("miso paste",           "miso",                "Miso"),
]


def merge_entries(conn: sqlite3.Connection, variant: str, canonical: str, display: str) -> tuple[int, int]:
    """
    Move all entries with item_name_normalized=variant to canonical.
    Returns (updated, deleted) counts.
    """
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, user_id, week_id FROM entries WHERE item_name_normalized = ?",
        (variant,)
    ).fetchall()

    if not rows:
        return 0, 0

    updated = deleted = 0
    for entry_id, user_id, week_id in rows:
        conflict = cur.execute(
            "SELECT id FROM entries WHERE user_id=? AND week_id=? AND item_name_normalized=?",
            (user_id, week_id, canonical)
        ).fetchone()

        if conflict:
            if not DRY_RUN:
                cur.execute("DELETE FROM entries WHERE id=?", (entry_id,))
            deleted += 1
        else:
            if not DRY_RUN:
                cur.execute(
                    "UPDATE entries SET item_name=?, item_name_normalized=? WHERE id=?",
                    (display, canonical, entry_id)
                )
            updated += 1

    return updated, deleted


def merge_cache(conn: sqlite3.Connection, variant: str, canonical: str) -> tuple[int, int]:
    """
    Merge VeggieBenefitsCache rows for variant → canonical.
    Returns (kept, deleted) counts.
    """
    cur = conn.cursor()
    has_variant = cur.execute(
        "SELECT COUNT(*) FROM veggiebefitscache WHERE item_name_normalized=?", (variant,)
    ).fetchone()[0]

    if not has_variant:
        return 0, 0

    has_canonical = cur.execute(
        "SELECT COUNT(*) FROM veggiebefitscache WHERE item_name_normalized=?", (canonical,)
    ).fetchone()[0]

    if not DRY_RUN:
        if has_canonical:
            cur.execute("DELETE FROM veggiebefitscache WHERE item_name_normalized=?", (variant,))
        else:
            cur.execute(
                "UPDATE veggiebefitscache SET item_name_normalized=? WHERE item_name_normalized=?",
                (canonical, variant)
            )
    return (0, has_variant) if has_canonical else (has_variant, 0)


def get_cache_table_name(conn: sqlite3.Connection) -> str | None:
    """Return actual cache table name (handles spelling variant in model)."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for name in ("veggiebefitscache", "veggiebenfitscache", "veggiebenefitscache", "veggiebenfitscache"):
        if name in tables:
            return name
    return None


def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    cache_table = get_cache_table_name(conn)
    if cache_table:
        print(f"Cache table found: {cache_table}")
    else:
        print("No cache table found — skipping cache merges")

    total_updated = total_deleted = total_skipped = 0
    cache_updated = cache_deleted = 0

    for variant, canonical, display in MERGES:
        u, d = merge_entries(conn, variant, canonical, display)
        if u or d:
            print(f"  entries [{variant}] → [{canonical}]: +{u} updated, -{d} deleted")
            total_updated += u
            total_deleted += d
        else:
            total_skipped += 1

        if cache_table:
            # Inline SQL with actual table name (can't parameterize table name)
            cur = conn.cursor()
            has_v = cur.execute(
                f"SELECT COUNT(*) FROM {cache_table} WHERE item_name_normalized=?", (variant,)
            ).fetchone()[0]
            if has_v:
                has_c = cur.execute(
                    f"SELECT COUNT(*) FROM {cache_table} WHERE item_name_normalized=?", (canonical,)
                ).fetchone()[0]
                if not DRY_RUN:
                    if has_c:
                        cur.execute(f"DELETE FROM {cache_table} WHERE item_name_normalized=?", (variant,))
                        cache_deleted += has_v
                    else:
                        cur.execute(
                            f"UPDATE {cache_table} SET item_name_normalized=? WHERE item_name_normalized=?",
                            (canonical, variant)
                        )
                        cache_updated += has_v

    if not DRY_RUN:
        conn.commit()
        print(f"\nCommitted.")
    else:
        print(f"\n[DRY RUN] No changes written.")

    conn.close()

    print(f"\n── Summary ───────────────────────────────────")
    print(f"  Entries updated : {total_updated}")
    print(f"  Entries deleted : {total_deleted}  (were duplicates of canonical)")
    print(f"  Merge pairs with no data: {total_skipped}")
    if cache_table:
        print(f"  Cache rows updated: {cache_updated}")
        print(f"  Cache rows deleted: {cache_deleted}")


if __name__ == "__main__":
    main()
