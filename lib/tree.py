"""tree.py

This module contains the implementation of a simple N-ary tree, with each node
containing a patch that takes us from one buffer state to another.
"""
import pickle
import os
import collections
import hashlib

from datetime import datetime
from .diff_match_patch import diff_match_patch


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
    new = hashlib.md5(buf.encode()).hexdigest()
    if os.path.exists(path):
        try:
            with open(path, 'rb') as loc:
                canidate = pickle.load(loc)
                old = hashlib.md5(canidate.text().encode()).hexdigest()
            if old == new:
                return canidate, True
        except EOFError:
            pass
    return UndoTree(), False


class Node:
    """A Node represents a single buffer state.
    """
    def __init__(self, idx, parent, timestamp, pos=None):
        self.idx = idx  # The node's unique index.
        self.parent = parent
        self.timestamp = timestamp
        self.children = []
        self.patches = {}
        self.position = pos # The node's buffer position.


class UndoTree:
    """An N-ary tree representing a text buffer's history.
    """
    def __init__(self):
        self._root = None
        self._total = 0
        self._n_idx = 0
        self._b_idx = 0
        self._buf = None
        self._undo_file = None
        self._dmp = diff_match_patch()
        self._index = collections.OrderedDict()

    def __len__(self):
        return self._total

    def insert(self, buf, pos=None):
        """Insert the given buffer and (optional) position into the tree.

        Args:
            buf (str): The contents to be inserted.
            pos (None|int): An optional integer representing a buffer position.
        """
        self._total = self._total + 1
        tm = datetime.now().strftime('%d-%m-%Y %H-%M-%S')
        to_add = Node(self._total, None, tm, pos)
        if self._root is None:
            self._root = to_add
        else:
            parent = self._find_parent()
            patches = self._patch(self._buf, buf)

            to_add.parent = parent
            to_add.patches[parent.idx] = patches[1]

            parent.children.append(to_add)
            parent.patches[self._total] = patches[0]

        self._n_idx = to_add.idx
        self._buf = buf
        self._index[self._total] = to_add

    def undo(self):
        """Move backward one node, if possible.
        """
        diff = None
        pos = None
        parent = self.head().parent
        if parent is not None:
            self._buf, diff = self._apply_patch(parent.idx)
            pos = parent.position
        return self._buf, diff, pos

    def redo(self):
        """Move forward one node, if possible.
        """
        diff = None
        pos = None
        n = self.head()
        if len(n.children) > 0:
            target = n.children[self._b_idx]
            self._buf, diff = self._apply_patch(target.idx)
            pos = target.position
        return self._buf, diff, pos

    def branch(self):
        """Return the active branch index.
        """
        return self._b_idx

    def text(self):
        """Return the active node's buffer.
        """
        return self._buf

    def nodes(self):
        """Return all nodes in the tree ordered by inserted time.
        """
        return list(self._index.values())

    def head(self):
        """Return the current node in the tree.
        """
        return self._search(self._n_idx)

    def switch_branch(self, direction):
        """Switch to the next branch in `direction`.
        """
        if direction and self._b_idx + 1 < len(self.head().children):
            self._b_idx = self._b_idx + 1
        elif not direction and self._b_idx - 1 >= 0:
            self._b_idx = self._b_idx - 1
        else:
            upper = len(self.head().children) - 1
            if not direction and upper > 0:
                self._b_idx = upper
            else:
                self._b_idx = 0

    def _search(self, idx):
        """Search for the node with an index of `idx`.
        """
        return self._index.get(idx, None)

    def _find_parent(self):
        """Find the current parent node.
        """
        maybe = self.head()
        if maybe.parent is not None and self._b_idx in maybe.parent.children:
            return maybe.parent.children[self._b_idx]
        else:
            return maybe

    def _patch(self, s1, s2):
        """Create patches for `s1` -> `s2` and `s2` -> `s1`.
        """
        d1 = self._dmp.diff_main(s1, s2)
        p1 = self._dmp.patch_make(s1, d1)

        # Instead of diffing twice, we just flip the first.
        for i in range(len(d1)):
            le = list(d1[i])
            le[0] = le[0] * -1
            d1[i] = le

        p2 = self._dmp.patch_make(s2, d1)
        return [p1, p2]

    def _apply_patch(self, idx):
        """Apply the node's patch given by `idx`.

        Returns:
            (str, str): The resulting text and the patch itself.
        """
        patch = self.head().patches[idx]
        out = self._dmp.patch_apply(patch, self._buf)
        self._n_idx = idx
        text = self._dmp.patch_toText(patch)
        return out[0], text
