# scratch/find_original_in_zip.py
import os
import zipfile

def search_zips():
    downloads_dir = r"c:\Users\lifel\Downloads"
    for f in os.listdir(downloads_dir):
        if f.endswith(".zip") and f.startswith("framework"):
            zip_path = os.path.join(downloads_dir, f)
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    for name in z.namelist():
                        if "Framework.docx" in name:
                            info = z.getinfo(name)
                            print(f"Archive: {f} | File: {name} | Size: {info.file_size} bytes")
            except Exception as e:
                print(f"Error reading {f}: {e}")

if __name__ == "__main__":
    search_zips()
