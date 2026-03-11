#!/usr/bin/env python3
"""
One-time script to merge duplicate and near-duplicate plant names in the database.
Also lowercases all item_name display values to match the app's phone-keyboard convention.

Supports both SQLite (dev) and PostgreSQL/Neon (production) via environment detection.

Usage:
  # Dev (SQLite) — uses DB_PATH env var, default /app/data/microbiome.db:
  python3 scripts/merge_plant_names.py [--dry-run]

  # Production (PostgreSQL/Neon):
  DATABASE_URL=postgresql://... python3 scripts/merge_plant_names.py [--dry-run]

Dependencies:
  - SQLite:     stdlib sqlite3 (no install needed)
  - PostgreSQL: pip install psycopg2-binary  (NOT psycopg2 — avoids libpq compile issues)
"""
import os
import sys

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_POSTGRES  = DATABASE_URL.startswith(("postgresql://", "postgres://"))
DB_PATH      = os.environ.get("DB_PATH", "/app/data/microbiome.db")
DRY_RUN      = "--dry-run" in sys.argv

# Restored accent for display (SQLite lower() loses accents on some builds,
# and the general lowercase pass would produce 'jalapeno' without the ñ).
DISPLAY_OVERRIDES: dict[str, str] = {
    "jalapeno": "jalapeño",
}

