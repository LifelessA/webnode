# scratch/check_new_repo.py
import re

def check_file():
    path = r"c:\Users\lifel\Downloads\framework\new repo.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print("Length of new repo.md:", len(content))
    
    # Find all headings matching '1: INTRODUCTION' or similar
    intro_matches = [m.start() for m in re.finditer(r'1:\s*INTRODUCTION', content)]
    print("Occurrences of '1: INTRODUCTION':", len(intro_matches))
    for idx, pos in enumerate(intro_matches):
        context = content[pos:pos+100].replace('\n', ' ')
        print(f"Match {idx+1} at index {pos}: {context}")

if __name__ == "__main__":
    check_file()
