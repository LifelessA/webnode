import json
with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for c in data.get('connections', []):
    print(c['source'], '->', c['target'])
