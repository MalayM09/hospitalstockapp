"""
GST calculation shared by purchase entry, bill editing and reports.

You pick the TOTAL GST rate on the invoice. For an intra-state purchase (vendor
in the same state) it is split equally into CGST + SGST; for an inter-state
purchase it is charged as IGST.

Rates offered: 5% and 18% are the main slabs since the Sept 2025 GST reform,
40% is the special slab, and 12% / 28% are kept so older invoices can still be
entered correctly.

Rounding: tax is calculated per item line to the paisa; the invoice TOTAL is
rounded to the nearest rupee once (as printed invoices do), not each line.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

GST_RATES = [0, 5, 12, 18, 28, 40]

_PAISA = Decimal("0.01")
_RUPEE = Decimal("1")


def to_decimal(value):
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except InvalidOperation:
        raise ValueError(f"Not a valid number: {value!r}")


def line_totals(quantity, rate, gst_rate, interstate=False):
    """
    Taxes for one item line, to the paisa (no rupee rounding).
    Returns Decimals: amount (taxable value), cgst, sgst, igst, total.
    """
    qty, unit, pct = to_decimal(quantity), to_decimal(rate), to_decimal(gst_rate)
    amount = (qty * unit).quantize(_PAISA, rounding=ROUND_HALF_UP)
    if interstate:
        igst = (amount * pct / 100).quantize(_PAISA, rounding=ROUND_HALF_UP)
        cgst = sgst = Decimal("0.00")
    else:
        cgst = (amount * pct / 2 / 100).quantize(_PAISA, rounding=ROUND_HALF_UP)
        sgst = cgst
        igst = Decimal("0.00")
    return {"amount": amount, "cgst": cgst, "sgst": sgst, "igst": igst,
            "total": amount + cgst + sgst + igst}


def round_off(total):
    """Round-off needed to bring an invoice total to the nearest rupee (Decimal)."""
    total = to_decimal(total)
    return total.quantize(_RUPEE, rounding=ROUND_HALF_UP) - total


def compute_totals(quantity, rate, gst_rate, interstate=False):
    """
    Totals for a single-line invoice, rounded to the rupee. Returns floats:
    amount, cgst, sgst, igst, round_off, net_amount.
    """
    t = line_totals(quantity, rate, gst_rate, interstate)
    ro = round_off(t["total"])
    return {
        "amount": float(t["amount"]), "cgst": float(t["cgst"]), "sgst": float(t["sgst"]),
        "igst": float(t["igst"]), "round_off": float(ro), "net_amount": float(t["total"] + ro),
    }


def invoice_totals(lines, interstate=False):
    """
    Totals for a whole invoice. `lines` is a list of dicts with quantity, rate, gst_rate.
    Returns floats: items, amount, cgst, sgst, igst, round_off, net_amount.
    """
    sums = {"amount": Decimal(0), "cgst": Decimal(0), "sgst": Decimal(0), "igst": Decimal(0)}
    for ln in lines:
        t = line_totals(ln["quantity"], ln["rate"], ln["gst_rate"], interstate)
        for k in sums:
            sums[k] += t[k]
    total = sum(sums.values())
    ro = round_off(total)
    return {"items": len(lines), **{k: float(v) for k, v in sums.items()},
            "round_off": float(ro), "net_amount": float(total + ro)}
