"""
First-run setup: default admin user, vendor list and item list.

Seeding happens ONCE, on a brand-new database (tracked by the 'seeded' flag in
app_meta). Previously this ran on every launch, so any default vendor or item
the user deleted came back the next time the app started.

Opening stock quantities are deliberately NOT seeded: they were a stale
snapshot, and inserting them dated "today" on a fresh install would corrupt
the register before historical data is imported.
"""
import logging

log = logging.getLogger(__name__)

VENDORS = [
    "SEEMA CHEMICALS",
    "RIDDHI TRADERS",
    "ADI ENTERPRISE",
    "PRASAD SURGICAL",
    "KRISHNA ENTERPRISE",
    "CURE SUPPLIERS",
    "AN PHARMA",
    "GTB ENTERPRISE",
    "J&B MEDICAL AND SURGICAL",
    "RBM DISRIBUTOR",
    "MATRIX BIOMEDICAL",
    "JP ENTERPRISE",
    "PRAKHAR ENTERPRISE",
]

ITEMS = [
    "Glucose Kit", "Serum cholesterol", "Serum triglyceride", "Blood urea",
    "Serum creatinine", "atotal bilirubin", "Serum SGPT", "Serum Alkaline phosphate",
    "Serum uric acid", "HBA1C", "CRP Kit", "RA", "Serum widal", "Pregnancy test",
    "M.T. test", "Urine strick", "Blood group", "Cell pack (diluent foe 3-part)",
    "Dengue card", "Cell clean", "Vaccurate k3. E.D.T.A.", "Vaccurate k3. Plain",
    "Vaccurate k3. FLUORIDE", "Giemasa stain", "Printer Roll",
    "Stromatolyser (lyse solution for 3 part)", "Distilled water", "Micro slide",
    "Cover slip", "Filter paper", "PM KIT(ERBA EM DESTINY 180)", "Paper tape",
    "Yellow tips", "Blue tips", "ESR tube", "Tissue paper roll", "Cleaner wood oil",
    "Turniket belt", "Fouchets reagent", "Barium Chloride", "Malaria card",
    "Urine container beaker", "ROTER", "XL AUTO WASH", "XL MULTICA ERBA NORM",
    "Blood collection needle 22g", "Collection vial 1.5 ml", "URBA Path",
    "URBA XL MULITCAL", "CRP",
]


def ensure_admin_user(db):
    """Create the default admin/admin login if there are no users at all."""
    if db.scalar("SELECT COUNT(*) FROM users") == 0:
        import bcrypt
        hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", hashed))
        log.info("Created default admin user")


def seed_if_first_run(db):
    """Insert default vendors and items, only on a brand-new database."""
    if db.scalar("SELECT value FROM app_meta WHERE key = 'seeded'"):
        return False
    with db.transaction():
        for name in VENDORS:
            db.execute("INSERT OR IGNORE INTO vendors (name) VALUES (?)", (name,))
        for name in ITEMS:
            db.execute("INSERT OR IGNORE INTO items (name) VALUES (?)", (name,))
        db.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES ('seeded', '1')")
    log.info("First run: seeded %d vendors and %d items", len(VENDORS), len(ITEMS))
    return True
