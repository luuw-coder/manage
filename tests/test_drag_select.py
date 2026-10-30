import unittest

from app.grid_select import press_selection, release_selection


class GridSelectTests(unittest.TestCase):
    def test_user_click_sequence(self):
        sel, anc = press_selection(set(), 0, -1, False, False)
        self.assertEqual(sel, {0})
        sel, anc = press_selection(sel, 1, anc, False, False)
        self.assertEqual(sel, {1})
        sel, anc = press_selection(sel, 2, anc, True, False)  # Ctrl: thêm
        self.assertEqual(sel, {1, 2})
        sel, anc = press_selection(sel, 0, anc, False, False)  # nhấn thường thẻ ngoài nhóm
        self.assertEqual(sel, {0})

    def test_ctrl_toggles_off(self):
        sel, _ = press_selection({0, 1}, 1, 1, True, False)
        self.assertEqual(sel, {0})

    def test_shift_selects_range_from_anchor(self):
        sel, anc = press_selection({2}, 4, 2, False, True)
        self.assertEqual(sel, {2, 3, 4})
        self.assertEqual(anc, 2)
        sel, _ = press_selection({4}, 1, 4, False, True)
        self.assertEqual(sel, {1, 2, 3, 4})

    def test_press_on_selected_group_keeps_group_for_drag(self):
        sel, anc = press_selection({0, 1, 2}, 1, 0, False, False)
        self.assertEqual(sel, {0, 1, 2})
        self.assertEqual(anc, 1)

    def test_release_without_drag_collapses_group(self):
        self.assertEqual(release_selection({0, 1, 2}, 1, 1, False, False), {1})
        self.assertEqual(release_selection({0, 1, 2}, 1, 0, False, False), {0, 1, 2})
        self.assertEqual(release_selection({0, 1}, 1, 1, True, False), {0, 1})


if __name__ == "__main__":
    unittest.main()
