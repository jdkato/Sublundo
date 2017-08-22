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
        pass
        '''
        v = sublime.active_window().active_view()
        loc = util.make_session(v.file_name())
        if loc not in VIEW_TO_TREE:
            return

        tree = VIEW_TO_TREE[loc]
        print("HMM", tree)
        view = sublime.active_window().new_file()
        view.set_name('Sublundo History')
        view.settings().set('gutter', False)
        view.settings().set('word_wrap', False)

        buf = util.render(tree.nodes(), tree.head().get('id'))
        view.replace(edit, sublime.Region(0, view.size()), buf)

        view.set_read_only(True)
        view.set_scratch(True)
        '''


class SublundoCommand(sublime_plugin.TextCommand):
    """
    """
    def run(self, edit, tree, command):
        """
        """
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
        pass
        '''
        global VIEW_TO_TREE
        if not view.file_name():
            return

        loc = util.make_session(view.file_name())
        if loc not in VIEW_TO_TREE:
            t = libundo.PyUndoTree(loc.encode('utf-8'), util.buffer(view))
            VIEW_TO_TREE[loc] = t
        '''

    def on_text_command(self, view, command_name, args):
        """
        @brief      { function_description }

        @param      self          The object
        @param      view          The view
        @param      command_name  The command name
        @param      args          The arguments

        @return     { description_of_the_return_value }
        """
        if not view.file_name():
            return None

        loc = util.make_session(view.file_name())
        '''
        if loc not in VIEW_TO_TREE:
            return None

        t = VIEW_TO_TREE[loc]

        if command_name in ('undo', 'redo'):
            t = libundo.PyUndoTree(loc.encode('utf-8'), util.buffer(view))
            return ('sublundo', {'tree': t, 'command': command_name})
        elif command_name == '_enter_normal_mode':
            t = libundo.PyUndoTree(loc.encode('utf-8'), util.buffer(view))
            # TODO: make trigger a setting
            t.insert(util.buffer(view))
        '''

        return None


def plugin_loaded():
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.mkdirs(history)


def plugin_unloaded():
    """
    @brief      { function_description }

    @return     { description_of_the_return_value }
    """
    pass
    '''
    for tree in VIEW_TO_TREE.values():
        tree.save()
    '''
