# scratch/build_clean_report.py
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
import re

# XML Namespace Mapping
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

def make_run(text, bold=False, italic=False, sz=22, font_name="Times New Roman", color="000000"):
    run = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
    rPr = ET.SubElement(run, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
    
    if bold:
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b')
    if italic:
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
        
    rFonts = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts')
    rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii', font_name)
    rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi', font_name)
    
    sz_el = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz')
    sz_el.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', str(sz))
    
    color_el = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color')
    color_el.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', color)
    
    t = ET.SubElement(run, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
    t.text = text
    return run

def make_paragraph(text_runs, style=None, align=None, before_space=0, after_space=120, line_spacing=240, keep_next=False):
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    pPr = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
    
    if style:
        pStyle = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
        pStyle.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', style)
        
    if align:
        jc = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}jc')
        jc.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', align)
        
    spacing = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing')
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before', str(before_space))
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after', str(after_space))
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}line', str(line_spacing))
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lineRule', 'auto')
    
    if keep_next:
        ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}keepNext')
        
    if isinstance(text_runs, str):
        p.append(make_run(text_runs))
    elif isinstance(text_runs, list):
        for run in text_runs:
            p.append(run)
            
    return p

def make_heading(text, level=1):
    sizes = {1: 32, 2: 26, 3: 22}
    sz = sizes.get(level, 22)
    color = "1F497D"
    
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    pPr = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
    
    pStyle = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
    pStyle.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', f"Heading{level}")
    
    ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}keepNext')
    
    spacing = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing')
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before', '240')
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after', '120')
    
    run = make_run(text, bold=True, sz=sz, color=color)
    p.append(run)
    return p

