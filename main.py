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
    """
    """
    def run(self, edit, loc, command):
        """
        """
        tree = util.VIEW_TO_TREE[loc]
        if command == 'undo':
            buf = tree.undo().decode('utf-8')
        else:
            buf = tree.redo().decode('utf-8')
        self.view.replace(edit, sublime.Region(0, self.view.size()), buf)


class UndoEventListener(sublime_plugin.EventListener):
    """
    @brief      Class for undo event listener.
    """
    def on_activated(self, view):
        """
        """
        loc, found = util.check_view(view)
        if loc and not found:
            t = libundo.PyUndoTree(loc.encode('utf-8'), util.buffer(view))
            util.VIEW_TO_TREE[loc] = t

    def on_post_text_command(self, view, command_name, args):
        """
        """
        loc, found = util.check_view(view)
        if not (loc and found):
            return None
        t = util.VIEW_TO_TREE[loc]
        new = util.buffer(view)
        old = t.buffer()
        if old != new:
            t.insert(new)
            print(view.file_name(), len(t))

    def on_text_command(self, view, command_name, args):
        """
        @brief      { function_description }

        @param      self          The object
        @param      view          The view
        @param      command_name  The command name
        @param      args          The arguments

        @return     { description_of_the_return_value }
        """
        loc, found = util.check_view(view)
        if not (loc and found):
            return None
        elif command_name in ('undo', 'redo'):
            return ('sublundo', {'loc': loc, 'command': command_name})
        return None


def plugin_loaded():
    """
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.mkdirs(history)


def plugin_unloaded():
    """
    @brief      { function_description }

    @return     { description_of_the_return_value }
    """
    for tree in util.VIEW_TO_TREE.values():
        tree.save()