# ---------------------------------------------------------------------------
# Master merge list: (variant_normalized, canonical_normalized, canonical_display)
# All display names are lowercase to match the app's phone-keyboard convention.
# ---------------------------------------------------------------------------
MERGES = [
    # ── Category 1: Clear spelling errors ──────────────────────────────────
    ("algea",                "algae",              "algae"),
    ("ashwaganda",           "ashwagandha",        "ashwagandha"),
    ("ashwaghanda",          "ashwagandha",        "ashwagandha"),
    ("bannana",              "banana",             "banana"),
    ("bettroot",             "beet",               "beet"),
    ("black sezame seed",    "black sesame seed",  "black sesame seed"),
    ("brocoli",              "broccoli",           "broccoli"),
    ("cardamon",             "cardamom",           "cardamom"),
    ("canatloupe",           "cantaloupe",         "cantaloupe"),
    ("chickpease",           "chickpea",           "chickpea"),
    ("chlorofil",            "chlorophyll",        "chlorophyll"),
    ("chlorophyl",           "chlorophyll",        "chlorophyll"),
    ("corriander",           "coriander",          "coriander"),
    ("corriangder",          "coriander",          "coriander"),
    ("cucmber",              "cucumber",           "cucumber"),
    ("egglant",              "eggplant",           "eggplant"),
    ("egg plant",            "eggplant",           "eggplant"),
    ("faro",                 "farro",              "farro"),
    ("fave bean",            "fava bean",          "fava bean"),
    ("giner",                "ginger",             "ginger"),
    ("jalepeno",             "jalapeno",           "jalapeño"),
    ("jalapeño",             "jalapeno",           "jalapeño"),
    ("kakao powder",         "cacao powder",       "cacao powder"),
    ("kohlaribi",            "kohlrabi",           "kohlrabi"),
    ("leak",                 "leek",               "leek"),
    ("macademia nut",        "macadamia nut",      "macadamia nut"),
    ("nut meg",              "nutmeg",             "nutmeg"),
    ("paprik powder",        "paprika",            "paprika"),
    ("pinenapple",           "pineapple",          "pineapple"),
    ("pomegrade",            "pomegranate",        "pomegranate"),
    ("pomegrenate",          "pomegranate",        "pomegranate"),
    ("poppy sead",           "poppy seed",         "poppy seed"),
    ("pumkin seed",          "pumpkin seed",       "pumpkin seed"),
    ("pumking seed",         "pumpkin seed",       "pumpkin seed"),
    ("raddichio",            "radicchio",          "radicchio"),
    ("rasberry",             "raspberry",          "raspberry"),
    ("sauekraut",            "sauerkraut",         "sauerkraut"),
    ("seeweed",              "seaweed",            "seaweed"),
    ("tomoatoe",             "tomato",             "tomato"),
    ("tomatoe",              "tomato",             "tomato"),
    ("cherry tomatoe",       "cherry tomato",      "cherry tomato"),
    ("tumeric",              "turmeric",           "turmeric"),
    ("walbut",               "walnut",             "walnut"),
    ("zuchini",              "zucchini",           "zucchini"),
    ("sweet potatoe",        "sweet potato",       "sweet potato"),
    ("potatoe",              "potato",             "potato"),
    ("purple potatoe",       "purple potato",      "purple potato"),
    ("russet potatoe",       "russet potato",      "russet potato"),
    ("yukon potatoe",        "yukon potato",       "yukon potato"),
    ("fingerling potatoe",   "fingerling potato",  "fingerling potato"),
    ("shitake mushroom",     "shiitake mushroom",  "shiitake mushroom"),
    ("shittake",             "shiitake mushroom",  "shiitake mushroom"),
    ("shittake mushroom",    "shiitake mushroom",  "shiitake mushroom"),

    # ── Category 2: Normalization bug (ves→f should be ves→ve) ─────────────
    ("chif",                 "chive",              "chive"),
    ("clof",                 "clove",              "clove"),
    ("olif",                 "olive",              "olive"),
    ("garlic chif",          "garlic chive",       "garlic chive"),
    ("kalamata olif",        "kalamata olive",     "kalamata olive"),
    ("green olif",           "green olive",        "green olive"),

    # ── Category 3: Regional / alternate names → US-English canonical ───────
    ("rucola",               "arugula",            "arugula"),
    ("aubergine",            "eggplant",           "eggplant"),
    ("pak choi",             "bok choy",           "bok choy"),
    ("pakchoi",              "bok choy",           "bok choy"),
    ("dragon fruit",         "pitaya",             "pitaya"),
    ("dragonfruit",          "pitaya",             "pitaya"),
    ("garbanzo bean",        "chickpea",           "chickpea"),
    ("kaki",                 "persimmon",          "persimmon"),
    ("khaki",                "persimmon",          "persimmon"),
    ("kurkuma",              "turmeric",           "turmeric"),
    ("koriander",            "coriander",          "coriander"),
    ("basilicum",            "basil",              "basil"),
    ("basilicum spice",      "basil",              "basil"),
    ("açaí",                 "acai",               "acai"),

    # ── Category 4: Form variations (same thing, different text) ────────────
    ("chilli",               "chili",              "chili"),
    ("chilli flake",         "chili flake",        "chili flake"),
    ("red chilli",           "red chili",          "red chili"),
    ("red chilli pepper",    "red chili pepper",   "red chili pepper"),
    ("paprika powder",       "paprika",            "paprika"),
    ("smoked paprika powder","smoked paprika",      "smoked paprika"),
    ("lemon grass",          "lemongrass",         "lemongrass"),
    ("passionfruit",         "passion fruit",      "passion fruit"),
    ("flaxseed",             "flax seed",          "flax seed"),
    ("microgreen",           "micro green",        "micro green"),
    ("beansprout",           "bean sprout",        "bean sprout"),
    ("soybean",              "soy bean",           "soy bean"),
    ("blackcurrant",         "black currant",      "black currant"),
    ("blackurrant",          "black currant",      "black currant"),
    ("redcurrant",           "red currant",        "red currant"),
    ("zaatar",               "za'atar",            "za'atar"),
    ("bulgar",               "bulgur",             "bulgur"),
    ("bulgar wheat",         "bulgur",             "bulgur"),
    ("bulgur wheat",         "bulgur",             "bulgur"),
    ("cous cous",            "couscous",           "couscous"),
    ("cuscous",              "couscous",           "couscous"),
    ("wakame seaweed",       "wakame",             "wakame"),
    ("kombu seaweed",        "kombu",              "kombu"),
    ("shiitake",             "shiitake mushroom",  "shiitake mushroom"),
    ("shiso leaf",           "shiso",              "shiso"),
    ("mandarine",            "mandarin",           "mandarin"),
    ("pecan nut",            "pecan",              "pecan"),
    ("cashew nut",           "cashew",             "cashew"),
    ("rosmaryn",             "rosemary",           "rosemary"),
    ("miso paste",           "miso",               "miso"),
]


