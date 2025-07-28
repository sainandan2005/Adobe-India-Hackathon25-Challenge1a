FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Try multiple PDF libraries for robustness
RUN pip install --no-cache-dir \
    PyPDF2==3.0.1 \
    pdfplumber==0.10.3 \
    && pip cache purge

# Copy the processing script
COPY process_pdfs.py .

# Run the script
CMD ["python", "process_pdfs.py"] 