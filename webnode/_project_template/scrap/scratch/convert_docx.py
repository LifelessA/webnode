import os
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

def markdown_to_docx_xml(md_text):
    # Standard XML namespace declarations
    xml_header = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '<w:body>\n'
    )
    xml_footer = '</w:body>\n</w:document>'
    
    body_elements = []
    
    # Split text into lines
    lines = md_text.splitlines()
    in_code_block = False
    code_block_lines = []
    
    in_table = False
    table_rows = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                in_code_block = False
                code_text = '\n'.join(code_block_lines)
                
                # Write code paragraph with Courier font and shading
                xml_para = (
                    '<w:p>\n'
                    '  <w:pPr>\n'
                    '    <w:shd w:val="clear" w:color="auto" w:fill="F4F4F4"/>\n'
                    '    <w:pBdr>\n'
                    '      <w:left w:val="single" w:sz="24" w:space="12" w:color="7F7F7F"/>\n'
                    '    </w:pBdr>\n'
                    '  </w:pPr>\n'
                    f'  <w:r>\n'
                    '    <w:rPr>\n'
                    '      <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>\n'
                    '      <w:sz w:val="18"/>\n'
                    '    </w:rPr>\n'
                    f'    <w:t>{escape(code_text)}</w:t>\n'
                    '  </w:r>\n'
                    '</w:p>'
                )
                body_elements.append(xml_para)
                code_block_lines = []
            else:
                in_code_block = True
            i += 1
            continue
            
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Handle tables
        if line.strip().startswith('|'):
            # Table row detected
            if not in_table:
                in_table = True
                table_rows = []
            
            # Skip separator line (e.g. | :--- | :--- |)
            if re.match(r'^\s*\|\s*[:\-|\s]+\s*$', line):
                i += 1
                continue
                
            cells = [c.strip() for c in line.split('|')[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                # End of table, compile table XML
                in_table = False
                xml_table = (
                    '<w:tbl>\n'
                    '  <w:tblPr>\n'
                    '    <w:tblBorders>\n'
                    '      <w:top w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>\n'
                    '      <w:left w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>\n'
                    '      <w:bottom w:val="single" w:sz="8" w:space="0" w:color="A0A0A0"/>\n'
                    '      <w:right w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>\n'
                    '      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>\n'
                    '      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>\n'
                    '    </w:tblBorders>\n'
                    '  </w:tblPr>\n'
                )
                for r_idx, row in enumerate(table_rows):
                    xml_table += '  <w:tr>\n'
                    for cell in row:
                        # Clean cell text from inline markdown (like `code` or **bold**)
                        clean_cell = re.sub(r'\*\*([^*]+)\*\*', r'\1', cell)
                        clean_cell = re.sub(r'`([^`]+)`', r'\1', clean_cell)
                        
                        is_header = (r_idx == 0)
                        shading = ' w:fill="F2F2F2"' if is_header else ''
                        bold_tag = '<w:b/>' if is_header else ''
                        
                        xml_table += (
                            '    <w:tc>\n'
                            '      <w:tcPr>\n'
                            f'        <w:shd w:val="clear" w:color="auto"{shading}/>\n'
                            '      </w:tcPr>\n'
                            '      <w:p>\n'
                            '        <w:r>\n'
                            f'          <w:rPr>{bold_tag}</w:rPr>\n'
                            f'          <w:t>{escape(clean_cell)}</w:t>\n'
                            '        </w:r>\n'
                            '      </w:p>\n'
                            '    </w:tc>\n'
                        )
                    xml_table += '  </w:tr>\n'
                xml_table += '</w:tbl>'
                body_elements.append(xml_table)
                table_rows = []

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Handle headings
        h_match = re.match(r'^(#{1,6})\s*(.*)$', line)
        if h_match:
            level = len(h_match.group(1))
            title = h_match.group(2).strip()
            
            # Clean formatting symbols from title
            title = re.sub(r'\*\*([^*]+)\*\*', r'\1', title)
            
            # Size in half-points (24 = 12pt, 36 = 18pt, etc.)
            sizes = {1: 36, 2: 28, 3: 24, 4: 20}
            sz = sizes.get(level, 20)
            
            xml_para = (
                '<w:p>\n'
                '  <w:pPr>\n'
                f'    <w:pStyle w:val="Heading{level}"/>\n'
                '    <w:keepNext/>\n'
                '  </w:pPr>\n'
                '  <w:r>\n'
                '    <w:rPr>\n'
                '      <w:b/>\n'
                '      <w:color w:val="1F497D"/>\n'
                f'      <w:sz w:val="{sz}"/>\n'
                '    </w:rPr>\n'
                f'    <w:t>{escape(title)}</w:t>\n'
                '  </w:r>\n'
                '</w:p>'
            )
            body_elements.append(xml_para)
            i += 1
            continue

        # Handle lists (bullet points)
        list_match = re.match(r'^\s*[-\*+]\s+(.*)$', line)
        if list_match:
            content = list_match.group(1).strip()
            # Inline bold/code styling replacements
            content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
            content = re.sub(r'`([^`]+)`', r'\1', content)
            
            xml_para = (
                '<w:p>\n'
                '  <w:pPr>\n'
                '    <w:ind w:left="360" w:hanging="180"/>\n'
                '  </w:pPr>\n'
                '  <w:r>\n'
                '    <w:t>• </w:t>\n'
                '  </w:r>\n'
                '  <w:r>\n'
                f'    <w:t>{escape(content)}</w:t>\n'
                '  </w:r>\n'
                '</w:p>'
            )
            body_elements.append(xml_para)
            i += 1
            continue

        # Handle plain paragraphs (and parse bold/code fragments)
        para_text = line.strip()
        
        # Check if line is horizontal rule
        if para_text == '---':
            xml_para = (
                '<w:p>\n'
                '  <w:pPr>\n'
                '    <w:pBdr>\n'
                '      <w:bottom w:val="single" w:sz="6" w:space="1" w:color="7F7F7F"/>\n'
                '    </w:pBdr>\n'
                '  </w:pPr>\n'
                '</w:p>'
            )
            body_elements.append(xml_para)
            i += 1
            continue
            
        # Parse bold formatting: split by **
        parts = re.split(r'(\*\*[^*]+\*\*)', para_text)
        xml_para = '<w:p>\n'
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                bold_text = part[2:-2]
                xml_para += (
                    '  <w:r>\n'
                    '    <w:rPr><w:b/></w:rPr>\n'
                    f'    <w:t>{escape(bold_text)}</w:t>\n'
                    '  </w:r>\n'
                )
            else:
                # Check for inline code `
                code_parts = re.split(r'(`[^`]+`)', part)
                for c_part in code_parts:
                    if c_part.startswith('`') and c_part.endswith('`'):
                        code_txt = c_part[1:-1]
                        xml_para += (
                            '  <w:r>\n'
                            '    <w:rPr>\n'
                            '      <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>\n'
                            '      <w:color w:val="A31515"/>\n'
                            '    </w:rPr>\n'
                            f'    <w:t>{escape(code_txt)}</w:t>\n'
                            '  </w:r>\n'
                        )
                    else:
                        if c_part:
                            xml_para += (
                                '  <w:r>\n'
                                f'    <w:t>{escape(c_part)}</w:t>\n'
                                '  </w:r>\n'
                            )
        xml_para += '</w:p>'
        body_elements.append(xml_para)
        i += 1

    return xml_header + '\n'.join(body_elements) + xml_footer

def create_docx(md_path, docx_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
        
    document_xml = markdown_to_docx_xml(md_text)
    
    # Files needed for standard DOCX container zip file
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '</Types>'
    )
    
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/relationship-details/2006/relationships">\n'
        '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '</Relationships>'
    )
    
    # Package into a zip archive (which IS the docx file format)
    with zipfile.ZipFile(docx_path, 'w') as docx:
        docx.writestr('[Content_Types].xml', content_types_xml)
        docx.writestr('_rels/.rels', rels_xml)
        docx.writestr('word/document.xml', document_xml)
        
    print(f"Successfully converted {md_path} -> {docx_path}")

if __name__ == '__main__':
    workspace_dir = r"c:\Users\lifel\Downloads\framework"
    md_file = os.path.join(workspace_dir, "framework_comprehensive_report.md")
    docx_file = os.path.join(workspace_dir, "framework_comprehensive_report.docx")
    
    create_docx(md_file, docx_file)
