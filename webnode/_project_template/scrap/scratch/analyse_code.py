import os
import ast

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}
        
    lines = content.splitlines()
    loc = len(lines)
    
    classes = 0
    functions = 0
    
    # Parse Python files
    if filepath.endswith('.py'):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes += 1
                elif isinstance(node, ast.FunctionDef):
                    functions += 1
        except Exception:
            # Fallback regex if it doesn't parse
            for line in lines:
                l = line.strip()
                if l.startswith('def '):
                    functions += 1
                elif l.startswith('class '):
                    classes += 1
                    
    return {
        "loc": loc,
        "classes": classes,
        "functions": functions,
        "size": len(content)
    }

def main():
    root_dir = r"c:\Users\lifel\Downloads\framework"
    exclude_dirs = [".git", "__pycache__", "venv", ".gemini", "db.sqlite3", "sessions.db"]
    
    results = []
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in ['.py', '.js', '.css', '.html', '.json']:
                continue
            if file in ['db.sqlite3', 'sessions.db', 'package.json']:
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, root_dir)
            analysis = analyze_file(full_path)
            analysis['path'] = rel_path.replace('\\', '/')
            results.append(analysis)
            
    print("| File | LOC | Classes | Functions | Size (Bytes) |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    total_loc = 0
    total_bytes = 0
    for res in sorted(results, key=lambda x: x['path']):
        if 'error' in res:
            continue
        print(f"| `{res['path']}` | {res['loc']} | {res['classes']} | {res['functions']} | {res['size']} |")
        total_loc += res['loc']
        total_bytes += res['size']
    print(f"\n**Total Files**: {len(results)}")
    print(f"**Total LOC**: {total_loc}")
    print(f"**Total Size**: {total_bytes} bytes")

if __name__ == "__main__":
    main()
