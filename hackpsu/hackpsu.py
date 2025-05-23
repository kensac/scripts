import csv
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

input_csv = "print.csv"
output_pdf = "output.pdf"

c = canvas.Canvas(output_pdf, pagesize=landscape(letter))
width, height = landscape(letter)

max_font_size = 100
target_width = 0.9 * width

with open(input_csv, "r", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile)
    

    names: list[str] = []

    # next(reader)  # Skip the header row if present

    for row in reader:
        name = row[0]
        names.append(name)

    names = list(set(names))
    names.sort()

    for name in names:

        text_width = pdfmetrics.stringWidth(name, "Helvetica", max_font_size)

        if text_width > target_width:
            font_size = max_font_size * target_width / text_width
        else:
            font_size = max_font_size

        c.setFont("Helvetica", font_size)
        c.drawCentredString(width / 2, height / 2, name)
        c.showPage()

c.save()
print(f"PDF created successfully: {output_pdf}")
