# scratch/restore_check.py
import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET

def get_first_paragraphs(path, count=5):
    if not os.path.exists(path):
        return "File not found."
    try:
        with zipfile.ZipFile(path) as z:
            doc_xml = z.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            paragraphs = []
            for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                text = "".join(t.text for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text)
                if text.strip():
                    paragraphs.append(text.strip())
                    if len(paragraphs) >= count:
                        break
            return paragraphs
    except Exception as e:
        return f"Error: {e}"

def main():
    cwd = r"c:\Users\lifel\Downloads\framework"
    print("=== GIT CHECK ===")
    try:
        res = subprocess.run(["git", "status"], cwd=cwd, capture_output=True, text=True)
        print("Git Status Output:\n", res.stdout)
        print("Git Status Error:\n", res.stderr)
    except Exception as e:
        print("Git check failed:", e)

    print("\n=== DOCX COMPARISON ===")
    print("Framework.docx first 3 paragraphs:")
    print(get_first_paragraphs(os.path.join(cwd, "Framework.docx"), 3))
    
    print("\nFramework_1.docx first 3 paragraphs:")
    print(get_first_paragraphs(os.path.join(cwd, "Framework_1.docx"), 3))

if __name__ == "__main__":
    main()
