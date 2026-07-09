from pathlib import Path
from xhtml2pdf import pisa

def build_pdf_from_html(html_path: str | Path, pdf_path: str | Path) -> Path:
    html_path = Path(html_path)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    print("Building PDF with xhtml2pdf...")

    html = html_path.read_text(encoding="utf-8")

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise RuntimeError("PDF generation failed with xhtml2pdf")

    print(f"PDF report saved to: {pdf_path}")
    return pdf_path
