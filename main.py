import os

import sublime
import sublime_plugin

from .lib import (util, tree)


class SublundoNextNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward=None):
        output = sublime.active_window().active_view().id()
        b_view = util.VIS_TO_VIEW[output]
        if forward:
            b_view.run_command('sublundo', {'command': 'redo'})
        else:
            b_view.run_command('sublundo', {'command': 'undo'})
        b_view.run_command('sublundo_visualize', {'output': output})


class SublundoSwitchBranchCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward=0):
        output = sublime.active_window().active_view().id()
        b_view = util.VIS_TO_VIEW[output]
        util.VIEW_TO_TREE[b_view.id()]['tree'].switch_branch(forward)


class SublundoVisualizeCommand(sublime_plugin.TextCommand):
    """SublundoVisualize manages the display and navigation of the UndoTree.
    """
    def run(self, edit, output=None):
        """Display the tree.
        """
        if util.check_view(self.view):
            # Find our visualization view:
            if output is None:
                # We don't have an output view, so it's an initial draw.
                window = sublime.active_window()
                old = window.active_view()
                view = window.new_file()

                nag, group = util.set_active_group(window, view, 'left')

                util.VIS_TO_VIEW[view.id()] = self.view

                view.set_name('Sublundo: History View')
                view.settings().set('gutter', False)
                view.settings().set('word_wrap', False)

                buf = util.render(util.VIEW_TO_TREE[self.view.id()]['tree'])
                view.replace(edit, sublime.Region(0, view.size()), buf)

                view.set_syntax_file(
                    'Packages/Sublundo/Sublundo.sublime-syntax')
                view.set_read_only(True)
                view.set_scratch(True)
                view.sel().clear()

                window.run_command('hide_overlay')
                window.focus_view(old)
                window.focus_view(view)
                if not window.find_output_panel('sublundo'):
                    p = window.create_output_panel('sublundo', False)
                    p.assign_syntax('Packages/Diff/Diff.sublime-syntax')
                window.run_command('show_panel', {'panel': 'output.sublundo'})
            else:
                # We were given an output view, so it's a re-draw.
                view = sublime.View(output)
                buf = util.render(util.VIEW_TO_TREE[self.view.id()]['tree'])

                view.set_read_only(False)
                view.replace(edit, sublime.Region(0, view.size()), buf)
                view.set_read_only(True)
                sublime.active_window().focus_view(view)

            pos = view.find_by_selector('keyword.other.sublundo.tree.position')
            view.show(pos[0], True)


class SublundoCommand(sublime_plugin.TextCommand):
    """Sublundo calls a given PyUndoTree's `undo` or `redo` method.
    """
    def run(self, edit, command):
        """Update the current view with the result of calling undo or redo.
        """
        t = util.VIEW_TO_TREE[self.view.id()]['tree']
        if command == 'undo':
            buf, diff, pos = t.undo()
        else:
            buf, diff, pos = t.redo()

        self.view.replace(edit, sublime.Region(0, self.view.size()), buf)
        if pos:
            line = self.view.line(pos - 1)
            self.view.add_regions(
                'sublundo',
                [line],
                'comment',
                '',
                sublime.DRAW_NO_FILL)
            self.view.show(line)

        p = sublime.active_window().find_output_panel('sublundo')
        if p and diff:
            p.replace(edit, sublime.Region(0, p.size()), diff)


class UndoEventListener(sublime_plugin.EventListener):
    """
    UndoEventListener manages UndoTrees on a view-specific basis: each view
    is assigned its own tree, which controls its undo/redo functionality.
    """
    def on_activated(self, view):
        """Initialize a new UndoTree for new buffers.
        """
        name = view.file_name()
        if name and not util.check_view(view):
            loc = util.make_session(name)
            buf = util.buffer(view)
            t, loaded = tree.load_session(loc, buf)
            if loaded:
                util.debug('Loaded session for {0}.'.format(name))
            else:
                t.insert(buf)
            util.VIEW_TO_TREE[view.id()] = {'tree': t, 'loc': loc}

    def on_close(self, view):
        """
        """
        if 'text.sublundo.tree' not in view.scope_name(0):
            return

        w = sublime.active_window()
        single = not w.views_in_group(0) or not w.views_in_group(1)
        if w.num_groups() == 2 and single:
            sublime.set_timeout(lambda: w.set_layout(
                {
                    "cols": [0.0, 1.0],
                    "rows": [0.0, 1.0],
                    "cells": [[0, 0, 1, 1]]
                }
            ), 300)
        w.run_command('hide_panel', {'panel': 'output.sublundo'})
        for v in w.views():
            v.erase_regions('sublundo')

    def on_pre_close(self, view):
        """
        """
        '''
        loc, found = util.check_view(view)
        if loc and found:
            tree.save_session(util.VIEW_TO_TREE[loc], loc)
        '''

    def on_modified(self, view):
        """Update the view's PyUndoTree when there has been a buffer change.
        """
        cmd = view.command_history(0, True)[0]
        if util.check_view(view) and cmd not in ('sublundo'):
            util.VIEW_TO_TREE[view.id()]['tree'].insert(
                util.buffer(view),
                view.sel()[0].begin()
            )

    def on_text_command(self, view, command_name, args):
        """Run `sublundo` instead of the built-in undo/redo commands.
        """
        triggers = ('undo', 'redo_or_repeat', 'redo')
        if util.check_view(view) and command_name in triggers:
            return ('sublundo', {'command': command_name})
        return None


def plugin_loaded():
    """Ensure that our session storage location exists.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.makedirs(history)
