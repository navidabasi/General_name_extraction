"""Cloud lifecycle and extraction regressions, with no external network calls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

from utils import extraction_rules as rules
from utils.extraction_defaults import default_rules
from extractors.gyg_standard import GYGStandardExtractor
from extractors.gyg_mda import GYGMDAExtractor
from utils.reseller_dob_extractors import _extract_gyg_standard_dobs, _extract_viator_dobs
from utils.age_calculator import categorize_age
from utils.normalization import extract_language_from_product_code
from tests.test_ventrata_columns import MAPPING, NEW_EXPORT_ROW, OLD_EXPORT_ROW
from data_loader import load_ventrata
from processor import NameExtractionProcessor


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.document = default_rules()
        self.document['revision'] = 'test.1'
        for name, value in [('_active', default_rules()), ('_source', 'bundled'),
                            ('CACHE_PATH', os.path.join(self.tmp.name, 'rules.json'))]:
            p = patch.object(rules, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.network = patch.object(rules.requests, 'get', side_effect=requests.ConnectionError('offline'))
        self.get = self.network.start()
        self.addCleanup(self.network.stop)

    def download(self, document=None):
        self.get.side_effect = None
        self.get.return_value = Mock(json=Mock(return_value=document or self.document))
        return rules.refresh_extraction_rules()

    def test_deployment_document_is_valid(self):
        path = Path(__file__).resolve().parents[1] / 'cloudflare-worker/src/extraction_rules.json'
        published = rules.validate_rules(json.loads(path.read_text()))
        self.assertEqual(published['version'], 1)

    def test_online_then_offline_uses_validated_cache(self):
        self.assertEqual(self.download()[1], 'cloud')
        self.get.side_effect = requests.Timeout('offline')
        self.assertEqual(rules.refresh_extraction_rules()[1], 'cached')
        self.assertEqual(rules.get_extraction_rules_source(), ('cached', 'test.1'))

    def test_invalid_update_does_not_replace_good_cache(self):
        self.download()
        before = Path(rules.CACHE_PATH).read_bytes()
        bad = copy.deepcopy(self.document)
        bad['patterns']['gyg_name']['regex'] = '['
        self.assertEqual(self.download(bad)[1], 'cached')
        self.assertEqual(Path(rules.CACHE_PATH).read_bytes(), before)

    def test_cold_offline_start_uses_original_rules(self):
        self.assertEqual(rules.refresh_extraction_rules()[1], 'bundled')
        self.assertEqual(GYGStandardExtractor()._extract_names('First Name: Jane\nLast Name: Smith'), ['Jane Smith'])

    def test_corrupt_cache_is_ignored(self):
        Path(rules.CACHE_PATH).write_text('[]')
        self.assertEqual(rules.refresh_extraction_rules()[1], 'bundled')

    def test_cache_write_failure_still_uses_download_and_keeps_it_in_memory(self):
        with patch.object(rules, 'write_json_cache', side_effect=OSError('read only')):
            self.assertEqual(self.download()[1], 'cloud')
        self.get.side_effect = requests.Timeout('offline')
        self.assertEqual(rules.refresh_extraction_rules()[0]['revision'], 'test.1')

    def test_bad_schema_flags_groups_and_settings_rejected(self):
        edits = [
            lambda d: d.update(version=2),
            lambda d: d.update(revision=''),
            lambda d: d['patterns']['gyg_name'].update(regex='(only one)', groups=1),
            lambda d: d['patterns']['gyg_name'].update(flags=128),
            lambda d: d['settings'].update(AGE_CHILD_MAX='18'),
            lambda d: d['settings'].update(AGE_CHILD_MAX=100),
            lambda d: d['settings'].update(EU_COUNTRIES=[42]),
            lambda d: d['settings'].update(UNKNOWN=True),
            lambda d: d['mda_patterns'].pop('PATTERN_TRAVELER'),
        ]
        for edit in edits:
            with self.subTest(edit=edit):
                bad = copy.deepcopy(self.document)
                edit(bad)
                with self.assertRaises(ValueError):
                    rules.validate_rules(bad)

    def test_cloud_name_and_dob_labels_take_effect_without_restart(self):
        extractor = GYGStandardExtractor()
        self.document['patterns']['gyg_name']['regex'] = r'Given:\s*([^\n:]+)\s*Family:\s*([^\n:]+)'
        self.document['patterns']['gyg_dob_slash']['regex'] = r'Born:\s*(\d{2}/\d{2}/\d{4})'
        self.download()
        self.assertEqual(extractor._extract_names('Given: Alice\nFamily: Brown'), ['Alice Brown'])
        self.assertEqual(_extract_gyg_standard_dobs('Born: 01/02/1990'), ['01/02/1990'])

    def test_cloud_mda_pattern_takes_effect(self):
        self.document['mda_patterns']['PATTERN_NAME_PAREN_DATE']['regex'] = r'([A-Za-z ]+)\s*\[(\d{1,2}/\d{1,2}/\d{4})\]'
        self.download()
        travelers = GYGMDAExtractor().extract_travelers('Alice Brown [01/02/1990]', 'TEST', {'travel_date': '2026-11-14'})
        self.assertEqual(travelers[0]['name'], 'Alice Brown')

    def test_cloud_settings_used_by_already_imported_consumers(self):
        self.document['settings']['LANGUAGE_MAP']['XYZ'] = 'Test language'
        self.document['settings']['AGE_CHILD_MAX'] = 16
        self.document['settings']['AGE_YOUTH_MIN'] = 16
        self.document['settings']['GYG_STANDARD_PLATFORMS'].append('New reseller')
        self.download()
        self.assertEqual(extract_language_from_product_code('ROMXYZ'), 'Test language')
        self.assertEqual(categorize_age(17), 'Youth')
        self.assertIn('New reseller', GYGStandardExtractor().get_reseller_types())
        self.assertIn('New reseller', rules.get_setting('ALL_GYG_PLATFORMS'))
        processor = object.__new__(NameExtractionProcessor)
        self.assertEqual(processor._identify_extractor_type('New reseller'), 'gyg_standard')
        self.assertEqual(processor._identify_extractor_type('Get your Guide Future'), 'gyg_standard')

    def test_existing_gyg_and_viator_dob_formats(self):
        self.assertEqual(_extract_gyg_standard_dobs('Date of Birth: 01/02/1990'), ['01/02/1990'])
        self.assertEqual(_extract_gyg_standard_dobs('Date of Birth: 1990-02-01'), ['1990-02-01'])
        self.assertEqual(_extract_viator_dobs('Q:Date of Birth\nA:01/02/1990, 10/03/2000'), ['01/02/1990', '10/03/2000'])

    def test_existing_mda_formats(self):
        for notes in ['Alice Brown (01/02/1990)', 'Alice Brown (1990.02.01)',
                      'Traveler 1:\nFirst Name: Alice\nLast Name: Brown\nDate of Birth: 1990-02-01']:
            with self.subTest(notes=notes):
                travelers = GYGMDAExtractor().extract_travelers(notes, 'TEST', {'travel_date': '2026-11-14'})
                self.assertEqual(travelers[0]['name'], 'Alice Brown')

    def test_old_and_new_xlsx_produce_same_name(self):
        for row in [OLD_EXPORT_ROW, NEW_EXPORT_ROW]:
            with self.subTest(layout=list(row)):
                path = os.path.join(self.tmp.name, 'input.xlsx')
                pd.DataFrame([row]).to_excel(path, index=False)
                with patch('data_loader.get_ventrata_input_columns', return_value=MAPPING):
                    df = load_ventrata(path)
                result = NameExtractionProcessor(df).process()
                self.assertEqual(len(result), 1)
                self.assertEqual(result.iloc[0]['Full Name'], 'David Charlton')

    def test_atomic_cache_failure_preserves_original(self):
        rules.write_json_cache(rules.CACHE_PATH, {'old': True})
        with patch.object(rules.os, 'replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                rules.write_json_cache(rules.CACHE_PATH, {'new': True})
        self.assertEqual(json.loads(Path(rules.CACHE_PATH).read_text()), {'old': True})
        self.assertEqual(os.listdir(self.tmp.name), ['rules.json'])


if __name__ == '__main__':
    unittest.main()
