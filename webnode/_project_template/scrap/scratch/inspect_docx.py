import os
import zipfile
import xml.etree.ElementTree as ET

def get_docx_text(docx_path):
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    
    if not os.path.exists(docx_path):
        return f"File not found: {docx_path}"
        
    try:
        with zipfile.ZipFile(docx_path) as z:
            doc_xml = z.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            
            paragraphs = []
            for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                p_text = []
                for r in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
                    for t in r.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                        if t.text:
                            p_text.append(t.text)
                text = "".join(p_text)
                if text.strip():
                    paragraphs.append(text)
            return paragraphs
    except Exception as e:
        return f"Error reading docx: {e}"

def main():
    docx_path = r"c:\Users\lifel\Downloads\framework\HeartGuard_AI_report (1).docx"
    paragraphs = get_docx_text(docx_path)
    output_path = r"c:\Users\lifel\Downloads\framework\scratch\inspect_output.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        if isinstance(paragraphs, str):
            f.write(paragraphs)
            return
            
        f.write(f"Total paragraphs: {len(paragraphs)}\n\n")
        for idx, p in enumerate(paragraphs):
            f.write(f"[{idx+1}] {p}\n")
            
    print("Inspection complete. Saved to:", output_path)

if __name__ == '__main__':
    main()
