"""Display formatting shared by screens, exports and printouts."""
from datetime import date


def inr(value, decimals=2, symbol=True):
    """Indian digit grouping: 213994.5 -> '₹2,13,994.50'."""
    if value is None or value == "":
        return ""
    value = float(value)
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.{decimals}f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    text = whole + (f".{frac}" if decimals else "")
    return f"{sign}{'₹' if symbol else ''}{text}"


def qty(value):
    if value is None or value == "":
        return ""
    value = float(value)
    return f"{int(value):,}" if value == int(value) else f"{value:,.2f}"


def nice_date(iso, with_year=True):
    """'2026-11-19' -> '19 Nov 2026' (or '19 Nov')."""
    if not iso:
        return ""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return d.strftime("%d %b %Y" if with_year else "%d %b")


def nice_month(ym):
    """'2026-11' -> 'Nov 2026'."""
    try:
        return date.fromisoformat(f"{ym}-01").strftime("%b %Y")
    except (ValueError, TypeError):
        return str(ym or "")


def format_cell(value, kind):
    """Format a report cell by column kind (text, int, money, date, month, pct)."""
    if value is None or value == "":
        return ""
    if isinstance(value, str) and kind not in ("date", "month"):
        return value  # e.g. the "Total" label
    return {
        "int": qty,
        "money": inr,
        "date": nice_date,
        "month": nice_month,
        "pct": lambda v: f"{float(v):g}%",
    }.get(kind, str)(value)
