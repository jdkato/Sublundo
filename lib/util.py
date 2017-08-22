import os
import sublime

from . import graphmod


def walk_nodes(nodes):
    for node in nodes:
        if node.get('parent') is not None:
            yield (node, [node.get('parent')])
        else:
            yield (node, [])


def render(tree, pos):
    nodes = tree.nodes()
    dag = sorted(nodes, key=lambda n: n.get('id'), reverse=True)
    return graphmod.generate(walk_nodes(dag), pos).rstrip()


def buffer(view):
    return view.substr(sublime.Region(0, view.size())).encode('utf-8')


def make_session(path):
    # TODO: better naming scheme
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    filename, _ = os.path.splitext(path)
    return os.path.join(history, filename + '.sublundo-session')
