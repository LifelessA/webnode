import sys, json, os
with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

nodes = {n['id']: n for n in graph_data['nodes']}
connections = graph_data['connections']
server_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'ServerNode'), None)

outgoing_map = {}
for c in connections:
    source_id = c.get('source') or c.get('from')
    target_id = c.get('target') or c.get('to')
    if source_id and target_id:
        if source_id not in outgoing_map:
            outgoing_map[source_id] = []
        outgoing_map[source_id].append(target_id)
        
reachable_ids = []
queue = [server_node_id]
while queue:
    curr = queue.pop(0)
    if curr not in reachable_ids:
        reachable_ids.append(curr)
        for tgt in outgoing_map.get(curr, []):
            queue.append(tgt)
            
print("Reachable:", reachable_ids)
