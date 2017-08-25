"""main.py

This module is the main entry point into the package. A high-level summary of
the plugin follows:

    * Watch for view `on_activated` events, assigning each view its own
      UndoTree, which we store in `util.VIEW_TO_TREE` for easy access.

    * Watch for an insertion trigger (`on_modified`, by default) to insert the
      current view's contents into the associated UndoTree.

    * Watch for the 'undo', 'redo_or_repeat', or 'redo' commands and overwrite
      them with `sublundo`, which calls either `tree.undo()` or `tree.redo()`
      on the current view.

We also implement a `sublundo_visualize` command, which presents a Gundo-like
visualization of the underlying UndoTree.
"""
import os

import sublime
import sublime_plugin

from .lib import (util, tree)


class SublundoNextNodeCommand(sublime_plugin.TextCommand):
    """SublundoNextNode implements movement in the UndoTree visualization.

    This command is bound to the up (or 'j') and down (or 'k') keys by default.
    """
    def run(self, edit, forward=0):
        """Move to the next node in the tree, if available.

        Args:
            forward (int): Indicates whether we're moving forward or backward.

        Examples:

            @
             \
              2

        <redo>

            1
             \
              @
        """
        # We first grab the ID of the current visualization's view. This tells
        # the `sublundo_visualize` command that we want a re-draw (vs. a new
        # draw).
        output = sublime.active_window().active_view().id()
        # `b_view` is the view associated with the actual text buffer we're
        # changing.
        b_view = util.VIS_TO_VIEW[output]
        if forward:
            b_view.run_command('sublundo', {'command': 'redo'})
        else:
            b_view.run_command('sublundo', {'command': 'undo'})

        b_view.run_command('sublundo_visualize', {'output': output})


class SublundoSwitchBranchCommand(sublime_plugin.TextCommand):
    """SublundoSwitchBranch controls branch switching in a visualization.
    """
    def run(self, edit, forward=0):
        """Switch to the next branch (as indicated by `forward`), if possible.

        Args:
            forward (int): Indicates whether to move to the next or previous
            branch.

        Examples:

             @                         1
            / \     -> <redo> ->      / \
           3   2                     3   @

        <undo>
        <switch_branch>

             @                         1
            / \     -> <redo> ->      / \
           3   2                     @   2
        """
        output = sublime.active_window().active_view().id()
        b_view = util.VIS_TO_VIEW[output]
        util.VIEW_TO_TREE[b_view.id()]['tree'].switch_branch(forward)


class SublundoVisualizeCommand(sublime_plugin.TextCommand):
    """SublundoVisualize manages the display the UndoTree and its diff preview.
    """
    def run(self, edit, output=False):
        """Display the tree and its diff preview.

        Args:
            output (bool): Indicates if we're re-drawing the tree.
        """
        if util.check_view(self.view):
            # Find our visualization view:
            if not output:
                # We don't have an output view, so it's an initial draw.
                window = sublime.active_window()
                old = window.active_view()
                view = window.new_file()

                # Set the layout.
                # TODO: make this a settings.
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

            # Move to the active node.
            pos = view.find_by_selector('keyword.other.sublundo.tree.position')
            if pos:
                view.show(pos[0], True)
            else:
                t = util.VIEW_TO_TREE[self.view.id()]['tree']
                util.debug('No active node? Total size = {0}.'.format(len(t)))


class SublundoCommand(sublime_plugin.TextCommand):
    """Sublundo calls a given UndoTree's `undo` or `redo` method.
    """
    def run(self, edit, command):
        """Update the current view with the result of calling `undo` or `redo`.

        Args:
            command (str): 'undo', 'redo', or 'redo_or_repeat'.
        """
        t = util.VIEW_TO_TREE[self.view.id()]['tree']
        if command == 'undo':
            buf, diff, pos = t.undo()
        else:
            buf, diff, pos = t.redo()

        self.view.replace(edit, sublime.Region(0, self.view.size()), buf)
        if pos:
            # Draw an outline around the line that's changing.
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
    """UndoEventListener manages UndoTrees on a view-specific basis.
    """
    def on_activated(self, view):
        """Initialize a new UndoTree for the view, if we haven't already.
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
            util.CHANGE_INDEX[view.id()] = 0

    def on_close(self, view):
        """Clean up the visualization.
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
        """Save the current sessions.

        TODO: work on this.
        """
        '''
        loc, found = util.check_view(view)
        if loc and found:
            tree.save_session(util.VIEW_TO_TREE[loc], loc)
        '''

    def on_text_command(self, view, command_name, args):
        """Run `sublundo` instead of the built-in `undo` and `redo` commands.
        """
        triggers = ('undo', 'redo_or_repeat', 'redo')
        if util.check_view(view) and command_name in triggers:
            return ('sublundo', {'command': command_name})
        elif command_name != 'sublundo' and view.id() in util.CHANGE_INDEX:
            if util.CHANGE_INDEX[view.id()] != view.change_count():
                util.VIEW_TO_TREE[view.id()]['tree'].insert(
                    util.buffer(view),
                    view.sel()[0].begin()
                )
                util.CHANGE_INDEX[view.id()] = view.change_count()
        return None


def plugin_loaded():
    """Ensure that our session storage location exists.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.makedirs(history)
