import os
import json
from pathlib import Path
import sys

def extract_pdf_outline(pdf_path):
    """
    Extract outline from PDF using available PDF libraries.
    Returns title and outline structure.
    """
    # Try PyPDF2 first (most reliable)
    try:
        import PyPDF2
        print(f"Using PyPDF2 for {pdf_path.name}")
        return extract_with_pypdf2(pdf_path)
    except ImportError:
        pass
    
    # Try pdfplumber second
    try:
        import pdfplumber
        print(f"Using pdfplumber for {pdf_path.name}")
        return extract_with_pdfplumber(pdf_path)
    except ImportError:
        pass
    
    # Try PyMuPDF as fallback
    try:
        import fitz  # PyMuPDF
        print(f"Using PyMuPDF version: {fitz.version[0]} for {pdf_path.name}")
        return extract_with_pymupdf(pdf_path)
    except ImportError as e:
        print(f"No PDF libraries available, using fallback method")
        return extract_pdf_fallback(pdf_path)
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return {
            "title": pdf_path.stem,
            "outline": []
        }

def extract_with_pypdf2(pdf_path):
    """Extract PDF content using PyPDF2."""
    import PyPDF2
    
    title = ""
    outline = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract title from metadata
            if pdf_reader.metadata and pdf_reader.metadata.title:
                title = pdf_reader.metadata.title.strip()[:100]
            
            # Try to extract outline/bookmarks
            if hasattr(pdf_reader, 'outline') and pdf_reader.outline:
                outline = process_pypdf2_outline(pdf_reader.outline)
            
            # If no title from metadata, try first page
            if not title and len(pdf_reader.pages) > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                if text:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        title = lines[0][:100]
            
            # If still no outline, try text-based detection
            if not outline:
                outline = extract_headings_from_text(pdf_reader)
            
            if not title:
                title = pdf_path.stem.replace('_', ' ').replace('-', ' ')
    
    except Exception as e:
        print(f"Error with PyPDF2: {e}")
        return extract_pdf_fallback(pdf_path)
    
    return {
        "title": title,
        "outline": outline
    }

def process_pypdf2_outline(outline, level=1):
    """Process PyPDF2 outline/bookmarks into our format."""
    result = []
    
    for item in outline:
        if isinstance(item, list):
            # Nested outline
            result.extend(process_pypdf2_outline(item, level + 1))
        else:
            # Bookmark item
            try:
                title_text = item.title if hasattr(item, 'title') else str(item)
                page_num = 1  # Default page
                
                if hasattr(item, 'page') and item.page:
                    # Try to get page number
                    try:
                        if hasattr(item.page, 'idnum'):
                            page_num = item.page.idnum
                        else:
                            page_num = 1
                    except:
                        page_num = 1
                
                result.append({
                    "level": f"H{min(level, 6)}",
                    "text": title_text.strip(),
                    "page": page_num
                })
            except Exception as e:
                print(f"Error processing outline item: {e}")
    
    return result