# ---------------------------------------------------------------------------
# DB connection + cursor abstraction
# ---------------------------------------------------------------------------

def get_connection():
    """Open a database connection appropriate for the current environment."""
    if IS_POSTGRES:
        try:
            import psycopg2
        except ImportError:
            print("ERROR: psycopg2 not installed.")
            print("       Run: pip install psycopg2-binary")
            sys.exit(1)
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        import sqlite3
        return sqlite3.connect(DB_PATH)


class Cursor:
    """
    Thin wrapper that normalises ? (SQLite) vs %s (PostgreSQL) placeholders
    so all merge logic above works unchanged for both databases.
    """
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, sql: str, params=()):
        if IS_POSTGRES:
            sql = sql.replace("?", "%s")
        self._cur.execute(sql, params)
        return self

    def fetchall(self):
        return self._cur.fetchall()

    def fetchone(self):
        return self._cur.fetchone()


def cur(conn) -> Cursor:
    return Cursor(conn.cursor())


def get_tables(conn) -> set:
    """Return the set of table names present in the DB."""
    c = cur(conn)
    if IS_POSTGRES:
        c.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    else:
        c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {r[0] for r in c.fetchall()}


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge_entries(conn, variant: str, canonical: str, display: str) -> tuple:
    """
    Remap all entries whose item_name_normalized=variant to the canonical form.

    If the user already has the canonical logged in the same week, the variant
    entry is a true duplicate and is deleted. Otherwise it is updated in place.

    Returns (updated, deleted).
    """
    c = cur(conn)
    rows = c.execute(
        "SELECT id, user_id, week_id FROM entries WHERE item_name_normalized = ?",
        (variant,)
    ).fetchall()

    if not rows:
        return 0, 0

    updated = deleted = 0
    for entry_id, user_id, week_id in rows:
        conflict = c.execute(
            "SELECT id FROM entries WHERE user_id = ? AND week_id = ? AND item_name_normalized = ?",
            (user_id, week_id, canonical)
        ).fetchone()

        if conflict:
            if not DRY_RUN:
                c.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            deleted += 1
        else:
            if not DRY_RUN:
                c.execute(
                    "UPDATE entries SET item_name = ?, item_name_normalized = ? WHERE id = ?",
                    (display, canonical, entry_id)
                )
            updated += 1

    return updated, deleted


