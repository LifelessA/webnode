import json

with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    graph = json.load(f)

for node in graph.get('nodes', []):
    if node['type'] == 'RenderNode' and node.get('config', {}).get('filename', '') == 'admin.html':
        html = node['config']['html_code']
        
        # Find all </script> positions
        pos = 0
        idx = 0
        while True:
            pos = html.find('</script>', pos)
            if pos == -1:
                break
            idx += 1
            # Show context around each </script>
            start = max(0, pos - 100)
            end = min(len(html), pos + 20)
            print(f"=== </script> #{idx} at position {pos} ===")
            print(html[start:end])
            print()
            pos += 1
        
        # Find all <script positions
        pos = 0
        idx = 0
        while True:
            pos = html.find('<script', pos)
            if pos == -1:
                break
            idx += 1
            start = max(0, pos - 50)
            end = min(len(html), pos + 100)
            print(f"=== <script #{idx} at position {pos} ===")
            print(html[start:end])
            print()
            pos += 1
