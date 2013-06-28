from pygraphviz import *
import textwrap

class Node:
    def __init__(self, id, label, edges={}, **kwargs):
        self.id = id
        self.label = '\\n'.join(textwrap.wrap(label, 25))
        self.edges = edges # to_id : {attr=val}
        self.attr = kwargs


def create_nodes(graph, nodes):
    for node in nodes:
        add_node(graph, node)
        for edge in node.edges:
            graph.add_edge(node.id, edge, **node.edges[edge])

def add_node(graph, node):
    try:
        graph.get_node(node.id).attr.update(label=node.label, **node.attr)
    except KeyError:
        graph.add_node(node.id, label=node.label, **node.attr)

# Init graph
graph = AGraph(name='main', directed=True, strict=False, compound=True,
    labelloc='t', label='Py2Deb')

# Default node attributes
graph.node_attr['shape'] = 'box'
graph.node_attr['width'] = 3
graph.node_attr['weight'] = 2

# Defining main nodes and edges
nodes = [
    Node(0, 'Parse command line options',
        edges = {
            10 : dict()
        }
    ),
    Node(10, 'Initialize the converter',
        edges = {
            20 : dict()
        }
    ),
    Node(20, 'Download/extract required packages (using pip-accel)',
        edges = {
            30 : dict()
        }
    ),
    Node(30, 'Generate a list of packages that need to be converted',
        edges = {
            40 : dict()
        }
    ),
    Node(40, 'Convert each package',
        edges = {
            50 : dict()
        }
    ),
    Node(50, 'Generate a list of packages that need to be converted',
        edges = {
            60 : dict()
        }
    ),
    Node(60, 'Clean-up')
]

# Defining subgraph for convert step
subgraph = graph.subgraph(name='cluster_0', label='Conversion')
convert_nodes = [
    Node(100, 'Debianize package',
        edges = {
            110 : dict()
        }
    ),
    Node(110, 'Patch rules file',
        edges = {
            120 : dict()
        }
    ),
    Node(120, 'Patch control file',
        edges = {
            130 : dict()
        }
    ),
    Node(130, 'Apply script',
        edges = {
            140 : dict()
        }
    ),
    Node(140, 'Sanity check dependencies',
        edges = {
            150 : dict()
        }
    ),
    Node(150, 'Build package',
        edges = {
            160 : dict()
        }
    ),
    Node(160, 'Move package to repository')
]

create_nodes(graph, nodes)
create_nodes(subgraph, convert_nodes)
graph.add_edge(40, 100, lhead='cluster_0', constraint=False, tailport='w')

# Output
print(graph)
graph.draw('py2deb_workflow.png', prog='dot')