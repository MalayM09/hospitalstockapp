"""
Printing tables (reports, registers, bills).

The printout has the health-centre heading, the report title and period, a
clean table with right-aligned numbers, a totals row, page numbers via the
print engine, and signature lines. All text is HTML-escaped, so item names
containing '&' or '<' print correctly.
"""
from datetime import datetime
from html import escape

from PyQt6.QtGui import QPageLayout, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

ORG_NAME = "Health Center, MSU — Laboratory Stock"

_NUMERIC = {"int", "money", "pct"}


def build_html(title, headers, rows, kinds=None, totals=None, period="", note=""):
    kinds = kinds or ["text"] * len(headers)

    def cell(tag, value, kind, extra=""):
        align = ' align="right"' if kind in _NUMERIC else ""
        return f"<{tag}{align}{extra}>{escape(str(value if value is not None else ''))}</{tag}>"

    head = "".join(cell("th", h, k) for h, k in zip(headers, kinds))
    body = []
    for i, r in enumerate(rows):
        bg = ' bgcolor="#F6F8FA"' if i % 2 else ""
        body.append(f"<tr{bg}>" + "".join(cell("td", v, k) for v, k in zip(r, kinds)) + "</tr>")
    if totals:
        body.append('<tr class="total">' + "".join(cell("td", v, k) for v, k in zip(totals, kinds)) + "</tr>")

    return f"""
    <html><head><style>
        body {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 9pt; color: #111827; }}
        .org {{ font-size: 9pt; color: #0F766E; font-weight: 600; }}
        h1 {{ font-size: 15pt; margin: 2px 0 0 0; }}
        .meta {{ color: #6B7280; font-size: 8.5pt; margin-bottom: 8px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th {{ background: #E6F4F1; color: #0F3D38; font-weight: 600; padding: 5px 6px;
              border-bottom: 1px solid #94A3B8; }}
        td {{ padding: 4px 6px; border-bottom: 1px solid #E5E7EB; }}
        tr.total td {{ font-weight: 700; border-top: 1.5px solid #111827; border-bottom: none; }}
        .note {{ color: #6B7280; font-size: 8pt; margin-top: 6px; }}
        .sign {{ margin-top: 40px; }}
    </style></head><body>
        <div class="org">{escape(ORG_NAME)}</div>
        <h1>{escape(title)}</h1>
        <div class="meta">{escape(period + '  ·  ' if period else '')}Printed {datetime.now():%d %b %Y, %I:%M %p}
            · {len(rows)} row{'s' if len(rows) != 1 else ''}</div>
        <table><tr>{head}</tr>{''.join(body)}</table>
        {f'<div class="note">{escape(note)}</div>' if note else ''}
        <table class="sign" width="100%"><tr>
            <td width="50%">Prepared by: ______________________</td>
            <td width="50%" align="right">Verified by: ______________________</td>
        </tr></table>
    </body></html>"""


def print_table(parent, title, headers, rows, kinds=None, totals=None, period="", note=""):
    """Show the print dialog and print. Returns True if printed."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    wide = len(headers) > 6
    printer.setPageOrientation(QPageLayout.Orientation.Landscape if wide else QPageLayout.Orientation.Portrait)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(f"Print — {title}")
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return False
    doc = QTextDocument()
    doc.setHtml(build_html(title, headers, rows, kinds, totals, period, note))
    doc.print(printer)
    return True


def print_report(parent, report):
    """Print a report_service.Report."""
    from utils.formatting import format_cell
    kinds = [k for _, k in report.columns]
    rows = [[format_cell(v, k) for v, k in zip(r, kinds)] for r in report.rows]
    totals = [format_cell(v, k) for v, k in zip(report.totals, kinds)] if report.totals else None
    return print_table(parent, report.title, [h for h, _ in report.columns], rows,
                       kinds, totals, report.period, report.note)
