import sqlite3
from pathlib import Path
from datetime import datetime
import sys

# Import centralized database path utility
from utils.db_path import get_database_path


DB_PATH = get_database_path()

# Sample vendor list (13 vendors — placeholder names, edit later)
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
    "PRAKHAR ENTERPRISE"
]

# Items with their initial stock quantities (item_name: quantity)
ITEMS_WITH_QUANTITY = {
    "Glucose Kit": 0,
    "Serum cholesterol": 0,
    "Serum triglyceride": 0,
    "Blood urea": 0,
    "Serum creatinine": 0,
    "atotal bilirubin": 0,
    "Serum SGPT": 0,
    "Serum Alkaline phosphate": 0,
    "Serum uric acid": 0,
    "HBA1C": 0,
    "CRP Kit": 0,
    "RA": 2,
    "Serum widal": 1,
    "Pregnancy test": 50,
    "M.T. test": 0,
    "Urine strick": 5,
    "Blood group": 0,
    "Cell pack (diluent foe 3-part)": 0,
    "Dengue card": 30,
    "Cell clean": 0,
    "Vaccurate k3. E.D.T.A.": 500,
    "Vaccurate k3. Plain": 600,
    "Vaccurate k3. FLUORIDE": 300,
    "Giemasa stain": 2,
    "Printer Roll": 4,
    "Stromatolyser (lyse solution for 3 part)": 0,
    "Distilled water": 4,
    "Micro slide": 2,
    "Cover slip": 4,
    "Filter paper": 1,
    "PM KIT(ERBA EM DESTINY 180)": 0,
    "Paper tape": 0,
    "Yellow tips": 0,
    "Blue tips": 0,
    "ESR tube": 0,
    "Tissue paper roll": 3,
    "Cleaner wood oil": 2,
    "Turniket belt": 3,
    "Fouchets reagent": 0,
    "Barium Chloride": 0,
    "Malaria card": 50,
    "Urine container beaker": 30,
    "ROTER": 3,
    "XL AUTO WASH": 1,
    "XL MULTICA ERBA NORM": 0,
    "Blood collection needle 22g": 4,
    "Collection vial 1.5 ml": 0,
    "URBA Path": 0,
    "URBA XL MULITCAL": 0,
    "CRP": 0
}

# Keep ITEMS list for backwards compatibility
ITEMS = list(ITEMS_WITH_QUANTITY.keys())


def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert vendors
    for vendor in VENDORS:
        cur.execute(
            "INSERT OR IGNORE INTO vendors (name) VALUES (?)",
            (vendor,)
        )

    # Insert items (name only, no quantity column)
    for item_name in ITEMS_WITH_QUANTITY.keys():
        cur.execute(
            "INSERT OR IGNORE INTO items (name) VALUES (?)",
            (item_name,)
        )

    conn.commit()

    # Now add initial stock quantities to stock_register
    # Only add entries for items with quantity > 0
    today = datetime.now().strftime("%Y-%m-%d")
    
    for item_name, quantity in ITEMS_WITH_QUANTITY.items():
        if quantity > 0:
            # Get the item_id for this item
            cur.execute("SELECT id FROM items WHERE name = ?", (item_name,))
            result = cur.fetchone()
            if result:
                item_id = result[0]
                # Check if there's already a stock entry for this item
                cur.execute("SELECT id FROM stock_register WHERE item_id = ?", (item_id,))
                existing = cur.fetchone()
                if not existing:
                    # Insert initial stock as received stock
                    cur.execute("""
                        INSERT INTO stock_register (item_id, vendor_id, received_qty, issued_qty, balance_qty, date)
                        VALUES (?, NULL, ?, 0, ?, ?)
                    """, (item_id, quantity, quantity, today))

    conn.commit()
    conn.close()
    print("✅ Vendors, Items & Initial Stock seeded successfully.")


if __name__ == "__main__":
    seed_data()
