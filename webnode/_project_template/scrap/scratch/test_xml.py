import os
import zipfile
import xml.etree.ElementTree as ET

def main():
    docx_path = r"c:\Users\lifel\Downloads\framework\HeartGuard_AI_report (1).docx"
    output_path = r"c:\Users\lifel\Downloads\framework\scratch\xml_structure.txt"
    
    if not os.path.exists(docx_path):
        print("Template file not found.")
        return
        
    try:
        with zipfile.ZipFile(docx_path) as z:
            doc_xml = z.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            
            # Find the body element
            body = root.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
            if body is None:
                print("Body element not found.")
                return
                
            children = list(body)
            print(f"Total elements in body: {len(children)}")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"Total elements: {len(children)}\n\n")
                for idx, child in enumerate(children):
                    tag = child.tag.split('}')[-1]
                    text = "".join(t.text for t in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text)
                    snippet = text[:60] if len(text) > 60 else text
                    f.write(f"[{idx}] {tag} | Text: {snippet}\n")
            print("XML structure inspect complete. Saved to:", output_path)
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    main()
