import json
import os

f = 'c:/Users/lifel/Downloads/framework/node_editor/graph.json'
with open(f, 'r', encoding='utf-8') as file:
    d = json.load(file)

for n in d['nodes']:
    if n['type'] == 'LogicNode':
        n['config']['code'] = 'def process_logic(request):\n    return {"status": "ok"}'

with open(f, 'w', encoding='utf-8') as file:
    json.dump(d, file, indent=4)