def merge_cache(conn, cache_table: str, variant: str, canonical: str) -> tuple:
    """
    Merge veggie_benefits_cache rows for variant → canonical.
    If a canonical cache row already exists, the variant row is deleted.
    Returns (updated, deleted).
    """
    c = cur(conn)
    has_variant = c.execute(
        f"SELECT COUNT(*) FROM {cache_table} WHERE item_name_normalized = ?",
        (variant,)
    ).fetchone()[0]

    if not has_variant:
        return 0, 0

    has_canonical = c.execute(
        f"SELECT COUNT(*) FROM {cache_table} WHERE item_name_normalized = ?",
        (canonical,)
    ).fetchone()[0]

    if not DRY_RUN:
        if has_canonical:
            c.execute(
                f"DELETE FROM {cache_table} WHERE item_name_normalized = ?",
                (variant,)
            )
        else:
            c.execute(
                f"UPDATE {cache_table} SET item_name_normalized = ? WHERE item_name_normalized = ?",
                (canonical, variant)
            )

    updated = 0 if has_canonical else has_variant
    deleted = has_variant if has_canonical else 0
    return updated, deleted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if IS_POSTGRES:
        # Mask password in log output
        host_part = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        env_label = f"PostgreSQL ({host_part})"
    else:
        env_label = f"SQLite ({DB_PATH})"

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Connecting to {env_label}\n")
    conn = get_connection()

    tables = get_tables(conn)
    cache_table = "veggie_benefits_cache" if "veggie_benefits_cache" in tables else None
    if cache_table:
        print(f"Cache table found: {cache_table}")
    else:
        print("Cache table not present — skipping cache merges")
    print()

    # ── Step 1: Canonical merges ─────────────────────────────────────────────
    print("── Step 1: Canonical merges ─────────────────────────────────────")
    total_updated = total_deleted = total_skipped = 0
    cache_updated = cache_deleted = 0

    for variant, canonical, display in MERGES:
        u, d = merge_entries(conn, variant, canonical, display)
        if u or d:
            print(f"  entries  [{variant}] → [{canonical}]: +{u} updated, -{d} deleted")
            total_updated += u
            total_deleted += d
        else:
            total_skipped += 1

        if cache_table:
            cu, cd = merge_cache(conn, cache_table, variant, canonical)
            if cu or cd:
                print(f"  cache    [{variant}] → [{canonical}]: +{cu} updated, -{cd} deleted")
                cache_updated += cu
                cache_deleted += cd

    # ── Step 2: Lowercase all item_name values ───────────────────────────────
    print()
    print("── Step 2: Lowercase all item_name values ───────────────────────")
    c = cur(conn)
    cap_count = c.execute(
        "SELECT COUNT(*) FROM entries WHERE item_name != lower(item_name)"
    ).fetchone()[0]

    if cap_count:
        print(f"  {cap_count} entries with capitalised item_name — lowercasing...")
        if not DRY_RUN:
            c.execute("UPDATE entries SET item_name = lower(item_name) WHERE item_name != lower(item_name)")
    else:
        print("  All item_name values already lowercase.")

    # ── Step 3: Restore display overrides (accent marks) ────────────────────
    # Must run AFTER the general lowercase so that e.g. 'Jalapeno' → 'jalapeno'
    # gets corrected to 'jalapeño' in a second pass.
    print()
    print("── Step 3: Restore display overrides (accents etc.) ─────────────")
    override_total = 0
    for normalized, display in DISPLAY_OVERRIDES.items():
        c2 = cur(conn)
        needs_fix = c2.execute(
            "SELECT COUNT(*) FROM entries WHERE item_name_normalized = ? AND item_name != ?",
            (normalized, display)
        ).fetchone()[0]
        if needs_fix:
            print(f"  '{normalized}' → display '{display}': {needs_fix} entries")
            if not DRY_RUN:
                c2.execute(
                    "UPDATE entries SET item_name = ? WHERE item_name_normalized = ? AND item_name != ?",
                    (display, normalized, display)
                )
            override_total += needs_fix
    if not override_total:
        print("  No display overrides needed.")

    # ── Commit ───────────────────────────────────────────────────────────────
    print()
    if not DRY_RUN:
        conn.commit()
        print("Committed. ✓")
    else:
        print("[DRY RUN] No changes written.")

    conn.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    print("── Summary ──────────────────────────────────────────────────────")
    print(f"  Entries merged (updated) : {total_updated}")
    print(f"  Entries merged (deleted) : {total_deleted}  (were same-week duplicates)")
    print(f"  Merge pairs with no data : {total_skipped}")
    print(f"  Entries lowercased       : {cap_count}")
    print(f"  Display overrides fixed  : {override_total}")
    if cache_table:
        print(f"  Cache rows updated       : {cache_updated}")
        print(f"  Cache rows deleted       : {cache_deleted}")
    print("─────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
