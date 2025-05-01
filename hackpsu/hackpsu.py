import csv
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

# Define your input CSV file and output PDF file names
input_csv = 'print.csv'
output_pdf = 'output.pdf'

# Set up a canvas with landscape orientation (using letter size)
c = canvas.Canvas(output_pdf, pagesize=landscape(letter))
width, height = landscape(letter)

# Maximum desired font size
max_font_size = 100
# Define the target width (90% of the page width)
target_width = 0.9 * width

# Open and read the CSV file
with open(input_csv, 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    # If your CSV has a header that you want to skip, uncomment the next line:
    # next(reader)
    for row in reader:
        # Assuming the first column contains the name
        name = row[0]
        # Calculate the width of the text at the maximum font size
        text_width = pdfmetrics.stringWidth(name, "Helvetica", max_font_size)
        # Determine the font size: if text_width exceeds target_width, scale down; otherwise, use max_font_size
        if text_width > target_width:
            font_size = max_font_size * target_width / text_width
        else:
            font_size = max_font_size

        # Set the dynamically calculated font size
        c.setFont("Helvetica", font_size)
        # Draw the name centered on the page
        c.drawCentredString(width/2, height/2, name)
        # Move to the next page
        c.showPage()

# Save the final PDF file
c.save()
print(f"PDF created successfully: {output_pdf}")
