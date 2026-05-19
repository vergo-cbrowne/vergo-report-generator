from io import BytesIO
from docx import Document


def build_docx(report_text: str) -> bytes:
    document = Document()
    document.add_heading("Vergo Master Report", level=1)

    for paragraph in report_text.split("\n\n"):
        paragraph_text = paragraph.strip()
        if paragraph_text:
            document.add_paragraph(paragraph_text)
        else:
            document.add_paragraph("")

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output.read()
