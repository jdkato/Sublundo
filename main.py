"""main.py

This module is the main entry point into the package. A high-level summary of
the plugin follows   :

    * Watch for view `on_activated` events, assigning each view its own
      UndoTree, which we store in `util.VIEW_TO_TREE` for easy access.

    * Watch for changes to every view's `change_count`, inserting into the
      associated UndoTree on increments.

    * Watch for the 'undo', 'redo_or_repeat', or 'redo' commands and overwrite
      them with `sublundo`, which calls either `tree.undo()` or `tree.redo()`
      on the current view.

We also implement a `sublundo_visualize` command, which presents a Gundo-like
visualization of the underlying UndoTree.
"""
import os
from datetime import datetime, timedelta

import sublime
import sublime_plugin

from .lib import util


class SublundoOpenFileCommand(sublime_plugin.ApplicationCommand):
    """This is a wrapper class for SublimeText's `open_file` command.
    """
    def run(self, f):
        sublime.run_command('open_file', {'file': f})

    def is_visible(self):
        """Hide if `edit_settings` is available.
        """
        return util.ST_VERSION < 3124


class SublundoEditSettingsCommand(sublime_plugin.ApplicationCommand):
    """This is a wrapper class for Sublime Text's `edit_settings` command.
    """
    def run(self, **kwargs):
        sublime.run_command('edit_settings', kwargs)

    def is_visible(self):
        """Only visible if `edit_settings` is available.
        """
        return util.ST_VERSION >= 3124


class SublundoNextNodeCommand(sublime_plugin.TextCommand):
    """SublundoNextNode implements movement in the UndoTree visualization.

    This is bound to the up (or 'j') and down (or 'k') keys by default.
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
            b_view.run_command('sublundo', {'command': 'redo', 'in_vis': True})
        else:
            b_view.run_command('sublundo', {'command': 'undo', 'in_vis': True})

        b_view.run_command('sublundo_visualize', {'output': output})


class SublundoSwitchBranchCommand(sublime_plugin.TextCommand):
    """SublundoSwitchBranch controls branch switching in a visualization.

    This is bound to the left (or 'h') and right (or 'l') keys by default.
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
        vis = None
        if util.check_view(self.view):
            # Find our visualization view:
            if not output:
                # We don't have an output view, so it's an initial draw.
                window = sublime.active_window()
                old = window.active_view()
                vis = window.new_file()

                # Set the layout.
                side = util.get_setting('layout', 'left')
                nag, group = util.set_active_group(window, vis, side)

                util.VIS_TO_VIEW[vis.id()] = self.view
                vis.set_name('Sublundo: History View')
                vis.settings().set('gutter', False)
                vis.settings().set('word_wrap', False)

                buf = util.render(util.VIEW_TO_TREE[self.view.id()]['tree'])
                vis.replace(edit, sublime.Region(0, vis.size()), buf)

                vis.set_syntax_file(
                    'Packages/Sublundo/Sublundo.sublime-syntax')
                vis.set_read_only(True)
                vis.set_scratch(True)
                vis.sel().clear()

                window.run_command('hide_overlay')
                window.focus_view(old)

                if not window.find_output_panel('sublundo'):
                    p = window.create_output_panel('sublundo', False)
                    p.assign_syntax('Packages/Diff/Diff.sublime-syntax')

                if util.get_setting('diff', True):
                    window.run_command('show_panel',
                                       {'panel': 'output.sublundo'})
            else:
                # We were given an output view, so it's a re-draw.
                vis = sublime.View(output)
                buf = util.render(util.VIEW_TO_TREE[self.view.id()]['tree'])

                vis.set_read_only(False)
                vis.replace(edit, sublime.Region(0, vis.size()), buf)
                vis.set_read_only(True)

            # Move to the active node.
            sublime.active_window().focus_view(vis)
            pos = vis.find_by_selector('keyword.other.sublundo.tree.position')
            if pos:
                vis.show(pos[0], True)
            else:
                t = util.VIEW_TO_TREE[self.view.id()]['tree']
                util.debug('No active node? Total size = {0}.'.format(len(t)))


class SublundoCommand(sublime_plugin.TextCommand):
    """Sublundo calls a given UndoTree's `undo` or `redo` method.
    """
    def run(self, edit, command, in_vis=False):
        """Update the current view with the result of calling `undo` or `redo`.

        Args:
            command (str): 'undo', 'redo', or 'redo_or_repeat'.
            in_vis (bool): `True` if we were called from `sublundo_next_node`.
        """
        t = util.VIEW_TO_TREE[self.view.id()]['tree']
        pos = 0
        if command == 'undo':
            buf, diff, pos = t.undo()
        else:
            buf, diff, pos = t.redo()

        self.view.replace(edit, sublime.Region(0, self.view.size()), buf)

        # Re-position the cursor.
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pos))
        self.view.show(pos)

        p = sublime.active_window().find_output_panel('sublundo')
        if all([p, diff, in_vis]):
            p.replace(edit, sublime.Region(0, p.size()), diff)
            self.view.add_regions(
                'sublundo',
                [self.view.full_line(pos)],
                'invalid',
                '',
                sublime.DRAW_NO_FILL)


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
            t, loaded = util.load_session(loc, buf)
            if loaded:
                util.debug('Loaded session for {0}.'.format(name))
            else:
                util.debug('Failed to load session for {0}.'.format(name))
                t.insert(buf, view.sel()[0].a)
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
        w.destroy_output_panel('output.sublundo')
        for v in w.views():
            v.erase_regions('sublundo')

    def on_pre_close(self, view):
        """Save the current session.
        """
        if util.get_setting('persist') and util.check_view(view):
            info = util.VIEW_TO_TREE[view.id()]
            util.save_session(info['tree'], info['loc'])

    def on_text_command(self, view, command_name, args):
        """Run `sublundo` instead of the built-in `undo` and `redo` commands.
        """
        triggers = ('undo', 'redo_or_repeat', 'redo')
        if util.check_view(view) and command_name in triggers:
            return ('sublundo', {'command': command_name})
        return None

    def on_post_text_command(self, view, command_name, args):
        """Update the tree.

        We only update the tree if `view.change_count()` has been incremented
        since we last checked. TODO: should this be a setting?
        """
        if command_name != 'sublundo' and view.id() in util.CHANGE_INDEX:
            if util.CHANGE_INDEX[view.id()] != view.change_count():
                util.VIEW_TO_TREE[view.id()]['tree'].insert(
                    util.buffer(view),
                    view.sel()[0].a
                )
                util.CHANGE_INDEX[view.id()] = view.change_count()


def plugin_loaded():
    """Ensure that our session storage location exists.
    """
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    if not os.path.exists(history):
        os.makedirs(history)


def plugin_unloaded():
    """Clean up *.sublundo-session files.
    """
    d = util.get_setting('delete_after_n_days', 5)
    days_ago = datetime.now() - timedelta(days=d)
    history = os.path.join(sublime.packages_path(), 'User', 'Sublundo')
    for session in os.listdir(history):
        if session.endswith('.sublundo-session'):
            p = os.path.join(history, session)
            modified = datetime.fromtimestamp(os.path.getmtime(p))
            if modified > days_ago:
                os.remove(p)
