"""
GST calculation shared by purchase entry, bill editing and reports.

You pick the TOTAL GST rate on the invoice. For an intra-state purchase (vendor
in the same state) it is split equally into CGST + SGST; for an inter-state
purchase it is charged as IGST.

Rates offered: 5% and 18% are the main slabs since the Sept 2025 GST reform,
40% is the special slab, and 12% / 28% are kept so older invoices can still be
entered correctly.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

GST_RATES = [0, 5, 12, 18, 28, 40]

_PAISA = Decimal("0.01")
_RUPEE = Decimal("1")


def _d(value):
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except InvalidOperation:
        raise ValueError(f"Not a valid number: {value!r}")


def compute_totals(quantity, rate, gst_rate, interstate=False):
    """
    quantity   - number of units
    rate       - price per unit before tax (Rs)
    gst_rate   - total GST %, e.g. 18
    interstate - True for IGST, False for CGST + SGST

    Returns a dict of floats: amount (taxable value), cgst, sgst, igst,
    round_off and net_amount (rounded to the nearest rupee, as on invoices).
    """
    qty = _d(quantity)
    unit = _d(rate)
    pct = _d(gst_rate)

    amount = (qty * unit).quantize(_PAISA, rounding=ROUND_HALF_UP)
    if interstate:
        igst = (amount * pct / 100).quantize(_PAISA, rounding=ROUND_HALF_UP)
        cgst = sgst = Decimal("0")
    else:
        half = pct / 2
        cgst = (amount * half / 100).quantize(_PAISA, rounding=ROUND_HALF_UP)
        sgst = cgst
        igst = Decimal("0")

    subtotal = amount + cgst + sgst + igst
    net = subtotal.quantize(_RUPEE, rounding=ROUND_HALF_UP)
    round_off = net - subtotal

    return {
        "amount": float(amount),
        "cgst": float(cgst),
        "sgst": float(sgst),
        "igst": float(igst),
        "round_off": float(round_off),
        "net_amount": float(net),
    }
