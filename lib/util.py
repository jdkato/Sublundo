"""util.py

This module contains our utility functions and global variable definitions.

NOTE: `calc_width`, `get_group` and `set_active_group` were borrowed from
https://github.com/aziz/SublimeFileBrowser.
"""
import hashlib
import pickle
import os

import sublime

from . import graphmod
from . import tree

SETTING_FILE = 'Sublundo.sublime-settings'

# `CHANGE_INDEX` maps view IDs to their `change_count()`s. We use this to
# determine when to insert into the view's UndoTree.
CHANGE_INDEX = {}

# `VIEW_TO_TREE` maps view IDs to their UndoTrees.
VIEW_TO_TREE = {}

# `VIS_TO_VIEW` maps visualization view IDs to their actual views.
VIS_TO_VIEW = {}


def save_session(session, path):
    """Save the given UndoTree.
    """
    with open(path, 'wb') as loc:
        pickle.dump(session, loc, pickle.HIGHEST_PROTOCOL)


def load_session(path, buf):
    """Try to load the UndoTree stored on `path`.

    If the current buffer (given by `buf`) doesn't match the last state stored
    on disk, we return a new UndoTree.

    Args:
        path (str): The path to the *.sublundo-session file.
        buf (str): The most recent file contents.

    Returns:
        tree.UndoTree
    """
    if os.path.exists(path):
        try:
            with open(path, 'rb') as loc:
                canidate = pickle.load(loc)
            if hash(canidate.text()) == hash(buf):
                return canidate, True
        except EOFError:
            pass
    return tree.UndoTree(), False


def calc_width(view):
    """Calculate the width for a visualization based on the view port size.
    """
    width = view.settings().get('tree_width', 0.3)
    if isinstance(width, float):
        width -= width // 1  # must be less than 1
    elif isinstance(width, int):  # assume it is pixels
        wport = view.viewport_extent()[0]
        width = 1 - round((wport - width) / wport, 2)
        if width >= 1:
            width = 0.9
    else:
        show_error('Bad `tree_width`; falling back to 0.3.')
        width = 0.3
    return width or 0.1  # avoid 0.0


def show_error(msg):
    """Show an error dialog to the user.
    """
    sublime.error_message('Sublundo [ERROR]: {0}'.format(msg))


def get_group(groups, active_groups):
    """Return number of neighbours based on the number of (active) groups.
    """
    if groups <= 4 and active_groups < 2:
        group = 1 if active_groups == 0 else 0
    elif groups == 4 and active_groups >= 2:
        group = 3 if active_groups == 2 else 2
    else:
        group = active_groups - 1
    return group


def set_active_group(window, view, other_group):
    """Determine the window layout.
    """
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
    """Return all (node, parent) combinations in the given list of nodes.
    """
    for node in nodes:
        if node.parent is not None:
            yield (node, [node.parent.idx])
        else:
            yield (node, [])


def render(tree):
    """Show an ASCII-formatted version of the given UndoTree.
    """
    current = tree.head().idx
    nodes = reversed(tree.nodes())
    return graphmod.generate(walk_nodes(nodes), current).rstrip()


def buffer(view):
    """Return the given view's entire buffer.
    """
    return view.substr(sublime.Region(0, view.size()))


def make_session(path):
    """Make a session file from the given file path.

    TODO: What if a file is re-named? Currently, it's history would be lost.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    m = hashlib.md5(path.encode())
    return os.path.join(history, m.hexdigest() + '.sublundo-session')


def check_view(view):
    """Determine if we've seen the given view yet.
    """
    return view.id() in VIEW_TO_TREE
