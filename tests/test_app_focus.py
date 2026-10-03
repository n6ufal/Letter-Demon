"""Tests for ui/app.py focus handling.

The app pulls focus into the prefix entry when the window is re-activated, but
must never steal focus from a control the user just clicked (that broke the
ttk.Combobox drop-downs under Tk 9).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.app import LetterDemonApp


class _FakeView:
    def __init__(self, entry):
        self.entry = entry


class _FakeApp:
    def __init__(self, root, entry):
        self.root = root
        self.view = _FakeView(entry)


class FocusStealTest(unittest.TestCase):
    """_maybe_focus_prefix_entry must only fire when nothing is focused."""

    @classmethod
    def setUpClass(cls):
        import tkinter as tk

        try:
            cls.root = tk.Tk()
        except tk.TclError:
            cls.root = None
            raise unittest.SkipTest("no display available for tkinter")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        if cls.root is not None:
            cls.root.destroy()

    def setUp(self):
        import tkinter as tk

        self.root = self.__class__.root
        self.frame = tk.Frame(self.root)
        self.frame.pack()
        self.entry = tk.Entry(self.frame)
        self.entry.pack()
        self.combo = tk.ttk.Combobox(self.frame, values=["a", "b"], state="readonly")
        self.combo.pack()
        self.app = _FakeApp(self.root, self.entry)
        self.root.deiconify()
        self.root.update()

    def tearDown(self):
        self.frame.destroy()
        self.root.withdraw()

    def _run(self):
        LetterDemonApp._maybe_focus_prefix_entry(self.app)
        self.root.update()

    def test_does_not_steal_focus_from_combobox(self):
        self.combo.focus_force()
        self.root.update()
        self._run()
        self.assertIs(self.root.focus_get(), self.combo)

    def test_does_not_steal_focus_from_entry(self):
        self.entry.focus_force()
        self.root.update()
        self._run()
        self.assertIs(self.root.focus_get(), self.entry)

    def test_grabs_focus_when_toplevel_focused(self):
        self.root.tk.call("focus", self.root.winfo_toplevel())
        self.root.update()
        self._run()
        self.assertIs(self.root.focus_get(), self.entry)

    def test_combobox_dropdown_opens_on_click(self):
        self.combo.focus_force()
        self.root.update()
        self.combo.event_generate(
            "<Button-1>", x=self.combo.winfo_width() - 5, y=self.combo.winfo_height() // 2
        )
        self.root.update()
        popdown = str(self.combo.tk.call("ttk::combobox::PopdownWindow", self.combo._w))
        self.assertEqual(1, self.root.tk.call("winfo", "ismapped", popdown))