def make_page_break():
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    run = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
    br = ET.SubElement(run, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')
    br.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type', 'page')
    return p

def make_table(headers, rows):
    tbl = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')
    tblPr = ET.SubElement(tbl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblPr')
    
    borders = ET.SubElement(tblPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblBorders')
    for b_type in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        b = ET.SubElement(borders, f'{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{b_type}')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'single')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz', '4')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space', '0')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', 'D3D3D3')
        
    tr = ET.SubElement(tbl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
    for head in headers:
        tc = ET.SubElement(tr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
        tcPr = ET.SubElement(tc, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcPr')
        shd = ET.SubElement(tcPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
        shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'clear')
        shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', 'auto')
        shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill', 'F2F2F2')
        
        p = ET.SubElement(tc, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
        p.append(make_run(head, bold=True, sz=20))
        
    for row in rows:
        tr = ET.SubElement(tbl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
        for cell in row:
            tc = ET.SubElement(tr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
            p = ET.SubElement(tc, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
            p.append(make_run(str(cell), sz=18))
            
    return tbl

def make_code_line(line):
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    pPr = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
    shd = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
    shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'clear')
    shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', 'auto')
    shd.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill', 'F4F4F4')
    
    spacing = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing')
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before', '0')
    spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after', '30')
    
    pbdr = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr')
    left = ET.SubElement(pbdr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}left')
    left.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'single')
    left.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz', '24')
    left.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space', '12')
    left.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', '7F7F7F')
    
    p.append(make_run(line, sz=16, font_name="Courier New"))
    return p

def main():
    workspace_dir = r"c:\Users\lifel\Downloads\framework"
    backup_path = os.path.join(workspace_dir, "Framework_1.docx")
    template_docx_path = os.path.join(workspace_dir, "Framework.docx")
    out_docx_path = os.path.join(workspace_dir, "Framework_updated.docx")
    md_path = os.path.join(workspace_dir, "new repo.md")
    
    # 1. Restore clean template from backup first
    if not os.path.exists(backup_path):
        print(f"Error: Backup file {backup_path} not found. Cannot compile.")
        return
    print("Restoring Framework.docx from backup Framework_1.docx...")
    shutil.copy(backup_path, template_docx_path)
    
    print("Reading new repo.md contents...")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    content = content.replace("\r\n", "\n")
    raw_blocks = content.split("\n\n")
    blocks = [b.strip() for b in raw_blocks if b.strip()]
    
    print(f"Total blocks read from markdown: {len(blocks)}")
    
    # Parse blocks into structured elements
    new_elements = []
    start_block_idx = None
    for idx, b in enumerate(blocks):
        if b.startswith("1: INTRODUCTION"):
            start_block_idx = idx
            break
            
    if start_block_idx is None:
        print("Error: Could not locate '1: INTRODUCTION' in new repo.md.")
        return
        
    print(f"Slicing markdown content starting at block index {start_block_idx}")
    main_blocks = blocks[start_block_idx:]
    
    current_section = ""
    i = 0
    while i < len(main_blocks):
        block = main_blocks[i]
        
        # 1. Headings
        h1_match = re.match(r'^(\d+):\s*(.*)$', block)
        if h1_match:
            chapter_num = h1_match.group(1)
            chapter_title = h1_match.group(2).strip()
            new_elements.append(make_page_break())
            new_elements.append(make_heading(f"{chapter_num}: {chapter_title}", level=1))
            current_section = f"{chapter_num}"
            i += 1
            continue
            
        h2_match = re.match(r'^(\d+\.\d+)\s*(.*)$', block)
        if h2_match:
            sec_num = h2_match.group(1)
            sec_title = h2_match.group(2).strip()
            new_elements.append(make_heading(f"{sec_num} {sec_title}", level=2))
            current_section = sec_num
            i += 1
            continue
            
        # 2. Tables
        if current_section == "6.1" and block == "Node Name":
            table_blocks = main_blocks[i:i+36]
            headers = table_blocks[0:4]
            rows = [table_blocks[r:r+4] for r in range(4, 36, 4)]
            new_elements.append(make_table(headers, rows))
            i += 36
            continue
            
        if current_section == "6.5" and block == "Attack Vector":
            table_blocks = main_blocks[i:i+24]
            headers = table_blocks[0:4]
            rows = [table_blocks[r:r+4] for r in range(4, 24, 4)]
            new_elements.append(make_table(headers, rows))
            i += 24
            continue
            
        if current_section == "7.5" and block == "Parameter Name":
            table_blocks = main_blocks[i:i+18]
            headers = table_blocks[0:3]
            rows = [table_blocks[r:r+3] for r in range(3, 18, 3)]
            new_elements.append(make_table(headers, rows))
            i += 18
            continue
            
        # 3. Code Blocks
        is_code = False
        if current_section.startswith("8."):
            is_code = True
        elif current_section == "7.2" and (
            block.startswith("git clone") or 
            block.startswith("cd ") or 
            block.startswith("python ") or 
            block.startswith("pip install")
        ):
            is_code = True
        elif current_section == "7.7" and block.startswith("export ENV="):
            is_code = True
        elif current_section == "3.9" and (
            "│" in block or "▼" in block or "┌" in block or "─" in block or block.startswith("[WSGI")
        ):
            is_code = True
        elif current_section == "5.3" and (
            block.startswith("<div") or block.startswith("<script") or "EventSource" in block
        ):
            is_code = True
        elif current_section == "4.1" and block.startswith("{"):
            is_code = True
        elif current_section == "4.3" and block.startswith("CREATE TABLE"):
            is_code = True
        elif current_section == "4.4" and block.startswith("CREATE TRIGGER"):
            is_code = True
            
        if is_code:
            lines = block.split("\n")
            for line in lines:
                new_elements.append(make_code_line(line))
            i += 1
            continue
            
        # 4. Plain Paragraphs
        new_elements.append(make_paragraph(block))
        i += 1
        
    print(f"Generated {len(new_elements)} OpenXML body elements.")
    
    # Open template document.xml
    print("Reading template structure...")
    with zipfile.ZipFile(template_docx_path) as z:
        doc_xml = z.read('word/document.xml')
        
    root = ET.fromstring(doc_xml)
    body = root.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
    elements = list(body)
    
    # Identify where actual content starts (after table of contents)
    start_index = None
    toc_passed = False
    
    # To avoid TOC matching: start_index is resolved ONLY when we pass the TOC 
    # AND match the actual start of Chapter 1 outside TOC boundaries.
    for idx, child in enumerate(elements):
        text = "".join(t.text for t in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text).strip()
        # Mark table of contents passed when we see REFERENCES inside TOC
        if "TABLE OF CONTENTS" in text or "Table of Contents" in text:
            toc_passed = True
            continue
            
        # Once TOC is passed, look for the actual "Introduction:" heading
        if toc_passed:
            # Table of contents ends at around the references item
            # We look for the main content start which has styling and says "Introduction:"
            pStyle = child.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
            if text == "Introduction:" and pStyle is not None:
                start_index = idx
                break
                
    if start_index is None:
        start_index = 120 # Fallback
        
    print(f"Slicing main content in template starting at element index {start_index}")
    
    # Delete everything from start_index to the final sectPr element
    del body[start_index:-1]
    
    # Insert new elements before the final sectPr element
    for el in new_elements:
        body.insert(len(body)-1, el)
        
    # Serialize back
    new_doc_xml = ET.tostring(root, encoding='utf-8', method='xml')
    
    print("Writing new ZIP archive container...")
    with zipfile.ZipFile(template_docx_path, 'r') as src:
        with zipfile.ZipFile(out_docx_path, 'w', zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename == 'word/document.xml':
                    dst.writestr(item, new_doc_xml)
                else:
                    dst.writestr(item, src.read(item.filename))
                    
    # Overwrite template
    if os.path.exists(template_docx_path):
        os.remove(template_docx_path)
    os.rename(out_docx_path, template_docx_path)
    print("SUCCESSFULLY COMPILED AND UPDATED Framework.docx CLEANLY!")

if __name__ == "__main__":
    main()
