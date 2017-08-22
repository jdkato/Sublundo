import hashlib
import os

import sublime

from . import graphmod

VIEW_TO_TREE = {}
CHANGE_INDEX = {}


def walk_nodes(nodes):
    for node in nodes:
        if node.get('parent') is not None:
            yield (node, [node.get('parent')])
        else:
            yield (node, [])


def render(tree):
    nodes = tree.nodes()
    dag = sorted(nodes, key=lambda n: n.get('id'), reverse=True)
    current = tree.head().get('id')
    return graphmod.generate(walk_nodes(dag), current).rstrip()


def buffer(view):
    return view.substr(sublime.Region(0, view.size())).encode('utf-8')


def make_session(path):
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    m = hashlib.md5()
    m.update(path.encode())
    return os.path.join(history, m.hexdigest() + '.sublundo-session')


def check_view(view):
    """
    @brief      { function_description }

    @param      view  The view

    @return     { description_of_the_return_value }
    """
    if not view.file_name():
        return ('', 0)

    loc = make_session(view.file_name())
    if loc not in VIEW_TO_TREE:
        return (loc, 0)

    return (loc, 1)
