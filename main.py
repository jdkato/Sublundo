import os

import sublime
import sublime_plugin

from .lib import (
    util,
    tree
)


class SublundoVisualizeCommand(sublime_plugin.TextCommand):
    """SublundoVisualize manages the display and navigation of the UndoTree.
    """
    def run(self, edit):
        """Display the tree.
        """
        active = sublime.active_window().active_view()
        loc, found = util.check_view(active)
        if loc and found:
            view = sublime.active_window().new_file()
            view.set_name('Sublundo: History View')
            view.settings().set('gutter', False)
            view.settings().set('word_wrap', False)

            buf = util.render(util.VIEW_TO_TREE[loc])
            view.replace(edit, sublime.Region(0, view.size()), buf)

            view.set_syntax_file('Packages/Sublundo/Sublundo.sublime-syntax')
            view.set_read_only(True)
            view.set_scratch(True)
            view.sel().clear()


class SublundoCommand(sublime_plugin.TextCommand):
    """Sublundo calls a given PyUndoTree's `undo` or `redo` method.
    """
    def run(self, edit, loc, command):
        """Update the current view with the result of calling undo or redo.
        """
        t = util.VIEW_TO_TREE[loc]

        if command == 'undo':
            buf = t.undo()
        else:
            buf = t.redo()

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
            t, loaded = tree.load_session(loc, util.buffer(view))
            util.VIEW_TO_TREE[loc] = t
            util.CHANGE_INDEX[loc] = view.change_count()
            if loaded:
                util.debug('Loaded session for {0}.'.format(view.file_name()))

    def on_pre_close(self, view):
        """
        """
        loc, found = util.check_view(view)
        if loc and found:
            tree.save_session(util.VIEW_TO_TREE[loc], loc)

    def on_modified(self, view):
        """Update the view's PyUndoTree when there has been a buffer change.
        """
        loc, found = util.check_view(view)
        cmd = view.command_history(0, True)[0]
        if loc and found and cmd not in ('sublundo'):
            util.VIEW_TO_TREE[loc].insert(util.buffer(view))

    def on_text_command(self, view, command_name, args):
        """Run `sublundo` instead of the built-in undo/redo commands.
        """
        loc, found = util.check_view(view)
        triggers = ('undo', 'redo_or_repeat', 'redo')
        if loc and found and command_name in triggers:
            return ('sublundo', {'loc': loc, 'command': command_name})
        return None


def plugin_loaded():
    """Ensure that our session storage location exists.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.makedirs(history)
