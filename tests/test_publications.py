import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publications", ROOT / "scripts/publications.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

# Actual JaLC CSL response for this publication, retrieved 2026-11-26.
CSL = {
    "DOI": "10.14988/0002001265", "language": "ja",
    "title": "欧州政治におけるGAL–TAN対立軸研究の展開と展望 : 政党間競争の視角から",
    "author": [{"given": "直志", "family": "伊﨑"}],
    "publisher": "同志社大学政策学会", "issued": {"date-parts": [[2025, 8, 1]]},
    "volume": "27", "number": "1", "page": "39-49", "container-title": "同志社政策科学研究",
}
# Relevant fields from the NDL SRU response (ISBN 9784560093580), 2026-11-26.
NDL = '''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcndl="http://ndl.go.jp/dcndl/terms/" xmlns:foaf="http://xmlns.com/foaf/0.1/">
 <dcndl:BibResource rdf:about="https://ndlsearch.ndl.go.jp/books/R100000002-I032891161#material">
  <dcterms:identifier rdf:datatype="http://ndl.go.jp/dcndl/terms/ISBN">978-4-560-09358-0</dcterms:identifier>
  <dcterms:title>民主主義の危機 : 比較分析が示す変容</dcterms:title>
  <dc:creator>アダム・プシェヴォスキ 著</dc:creator><dc:creator>吉田徹, 伊﨑直志 訳</dc:creator>
  <dcterms:publisher><foaf:Agent><foaf:name>白水社</foaf:name></foaf:Agent></dcterms:publisher>
  <dcterms:issued>2023</dcterms:issued>
 </dcndl:BibResource>
</rdf:RDF>'''


class PublicationsTest(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((ROOT / "tests/fixtures/publications.json").read_text())

    def test_exact_user_citations(self):
        self.assertEqual(p.citation(self.records[0]), '伊﨑直志（2026）「イギリス労働党における『危機』言説の展開（1975–1984年）」『同志社政策科学研究』28（1）、47–58。')
        self.assertEqual(p.citation(self.records[2]), 'プシェヴォスキ, A.、吉田徹・伊﨑直志（訳）（2023）『民主主義の危機―比較分析が示す変容』白水社。')

    def test_jalc_number_and_author(self):
        record = p.from_csl(CSL, '10.14988/0002001265')
        self.assertEqual(record['authors'], ['伊﨑直志'])
        self.assertEqual(p.citation(record), '伊﨑直志（2025）「欧州政治におけるGAL–TAN対立軸研究の展開と展望―政党間競争の視角から」『同志社政策科学研究』27（1）、39–49。')

    def test_ndl_translator_roles(self):
        record = p.from_ndl(NDL, '9784560093580')
        self.assertEqual(record['authors'], ['プシェヴォスキ, A.'])
        self.assertEqual(record['translators'], ['吉田徹', '伊﨑直志'])
        self.assertEqual(p.citation(record), p.citation(self.records[2]))

    def test_identifiers(self):
        for raw in ['978-4-560-09358-0', 'ISBN: 9784560093580', 'ISBN-10: 4-560-09358-X', '９７８４５６００９３５８０']:
            self.assertEqual(p.normalize_identifier(raw), ('isbn', '9784560093580'))
        self.assertEqual(p.normalize_identifier('https://doi.org/10.14988%2F0002001265'), ('doi', '10.14988/0002001265'))
        for raw in ['9784560093581', '4560093580', 'https://example.com', '10.1234/with space']:
            with self.assertRaises(ValueError):
                p.normalize_identifier(raw)

    def test_missing_roles_are_not_guessed(self):
        with self.assertRaises(ValueError):
            p.from_ndl(NDL.replace(' 訳</dc:creator>', '</dc:creator>'), '9784560093580')
        unknown = [{'summary': {'isbn': '9784560093580'}, 'onix': {'DescriptiveDetail': {
            'Contributor': [{'PersonName': {'content': '吉田, 徹, 1975-'}, 'ContributorRole': []}]}}}]
        with self.assertRaises(ValueError):
            p.from_openbd(unknown, '9784560093580')

    def test_wrong_record_and_missing_year_fail(self):
        with self.assertRaises(ValueError):
            p.from_csl(CSL, '10.14988/wrong')
        missing = copy.deepcopy(CSL)
        del missing['issued']
        with self.assertRaises(ValueError):
            p.from_csl(missing, CSL['DOI'])
        with self.assertRaises(ValueError):
            p.from_ndl(NDL.replace('978-4-560-09358-0', '0000000000000'), '9784560093580')

    def test_optional_pages_are_not_invented(self):
        record = p.from_csl({k: v for k, v in CSL.items() if k not in ('page', 'volume', 'number')}, CSL['DOI'])
        self.assertTrue(p.citation(record).endswith('『同志社政策科学研究』。'))

    def test_render_escapes_content(self):
        record = copy.deepcopy(self.records[0])
        record['title'] = '<script>alert("test")</script>'
        output = p.render(p.prepare([record]))
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)

    def test_build_is_deterministic_and_invalid_input_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name in ['index.html', 'publications.json']:
                (directory / name).write_bytes((ROOT / 'docs' / name).read_bytes())
            p.build(self.records, directory)
            before = {x.name: x.read_bytes() for x in directory.iterdir()}
            p.build(self.records, directory, check=True)
            invalid = copy.deepcopy(self.records)
            invalid[0]['authors'] = []
            with self.assertRaises(ValueError):
                p.build(invalid, directory)
            self.assertEqual(before, {x.name: x.read_bytes() for x in directory.iterdir()})

    def test_duplicate_does_not_refetch_or_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'publications.json').write_text(json.dumps(self.records, ensure_ascii=False))
            before = (directory / 'publications.json').read_bytes()
            with patch.object(p, 'lookup') as lookup, patch('sys.argv', [
                'publications.py', 'add', '4-560-09358-X', '--directory', temp
            ]):
                p.main()
                lookup.assert_not_called()
            self.assertEqual(before, (directory / 'publications.json').read_bytes())

    def test_add_persists_to_data_and_html(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'index.html').write_bytes((ROOT / 'docs/index.html').read_bytes())
            (directory / 'publications.json').write_text(json.dumps(self.records[:2], ensure_ascii=False))
            with patch.object(p, 'lookup', return_value=p.from_ndl(NDL, '9784560093580')), patch('sys.argv', [
                'publications.py', 'add', '9784560093580', '--directory', temp
            ]):
                p.main()
            data = json.loads((directory / 'publications.json').read_text())
            self.assertEqual(len(data), 3)
            self.assertIn(data[2]['citation'], (directory / 'index.html').read_text())


if __name__ == '__main__':
    unittest.main()
