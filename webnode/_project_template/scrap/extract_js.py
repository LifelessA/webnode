import json

with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    graph = json.load(f)

for node in graph.get('nodes', []):
    if node['type'] == 'RenderNode' and node.get('config', {}).get('filename', '') == 'admin.html':
        html = node['config']['html_code']
        start_idx = html.find('<script>') + 8
        end_idx = html.rfind('</script>')
        js_code = html[start_idx:end_idx]
        
        with open('admin_script.js', 'w', encoding='utf-8') as jsf:
            jsf.write(js_code)
        print("JS written to admin_script.js")
        break
