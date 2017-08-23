import os

import sublime
import sublime_plugin

from .lib import util, libundo


class SublundoVisualizeCommand(sublime_plugin.TextCommand):
    """
    """
    def run(self, edit):
        """
        """
        active = sublime.active_window().active_view()
        loc, found = util.check_view(active)
        if loc and found:
            t = util.VIEW_TO_TREE[loc]
            view = sublime.active_window().new_file()
            view.set_name('Sublundo History')
            view.settings().set('gutter', False)
            view.settings().set('word_wrap', False)

            buf = util.render(t)
            view.replace(edit, sublime.Region(0, view.size()), buf)

            view.set_read_only(True)
            view.set_scratch(True)


class SublundoCommand(sublime_plugin.TextCommand):
    """Sublundo calls a given PyUndoTree's `undo` or `redo` method.
    """
    def run(self, edit, loc, command):
        """Update the current view with the result of calling undo or redo.
        """
        tree = util.VIEW_TO_TREE[loc]
        if command == 'undo':
            buf = tree.undo().decode('utf-8')
        else:
            buf = tree.redo().decode('utf-8')
        self.view.replace(edit, sublime.Region(0, self.view.size()), buf)


class UndoEventListener(sublime_plugin.EventListener):
    """
    UndoEventListener manages PyUndoTrees on a view-specific basis: each view
    is assigned its own tree, which controls its undo/redo functionality.
    """
    def on_activated(self, view):
        """Initialize a new PyUndoTree for new buffers.
        """
        loc, found = util.check_view(view)
        if loc and not found:
            t = libundo.PyUndoTree(loc.encode('utf-8'), util.buffer(view))
            util.VIEW_TO_TREE[loc] = t
            util.CHANGE_INDEX[loc] = view.change_count()

    def on_post_text_command(self, view, command_name, args):
        """Update the view's PyUndoTree when there has been a buffer change.
        """
        loc, found = util.check_view(view)
        if loc and found and util.CHANGE_INDEX[loc] != view.change_count():
            util.VIEW_TO_TREE[loc].insert(util.buffer(view))
            util.CHANGE_INDEX[loc] = view.change_count()

    def on_text_command(self, view, command_name, args):
        """Run `sublundo` instead of the built-in undo/redo commands.
        """
        loc, found = util.check_view(view)
        if loc and found and command_name in ('undo', 'redo'):
            return ('sublundo', {'loc': loc, 'command': command_name})
        return None


def plugin_loaded():
    """Ensure that our session storage location exists.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.makedirs(history)


def plugin_unloaded():
    """Save our session data.
    """
    for tree in util.VIEW_TO_TREE.values():
        tree.save()
