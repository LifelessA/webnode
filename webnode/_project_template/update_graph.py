import json
with open('node_editor/graph.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for node in data['nodes']:
    if node['type'] == 'RenderNode':
        filename = node['config'].get('filename')
        if filename == 'index.html':
            with open('templates/index.html', 'r', encoding='utf-8') as hf:
                node['config']['html_code'] = hf.read()
        elif filename == 'login.html':
            with open('templates/login.html', 'r', encoding='utf-8') as hf:
                node['config']['html_code'] = hf.read()

with open('node_editor/graph.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)
