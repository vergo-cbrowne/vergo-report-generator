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
            display_header_footer=True,
            header_template="<div></div>",
            footer_template="""
                <div style="
                    width: 100%;
                    font-size: 8px;
                    color: #5b6770;
                    padding: 0 0.6in;
                    text-align: right;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Page <span class="pageNumber"></span> of <span class="totalPages"></span>
                </div>
            """,
            margin={
                "top": "0.6in",
                "right": "0.6in",
                "bottom": "0.75in",
                "left": "0.6in",
            },
        )

        browser.close()

    print(f"PDF report saved to: {pdf_path}")
    return pdf_path