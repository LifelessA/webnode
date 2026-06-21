# scratch/scan_framework.py
import os
import zipfile
import xml.etree.ElementTree as ET

def scan_document():
    path = r"c:\Users\lifel\Downloads\framework\Framework.docx"
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return
        
    try:
        with zipfile.ZipFile(path) as z:
            doc_xml = z.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            
            print("=== HEADINGS IN FRAMEWORK.DOCX ===")
            heading_count = 0
            for child in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                # Check for styles
                pStyle = child.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
                text = "".join(t.text for t in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text).strip()
                
                if pStyle is not None:
                    style_val = pStyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                    if style_val and ("Heading" in style_val or style_val.startswith("Heading")):
                        print(f"[{style_val}] {text}")
                        heading_count += 1
                elif text.startswith(("1:", "2:", "3:", "4:", "5:", "6:", "7:", "8:", "9:", "10:")) or text.startswith(("1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "5.1", "5.2", "6.1", "6.2", "7.1", "7.2", "8.1", "8.2", "9.1", "9.2")):
                    print(f"[NoStyle Heading] {text}")
                    heading_count += 1
                    
            print(f"\nTotal Headings Found: {heading_count}")
    except Exception as e:
        print("Error reading document:", e)

if __name__ == "__main__":
    scan_document()
