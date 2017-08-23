import hashlib
import os

import sublime

from . import graphmod

SETTING_FILE = 'Sublundo.sublime-settings'
VIEW_TO_TREE = {}
VIS_TO_VIEW = {}


def get_setting(name):
    """Return the value associated with the setting `name`.
    """
    settings = sublime.load_settings(SETTING_FILE)
    return settings.get(name, '')


def set_setting(name, value):
    """Store and save `name` as `value`.
    """
    settings = sublime.load_settings(SETTING_FILE)
    settings.set(name, value)
    sublime.save_settings(SETTING_FILE)


def debug(message, prefix='Sublundo', level='debug'):
    """Print a formatted entry to the console.

    Args:
        message (str): A message to print to the console
        prefix (str): An optional prefix
        level (str): One of debug, info, warning, error [Default: debug]

    Returns:
        str: Issue a standard console print command.
    """
    if get_setting('debug'):
        print('{prefix}: [{level}] {message}'.format(message=message,
                                                     prefix=prefix,
                                                     level=level))


def walk_nodes(nodes):
    for node in nodes:
        if node.parent is not None:
            yield (node, [node.parent.idx])
        else:
            yield (node, [])


def render(tree):
    nodes = tree.nodes()
    dag = sorted(nodes, key=lambda n: n.idx, reverse=True)
    current = tree.head().idx
    return graphmod.generate(walk_nodes(dag), current).rstrip()


def buffer(view):
    return view.substr(sublime.Region(0, view.size()))


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
    return view.id() in VIEW_TO_TREE
