import os
import unittest

from lib.tree import (
    UndoTree,
    load_session,
    save_session
)


def new_tree(name):
    if os.path.exists(name):
        os.remove(name)
    return UndoTree()


class UndoTreeTestCase(unittest.TestCase):
    """Tests for navigation and serialization of UndoTree.
    """
    def test_navigate_linear(self):
        t = new_tree('test.libundo-session')
        # Initial state -- one addition ('1'):
        #
        #             1 (@)
        t.insert('My name is Joe.')
        self.assertEqual(t.text(), 'My name is Joe.')
        self.assertEqual(t.head().idx, 1)

        # Second state --  another addition ('2'):
        #
        #             1
        #              \
        #               2 (@)
        t.insert('My name is actually Bob.')
        self.assertEqual(t.text(), 'My name is actually Bob.')
        self.assertEqual(t.head().idx, 2)

        # Third state -- back to 'A':
        #
        #             1 (@)
        #              \
        #               2
        self.assertEqual(t.undo()[0], 'My name is Joe.')
        self.assertEqual(t.head().idx, 1)

        # Fourth state -- back to 'B':
        #
        #             1
        #              \
        #               2 (@)
        self.assertEqual(t.redo()[0], 'My name is actually Bob.')
        self.assertEqual(t.head().idx, 2)

    def test_navigate_branch(self):
        t = new_tree('test.libundo-session')
        # Initial state -- one addition ('1'):
        #            1 (@)
        t.insert('My name is Joe.')
        self.assertEqual(t.text(), 'My name is Joe.')
        self.assertEqual(t.head().idx, 1)

        # Second state --  two more additions ('2' & '3'):
        #
        #            1
        #           / \
        #      (@) 3   2
        t.insert('My name is actually Bob.')
        self.assertEqual(t.text(), 'My name is actually Bob.')
        self.assertEqual(t.head().idx, 2)
        self.assertEqual(t.head().parent.idx, 1)

        self.assertEqual(t.undo()[0], 'My name is Joe.')

        t.insert('My name is Bob.')
        self.assertEqual(t.text(), 'My name is Bob.')
        self.assertEqual(t.head().idx, 3)
        self.assertEqual(t.head().parent.idx, 1)

        # Third state --  back to '2':
        #
        #             1
        #            / \
        #           3   2 (@)
        self.assertEqual(t.undo()[0], 'My name is Joe.')
        self.assertEqual(t.head().idx, 1)

        self.assertEqual(t.redo()[0], 'My name is actually Bob.')
        self.assertEqual(t.head().idx, 2)

        # Fourth state --  back to '3':
        #
        #            1
        #           / \
        #      (@) 3   2
        self.assertEqual(t.undo()[0], 'My name is Joe.')

        t.switch_branch(1)

        self.assertEqual(t.redo()[0], 'My name is Bob.')

    def test_serialize_valid(self):
        t = new_tree('test.sublundo-session')

        t.insert('Hello from libundo (C++)!')
        self.assertEqual(len(t), 1)
        save_session(t, 'test.sublundo-session')

        t2 = load_session('test.sublundo-session', 'Hello from libundo (C++)!')
        self.assertEqual(len(t2[0]), 1)
        self.assertEqual(t2[1], True)

    def test_serialize_invalid(self):
        t = new_tree('test.sublundo-session')

        t.insert('Hello from libundo (C++)!')
        self.assertEqual(len(t), 1)
        save_session(t, 'test.sublundo-session')

        t2 = load_session('test.sublundo-session', 'Hello from libundo!')
        self.assertEqual(len(t2[0]), 0)
        self.assertEqual(t2[1], False)


if __name__ == '__main__':
    unittest.main()
