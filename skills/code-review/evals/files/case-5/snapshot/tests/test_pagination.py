import unittest

from app import pagination


class TotalPagesTests(unittest.TestCase):
    def test_empty_set_has_no_pages(self):
        self.assertEqual(pagination.total_pages(0, 10), 0)

    def test_exact_multiple(self):
        self.assertEqual(pagination.total_pages(20, 10), 2)

    def test_partial_last_page(self):
        self.assertEqual(pagination.total_pages(21, 10), 3)

    def test_rejects_non_positive_size(self):
        with self.assertRaises(ValueError):
            pagination.total_pages(10, 0)


class PageSliceTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(pagination.page_slice([], 1, 10), [])

    def test_single_page_fits_everything(self):
        rows = ["a", "b", "c"]
        self.assertEqual(pagination.page_slice(rows, 1, 10), rows)

    def test_returns_a_list(self):
        self.assertIsInstance(pagination.page_slice(("a", "b"), 1, 10), list)


class PageMetaTests(unittest.TestCase):
    def test_meta_reports_totals(self):
        meta = pagination.page_meta(total=5, page=2, size=2)
        self.assertEqual(meta["page"], 2)
        self.assertEqual(meta["size"], 2)
        self.assertEqual(meta["total_records"], 5)
        self.assertEqual(meta["total_pages"], 3)
