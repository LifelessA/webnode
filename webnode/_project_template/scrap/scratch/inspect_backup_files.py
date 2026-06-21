# scratch/inspect_backup_files.py
import os
import zipfile
import xml.etree.ElementTree as ET

def get_docx_title(path):
    if not os.path.exists(path):
        return "Not found"
    try:
        with zipfile.ZipFile(path) as z:
            doc_xml = z.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            paragraphs = []
            for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                text = "".join(t.text for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text).strip()
                if text:
                    paragraphs.append(text)
                    if len(paragraphs) >= 8:
                        break
            return paragraphs
    except Exception as e:
        return f"Error: {e}"

def main():
    files = [
        "Framework.docx",
        "Framework_1.docx",
        "HeartGuard_AI_report (1).docx",
        "Web_Node_report.docx",
        "Web_Node_report_1.docx",
        "framework_comprehensive_report.docx"
    ]
    cwd = r"c:\Users\lifel\Downloads\framework"
    for f in files:
        path = os.path.join(cwd, f)
        print(f"\n=== FILE: {f} ===")
        print("Size:", os.path.getsize(path) if os.path.exists(path) else "N/A")
        paragraphs = get_docx_title(path)
        if isinstance(paragraphs, list):
            for i, p in enumerate(paragraphs):
                print(f"[{i+1}] {p[:120]}")
        else:
            print(paragraphs)

if __name__ == "__main__":
    main()
