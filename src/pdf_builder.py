from pathlib import Path
from playwright.sync_api import sync_playwright


def build_pdf_from_html(html_path: str | Path, pdf_path: str | Path) -> Path:
    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()

    if not html_path.exists():
        raise FileNotFoundError(f"HTML report not found: {html_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    file_url = html_path.as_uri()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(file_url, wait_until="networkidle")
        page.emulate_media(media="screen")

        page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            margin={
                "top": "0.6in",
                "right": "0.6in",
                "bottom": "0.6in",
                "left": "0.6in",
            },
        )

        browser.close()

    print(f"PDF report saved to: {pdf_path}")
    return pdf_path
    