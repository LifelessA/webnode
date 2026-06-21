import sys, json, os
sys.path.append(r'c:\Users\lifel\Downloads\framework\node_editor')
import node_backend

class Dummy: pass
handler = Dummy()
handler.compile_graph = node_backend.EditorHandler.compile_graph.__get__(handler)
with open(r'c:\Users\lifel\Downloads\framework\node_editor\graph.json', 'r', encoding='utf-8') as f:
    graph = json.load(f)

handler.compile_graph(graph)
print("Graph compiled successfully.")
