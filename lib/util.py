import hashlib
import os

import sublime

from . import graphmod

SETTING_FILE = 'Sublundo.sublime-settings'
VIEW_TO_TREE = {}
VIS_TO_VIEW = {}


def calc_width(view):
    '''
    return float width, which must be
        0.0 < width < 1.0 (other values acceptable, but cause unfriendly layout)
    used in show.show() and "dired_select" command with other_group=True
    '''
    width = view.settings().get('tree_width', 0.3)
    if isinstance(width, float):
        width -= width // 1  # must be less than 1
    elif isinstance(width, int):  # assume it is pixels
        wport = view.viewport_extent()[0]
        width = 1 - round((wport - width) / wport, 2)
        if width >= 1:
            width = 0.9
    else:
        sublime.error_message(u'FileBrowser:\n\ndired_width set to '
                              u'unacceptable type "%s", please change it.\n\n'
                              u'Fallback to default 0.3 for now.' % type(width))
        width = 0.3
    return width or 0.1  # avoid 0.0


def get_group(groups, nag):
    '''
    groups  amount of groups in window
    nag     number of active group
    return number of neighbour group
    '''
    if groups <= 4 and nag < 2:
        group = 1 if nag == 0 else 0
    elif groups == 4 and nag >= 2:
        group = 3 if nag == 2 else 2
    else:
        group = nag - 1
    return group


def set_active_group(window, view, other_group):
    nag = window.active_group()
    if other_group:
        group = 0 if other_group == 'left' else 1
        groups = window.num_groups()
        if groups == 1:
            width = calc_width(view)
            cols = [0.0, width, 1.0] if other_group == 'left' else [
                0.0, 1 - width, 1.0]
            window.set_layout({"cols": cols, "rows": [0.0, 1.0], "cells": [
                              [0, 0, 1, 1], [1, 0, 2, 1]]})
        elif view:
            group = get_group(groups, nag)
        window.set_view_index(view, group, 0)
    else:
        group = nag

    # when other_group is left, we need move all views to right except FB view
    if nag == 0 and other_group == 'left' and group == 0:
        for v in reversed(window.views_in_group(nag)[1:]):
            window.set_view_index(v, 1, 0)

    return (nag, group)


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
