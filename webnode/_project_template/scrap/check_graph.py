import json
with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for n in data.get('nodes', []):
    print(n['id'], n['type'])
