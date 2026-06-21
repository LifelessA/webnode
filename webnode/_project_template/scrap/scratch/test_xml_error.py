# scratch/test_xml_error.py
import zipfile
import sys

def test_xml():
    docx_path = r"c:\Users\lifel\Downloads\framework\Framework.docx"
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            
        print("XML length:", len(xml_content))
        
        # Try to decode to string
        xml_str = xml_content.decode('utf-8')
        
        # Let's find what is around column 116955
        col = 116955
        start = max(0, col - 100)
        end = min(len(xml_str), col + 100)
        
        print("\n=== CONTEXT AROUND ERROR INDEX ===")
        print(xml_str[start:col])
        print(">>> ERROR HERE <<<")
        print(xml_str[col:end])
        
    except Exception as e:
        print("Error checking XML:", e)

if __name__ == "__main__":
    test_xml()