def extract_headings_from_text(pdf_reader):
    """Extract potential headings by analyzing text patterns."""
    outline = []
    
    try:
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty or very short lines
                if not line or len(line) < 3:
                    continue
                
                # Clean up common patterns and numbers
                clean_line = line
                
                # Remove trailing periods and clean spaces
                if clean_line.endswith('.'):
                    clean_line = clean_line[:-1].strip()
                
                # Simple heuristics for heading detection
                is_heading = (
                    len(clean_line) < 200 and  # Not too long
                    not clean_line.endswith('.') and  # Doesn't end with period
                    (
                        # Table of Contents indicators
                        any(clean_line.upper().startswith(prefix.upper()) for prefix in [
                            'Table of Contents', 'Contents', 'Revision History', 
                            'Acknowledgements', 'Abstract', 'Summary', 'Overview',
                            'Introduction', 'Conclusion', 'References', 'Bibliography'
                        ]) or
                        # Numbered sections
                        any(clean_line.startswith(prefix) for prefix in [
                            '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.',
                            '1 ', '2 ', '3 ', '4 ', '5 ', '6 ', '7 ', '8 ', '9 ',
                        ]) or
                        # Subsections
                        any(clean_line.startswith(prefix) for prefix in [
                            '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9',
                            '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8', '2.9',
                            '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9',
                            '4.1', '4.2', '4.3', '4.4', '4.5', '4.6', '4.7', '4.8', '4.9',
                        ]) or
                        # Chapter indicators
                        any(clean_line.upper().startswith(prefix.upper()) for prefix in [
                            'Chapter', 'Section', 'Part', 'Appendix'
                        ]) or
                        # All caps (but not too long)
                        (clean_line.isupper() and len(clean_line) < 100) or
                        # Short lines with colons
                        (len(clean_line.split()) <= 10 and ':' in clean_line)
                    )
                )
                
                if is_heading:
                    # Determine heading level based on content and structure
                    if any(clean_line.upper().startswith(prefix.upper()) for prefix in [
                        'Chapter', 'Part', 'Table of Contents', 'Contents', 
                        'Revision History', 'Acknowledgements', 'Abstract', 
                        'Summary', 'Overview', 'Introduction', 'Conclusion', 
                        'References', 'Bibliography'
                    ]):
                        level = "H1"
                    elif any(clean_line.startswith(prefix) for prefix in [
                        '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.',
                        '1 ', '2 ', '3 ', '4 ', '5 ', '6 ', '7 ', '8 ', '9 '
                    ]):
                        level = "H1"
                    elif any(clean_line.startswith(prefix) for prefix in [
                        '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9',
                        '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8', '2.9',
                        '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9',
                        '4.1', '4.2', '4.3', '4.4', '4.5', '4.6', '4.7', '4.8', '4.9',
                    ]):
                        level = "H2"
                    elif clean_line.isupper() and len(clean_line) < 50:
                        level = "H1"
                    else:
                        level = "H2"
                    
                    # Clean the text for output
                    clean_text = clean_line.strip()
                    
                    outline.append({
                        "level": level,
                        "text": clean_text,
                        "page": page_num + 1
                    })
                    
                    # Limit to avoid too many headings
                    if len(outline) > 50:
                        break
            
            if len(outline) > 50:
                break
    
    except Exception as e:
        print(f"Error extracting headings from text: {e}")
    
    return outline

def extract_with_pdfplumber(pdf_path):
    """Extract PDF content using pdfplumber."""
    import pdfplumber
    
    title = ""
    outline = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract title from first page
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                if text:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        title = lines[0][:100]  # Use first line as title
            
            if not title:
                title = pdf_path.stem
            
            # Analyze text across all pages to detect headings
            all_text_objects = []
            
            for page_num, page in enumerate(pdf.pages):
                chars = page.chars
                if chars:
                    # Group characters into text blocks
                    lines = page.extract_text().split('\n') if page.extract_text() else []
                    
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 3:  # Skip very short lines
                            # Simple heuristics for heading detection
                            is_heading = (
                                len(line) < 100 and  # Not too long
                                (line.isupper() or  # All caps
                                 any(line.startswith(prefix) for prefix in ['Chapter', 'Section', 'Part', 'Introduction', 'Conclusion']) or
                                 line.endswith(':') or  # Ends with colon
                                 (len(line.split()) <= 8 and not line.endswith('.')))  # Short and no period
                            )
                            
                            if is_heading:
                                # Determine heading level based on length and position
                                if any(line.startswith(prefix) for prefix in ['Chapter', 'Part']):
                                    level = "H1"
                                elif any(line.startswith(prefix) for prefix in ['Section']):
                                    level = "H2"
                                elif line.isupper():
                                    level = "H2"
                                else:
                                    level = "H3"
                                
                                outline.append({
                                    "level": level,
                                    "text": line,
                                    "page": page_num + 1
                                })
    
    except Exception as e:
        print(f"Error with pdfplumber: {e}")
        return extract_pdf_fallback(pdf_path)
    
    return {
        "title": title,
        "outline": outline
    }

