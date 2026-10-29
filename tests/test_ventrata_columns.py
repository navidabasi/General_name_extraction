"""Tests for the Ventrata column mapping shared with Crown Report."""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_loader  # noqa: E402
from utils import ventrata_columns  # noqa: E402

# ventrata.input_columns as published on the Worker (revision 2026-10-29.1).
MAPPING = {
    'Reseller': 'Booking Order Reseller Name',
    'Order Reference': 'Booking Order Reference',
    'Unit': 'Unit Label',
    'Public Notes': 'Booking Public Notes',
    'Private Notes': 'Booking Private Notes',
    'Travel Date': 'Date',
    'Product Code': 'Booking Product Code',
    'Customer Country': 'Booking Order Customer Country',
    'Ticket Customer First Name': 'Customer First Name',
    'Ticket Customer Last Name': 'Customer Last Name',
    'Tour Time': 'Booking Tour Time',
    'Customer': 'Booking Order Customer',
    'Booking Type': 'Booking Booking Type',
    'Product': 'Product Internal Name',
    'Product Tags': 'All Tags',
    'Booking Date': 'Created At Date',
}

# Headers as Ventrata exports them since October 2026.
NEW_EXPORT_ROW = {
    'Booking Reference': 'QNQ51ZAS',
    'Booking Order Reference': 'G33B3C32',
    'Booking Order Customer': 'CHARLTON, David',
    'Status': 'Confirmed',
    'Product Internal Name': "Rome: Castel Sant'Angelo Skip-the-Line Tickets with Audio Guide",
    'Date': '2026-10-29',
    'Created At Date': '2026-10-29',
    'Unit Label': 'Adult',
    'Customer First Name': 'David',
    'Customer Last Name': 'Charlton',
    'Booking Order Reseller Name': 'Viator',
    'Booking Public Notes': '',
    'Booking Private Notes': '(TIX NOM 13:30)',
    'All Tags': "Castel Sant'Angelo",
    'Booking Product Code': 'ROMSANAUGMTL',
    'Booking Order Customer Country': 'GB',
    'Booking Tour Time': '13:30:00',
    'Booking Booking Type': 'Standalone',
    'ID': '01a186d0-8742-72c7-98f9-958126ab6952',
}

# The same booking in the layout used before October 2026.
OLD_EXPORT_ROW = {
    'Booking Reference': 'QNQ51ZAS',
    'Order Reference': 'G33B3C32',
    'Customer': 'CHARLTON, David',
    'STATUS': 'Confirmed',
    'Product': "Rome: Castel Sant'Angelo Skip-the-Line Tickets with Audio Guide",
    'Travel Date': '2026-10-29',
    'UNIT': 'Adult',
    'Ticket Customer First Name': 'David',
    'Ticket Customer Last Name': 'Charlton',
    'Reseller': 'Viator',
    'Public Notes': '',
    'Private Notes': '(TIX NOM 13:30)',
    'Product Code': 'ROMSANAUGMTL',
    'Customer Country': 'GB',
    'Tour Time': '13:30:00',
    'ID': '01a186d0-8742-72c7-98f9-958126ab6952',
}

RULES_YAML = "version: 1\nrevision: 'test.1'\nventrata:\n  input_columns:\n" + "".join(
    f"    '{internal}': '{export}'\n" for internal, export in MAPPING.items()
)


class RenameTest(unittest.TestCase):
    def test_new_headers_become_the_internal_names(self):
        df = ventrata_columns.rename_ventrata_columns(pd.DataFrame([NEW_EXPORT_ROW]), MAPPING)
        for internal_name in MAPPING:
            self.assertIn(internal_name, df.columns)
        self.assertEqual(df.loc[0, 'Order Reference'], 'G33B3C32')
        self.assertEqual(df.loc[0, 'Unit'], 'Adult')
        self.assertEqual(df.loc[0, 'Travel Date'], '2026-10-29')
        # Columns Ventrata did not rename are kept.
        self.assertEqual(df.loc[0, 'ID'], NEW_EXPORT_ROW['ID'])

    def test_old_headers_are_left_alone(self):
        df = ventrata_columns.rename_ventrata_columns(pd.DataFrame([OLD_EXPORT_ROW]), MAPPING)
        self.assertEqual(list(df.columns), list(OLD_EXPORT_ROW))

    def test_export_names_match_case_insensitively(self):
        df = pd.DataFrame([{'UNIT LABEL': 'Child'}])
        self.assertEqual(list(ventrata_columns.rename_ventrata_columns(df, MAPPING).columns), ['Unit'])

    def test_an_existing_internal_column_is_not_duplicated(self):
        df = pd.DataFrame([{'Date': '2026-10-29', 'Travel Date': '2026-10-30'}])
        renamed = ventrata_columns.rename_ventrata_columns(df, MAPPING)
        self.assertEqual(list(renamed.columns), ['Date', 'Travel Date'])
        self.assertEqual(renamed.loc[0, 'Travel Date'], '2026-10-30')


class MappingSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(ventrata_columns, 'CACHE_PATH', os.path.join(self.tmp.name, 'cache.json'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _response(self, text):
        response = mock.Mock(text=text)
        response.raise_for_status.return_value = None
        return response

    def test_cloud_mapping_is_used_and_cached(self):
        with mock.patch.object(ventrata_columns.requests, 'get', return_value=self._response(RULES_YAML)):
            self.assertEqual(ventrata_columns.get_ventrata_input_columns(), MAPPING)
        self.assertEqual(ventrata_columns.get_ventrata_columns_source(), ('cloud', 'test.1'))
        with open(ventrata_columns.CACHE_PATH, encoding='utf-8') as handle:
            self.assertEqual(json.load(handle)['input_columns'], MAPPING)

    def test_cache_is_used_when_the_worker_is_unreachable(self):
        with open(ventrata_columns.CACHE_PATH, 'w', encoding='utf-8') as handle:
            json.dump({'revision': 'test.0', 'input_columns': MAPPING}, handle)
        with mock.patch.object(ventrata_columns.requests, 'get', side_effect=OSError('offline')):
            self.assertEqual(ventrata_columns.get_ventrata_input_columns(), MAPPING)
        self.assertEqual(ventrata_columns.get_ventrata_columns_source(), ('cached', 'test.0'))

    def test_an_invalid_download_falls_back_to_the_cache(self):
        with open(ventrata_columns.CACHE_PATH, 'w', encoding='utf-8') as handle:
            json.dump({'revision': 'test.0', 'input_columns': MAPPING}, handle)
        broken = "ventrata:\n  input_columns:\n    Reseller: 'Booking Order Reseller Name'\n"
        with mock.patch.object(ventrata_columns.requests, 'get', return_value=self._response(broken)):
            self.assertEqual(ventrata_columns.get_ventrata_input_columns(), MAPPING)
        self.assertEqual(ventrata_columns.get_ventrata_columns_source()[0], 'cached')

    def test_no_mapping_without_download_or_cache(self):
        with mock.patch.object(ventrata_columns.requests, 'get', side_effect=OSError('offline')):
            self.assertEqual(ventrata_columns.get_ventrata_input_columns(), {})
        self.assertEqual(ventrata_columns.get_ventrata_columns_source(), ('none', ''))


class LoadVentrataTest(unittest.TestCase):
    def _write(self, row):
        handle = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        pd.DataFrame([row]).to_excel(handle.name, index=False)
        return handle.name

    def test_new_layout_loads_with_the_shared_mapping(self):
        path = self._write(NEW_EXPORT_ROW)
        with mock.patch.object(data_loader, 'get_ventrata_input_columns', return_value=MAPPING):
            df = data_loader.load_ventrata(path)
        self.assertEqual(df.loc[0, 'Ticket Customer First Name'], 'David')
        self.assertEqual(df.loc[0, '_normalized_order_ref'], 'g33b3c32')
        self.assertEqual(data_loader.get_ventrata_column_map(df)['tour_time'], 'Tour Time')

    def test_old_layout_still_loads(self):
        path = self._write(OLD_EXPORT_ROW)
        with mock.patch.object(data_loader, 'get_ventrata_input_columns', return_value=MAPPING):
            df = data_loader.load_ventrata(path)
        self.assertEqual(df.loc[0, 'Order Reference'], 'G33B3C32')

    def test_new_layout_without_any_mapping_explains_what_to_do(self):
        path = self._write(NEW_EXPORT_ROW)
        with mock.patch.object(ventrata_columns.requests, 'get', side_effect=OSError('offline')), \
                mock.patch.object(ventrata_columns, 'CACHE_PATH', os.path.join(tempfile.gettempdir(), 'missing-ne.json')):
            with self.assertRaisesRegex(ValueError, 'could not be downloaded'):
                data_loader.load_ventrata(path)


if __name__ == '__main__':
    unittest.main()
