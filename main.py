from lib import (graphmod, libundo)

t = libundo.PyUndoTree('test.libundo-session', '')
t.insert('My name is Joe.')
t.insert('My name is actually Bob.')
t.undo()
t.insert('My name is Bob.')


def render(tree):
    nodes = tree.nodes()

    def walk_nodes(nodes):
        for node in nodes:
            if node.get('parent') is not None:
                yield (node, [node.get('parent')])
            else:
                yield (node, [])

    dag = sorted(nodes, key=lambda n: n.get('id'), reverse=True)
    current = 3

    result = graphmod.generate(
        walk_nodes(dag), graphmod.asciiedges, current).rstrip()
    print(result)


render(t)