def extract_with_pymupdf(pdf_path):
    """Extract PDF content using PyMuPDF."""
    import fitz
    
    # Open PDF
    doc = fitz.open(pdf_path)
    
    # Extract title from metadata or first page
    title = doc.metadata.get('title', '').strip()
    if not title:
        # Fallback: try to get title from first page
        if len(doc) > 0:
            first_page = doc[0]
            text = first_page.get_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                title = lines[0][:100]  # Limit title length
    
    if not title:
        title = pdf_path.stem  # Use filename as fallback
    
    # Extract outline using built-in TOC
    outline = []
    toc = doc.get_toc()
    
    if toc:
        # Process built-in table of contents
        for level, title_text, page_num in toc:
            # Convert level to H1, H2, H3 format
            heading_level = f"H{min(level, 6)}"  # Cap at H6
            
            outline.append({
                "level": heading_level,
                "text": title_text.strip(),
                "page": page_num
            })
    else:
        # Fallback: analyze text formatting to detect headings
        outline = analyze_text_formatting(doc)
    
    doc.close()
    
    return {
        "title": title,
        "outline": outline
    }

def analyze_text_formatting(doc):
    """
    Analyze text formatting to detect headings when no TOC is available.
    """
    outline = []
    
    try:
        # Collect all text with formatting info
        all_blocks = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")
            
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text and len(text) > 3:  # Filter short text
                                all_blocks.append({
                                    "text": text,
                                    "size": span.get("size", 12),
                                    "flags": span.get("flags", 0),
                                    "page": page_num + 1
                                })
        
        if not all_blocks:
            return outline
        
        # Calculate average font size
        sizes = [block["size"] for block in all_blocks]
        avg_size = sum(sizes) / len(sizes)
        
        # Detect headings based on font size and formatting
        for block in all_blocks:
            text = block["text"]
            size = block["size"]
            flags = block["flags"]
            page = block["page"]
            
            # Skip if text is too long (likely paragraph)
            if len(text) > 200:
                continue
            
            # Check if this looks like a heading
            is_bold = flags & 2**4  # Bold flag
            is_large = size > avg_size * 1.2
            is_heading_like = (
                is_bold or is_large or
                text.isupper() or
                any(text.startswith(prefix) for prefix in ["Chapter", "Section", "Part"])
            )
            
            if is_heading_like:
                # Determine heading level based on size
                if size > avg_size * 1.5:
                    level = "H1"
                elif size > avg_size * 1.3:
                    level = "H2"
                elif size > avg_size * 1.1:
                    level = "H3"
                else:
                    level = "H4"
                
                outline.append({
                    "level": level,
                    "text": text,
                    "page": page
                })
    
    except Exception as e:
        print(f"Error in text formatting analysis: {e}")
    
    return outline

def extract_pdf_fallback(pdf_path):
    """
    Fallback method when PyMuPDF is not available.
    Returns basic structure with filename as title.
    """
    return {
        "title": pdf_path.stem.replace('_', ' ').replace('-', ' ').title(),
        "outline": []
    }

def process_pdfs():
    # Get input and output directories
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # For local testing, use current directory structure
    if not input_dir.exists():
        input_dir = Path("sample_dataset/pdfs")
        output_dir = Path("sample_dataset/outputs_generated")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        
        try:
            # Extract outline from PDF
            result = extract_pdf_outline(pdf_file)
            
            # Create output JSON file
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Processed {pdf_file.name} -> {output_file.name}")
            print(f"   Title: {result['title']}")
            print(f"   Outline items: {len(result['outline'])}")
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file.name}: {e}")
            
            # Create empty outline as fallback
            fallback_result = {
                "title": pdf_file.stem,
                "outline": []
            }
            
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(fallback_result, f, indent=2)

if __name__ == "__main__":
    print("Starting PDF processing...")
    process_pdfs() 
    print("Completed PDF processing!")