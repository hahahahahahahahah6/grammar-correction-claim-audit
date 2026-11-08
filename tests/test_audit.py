EXPECTED_GRAMMARCORRECTION = ['grammar correction', 'grammar-correction', 'grammarcorrection', 'grammar correction model', 'grammar correction models', 'grammar correction system', 'grammar correction systems', 'grammar correction feature', 'grammar correction capability', 'grammar correction support', 'supports grammar correction', 'grammar correction tool', 'grammar correction api', 'grammar correction pipeline', 'grammar correction algorithm', 'grammar correction library', 'grammar correction framework', 'grammar correction service', 'grammar correction function', 'grammar correction engine', 'grammar correction engines', 'grammar corrector', 'grammar correctors', 'corrects grammar', 'correct grammar', 'corrects grammatical errors', 'correct grammatical errors', 'corrects grammar mistakes', 'correct grammar mistakes', 'fix grammar', 'fixes grammar', 'fix grammatical errors', 'fixes grammatical errors', 'grammar checking', 'grammar-checking', 'grammar checker', 'grammar checkers', 'grammar error correction', 'grammatical error correction', 'gec model', 'gec system', 'grammar correction task', 'grammar correction benchmark', 'automatic grammar correction', 'automated grammar correction', 'corrects your grammar', 'correct my grammar', 'grammar correction software', 'grammar correction app', 'grammar correction program']
EXPECTED_NOGRAMMARCORRECTION = ['does not support grammar correction', 'do not support grammar correction', "doesn't support grammar correction", "don't support grammar correction", 'no grammar correction', 'without grammar correction', 'never performs grammar correction', 'does not perform grammar correction', 'grammar correction not supported', 'grammar correction unsupported', 'no grammar correction support', 'lacks grammar correction', 'missing grammar correction', 'grammar correction disabled', 'no grammar correction capability', 'without grammar correction support', 'does not provide grammar correction', 'no grammar correction model', 'grammar correction not available', 'does not use grammar correction', 'no grammar corrector', 'without grammar corrector', 'does not support grammar corrector', 'no grammar checker']
EXPECTED_GENERIC_NAMES = ['correct_grammar', 'grammar_correction', 'fix_grammar', 'correct_text', 'grammar_check', 'check_grammar', 'correct_sentence', 'fix_grammatical_errors', 'grammar_corrector', 'correct_english', 'fix_typos_and_grammar', 'grammar_fix', 'correct_spelling_and_grammar', 'proofread', 'proofread_text', 'correct_writing', 'grammar_error_correction', 'gec', 'correct_grammar_errors', 'fix_grammar_errors', 'grammar_correction_tool', 'correct_sentence_grammar', 'fix_writing_errors', 'grammar_correction_model']
EXPECTED_LANGUAGETOOL_CLASSES = ['LanguageTool', 'LanguageToolPublicAPI']
EXPECTED_GRAMFORMER_CLASSES = ['Gramformer']
EXPECTED_HAPPY_CLASSES = ['HappyTextToText']
EXPECTED_GINGER_CLASSES = ['GingerIt']

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from grammar_correction_claim_audit import phrases
from grammar_correction_claim_audit.audit import audit, evidence, main, match_phrases, prose


class AuditTests(unittest.TestCase):
    def fixture(self, files):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        return root

    def cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = main(list(map(str, args)))
            except SystemExit as error:
                code = error.code
        return code, output.getvalue(), errors.getvalue()

    def test_phrase_oracle(self):
        self.assertEqual(phrases.GRAMMARCORRECTION, EXPECTED_GRAMMARCORRECTION)
        self.assertEqual(phrases.NOGRAMMARCORRECTION, EXPECTED_NOGRAMMARCORRECTION)
        self.assertEqual(len(EXPECTED_GRAMMARCORRECTION), 50)
        self.assertEqual(len(EXPECTED_NOGRAMMARCORRECTION), 24)

    def test_generic_oracle(self):
        self.assertEqual(phrases.GENERIC_NAMES, EXPECTED_GENERIC_NAMES)
        self.assertEqual(len(EXPECTED_GENERIC_NAMES), 24)

    def test_dedicated_oracle(self):
        self.assertEqual(phrases.LANGUAGETOOL_CLASSES, ['LanguageTool', 'LanguageToolPublicAPI'])
        self.assertEqual(phrases.GRAMFORMER_CLASSES, ['Gramformer'])
        self.assertEqual(phrases.HAPPY_CLASSES, ['HappyTextToText'])
        self.assertEqual(phrases.GINGER_CLASSES, ['GingerIt'])

    def test_all_phrases(self):
        for phrase in EXPECTED_GRAMMARCORRECTION:
            with self.subTest(phrase=phrase):
                self.assertEqual(match_phrases(phrase), ([{'phrase': phrase, 'offset': 0}], []))
        for phrase in EXPECTED_NOGRAMMARCORRECTION:
            with self.subTest(phrase=phrase):
                self.assertEqual(match_phrases(phrase), ([], [{'phrase': phrase, 'offset': 0}]))

    def test_assigned_pairs(self):
        for cls, method in [('LanguageTool', 'correct'), ('LanguageToolPublicAPI', 'correct'),
                            ('Gramformer', 'correct'), ('HappyTextToText', 'generate_text'), ('GingerIt', 'parse')]:
            for imports, constructor in [('', cls), ('import anything as a\n', 'a.' + cls),
                    ('from anything import ' + cls + ' as C\n', 'C')]:
                with self.subTest(cls=cls, imports=imports):
                    self.assertTrue(evidence(imports + 'tool = ' + constructor + '()\ntool.' + method + '(text)'))

    def test_chained_pairs(self):
        for cls, method in [('LanguageTool', 'correct'), ('LanguageToolPublicAPI', 'correct'),
                            ('Gramformer', 'correct'), ('HappyTextToText', 'generate_text'), ('GingerIt', 'parse')]:
            for imports, constructor in [('', cls), ('import anything as a\n', 'a.' + cls),
                    ('from anything import ' + cls + ' as C\n', 'C')]:
                with self.subTest(cls=cls, imports=imports):
                    self.assertTrue(evidence(imports + constructor + '().' + method + '(text)'))

    def test_real_module_imports(self):
        for module, cls, method in [('language_tool_python', 'LanguageTool', 'correct'),
                ('language_tool_python', 'LanguageToolPublicAPI', 'correct'),
                ('gramformer', 'Gramformer', 'correct'), ('happytransformer', 'HappyTextToText', 'generate_text'),
                ('gingerit.gingerit', 'GingerIt', 'parse')]:
            self.assertTrue(evidence('import ' + module + '\nx=' + module + '.' + cls + '()\nx.' + method + '(text)'))

    def test_generic_attributes(self):
        for name in EXPECTED_GENERIC_NAMES:
            for base in ['anything', 'thing.client', 'factory()', 'items[0]']:
                with self.subTest(name=name, base=base):
                    self.assertTrue(evidence(base + '.' + name + '(text)'))

    def test_generic_imports(self):
        for name in EXPECTED_GENERIC_NAMES:
            for alias in [name, 'repair']:
                with self.subTest(name=name, alias=alias):
                    self.assertTrue(evidence('from arbitrary import ' + name + ' as ' + alias + '\n' + alias + '(text)'))

    def test_assignment_aliases(self):
        self.assertTrue(evidence('x=LanguageTool()\ny=x\ny.correct(text)'))

    def test_bare_import_rejection(self):
        for module in ['language_tool_python', 'gramformer', 'happytransformer', 'gingerit']:
            self.assertFalse(evidence('import ' + module))
        for name in EXPECTED_GENERIC_NAMES:
            self.assertFalse(evidence('from anything import ' + name))

    def test_neighbor_rejection(self):
        for source in ['from spellchecker import SpellChecker\ns=SpellChecker()\ns.correction(word)',
                'dictionary.lookup(word)', 'pipeline("paraphrase")(text)',
                'from transformers import pipeline\np=pipeline("text2text-generation", model="t5-paraphrase")\np(text)',
                'pipeline("text-generation")(text)', 'llm.generate(text)',
                'pipeline("translation")(text)', 'subprocess.run(["grammar-correction", text])']:
            with self.subTest(source=source):
                self.assertFalse(evidence(source))

    def test_lone_constructions_and_calls(self):
        for cls in ['LanguageTool', 'LanguageToolPublicAPI', 'Gramformer', 'HappyTextToText', 'GingerIt']:
            self.assertFalse(evidence(cls + '()'))
            self.assertFalse(evidence(cls))
        for method in ['correct', 'generate_text', 'parse']:
            self.assertFalse(evidence('x.' + method + '(text)'))

    def test_wrong_receiver_or_method(self):
        for source in ['tool=LanguageTool()\nother.correct(text)',
                'tool=HappyTextToText()\ntool.correct(text)',
                'tool=GingerIt()\ntool.generate_text(text)',
                'tool=Gramformer()\ntool.parse(text)',
                'tool=LanguageTool()\ntool=Other()\ntool.correct(text)']:
            self.assertFalse(evidence(source))

    def test_non_calls(self):
        for source in ['"grammar correction"', '# grammar checker\n',
                '"""LanguageTool().correct(text)"""', 'x.correct_grammar',
                'from x import correct_grammar\ncorrect_grammar', 'correct_grammar(text)']:
            self.assertFalse(evidence(source))

    def test_shadowing(self):
        for cls, method in [('LanguageTool', 'correct'), ('LanguageToolPublicAPI', 'correct'),
                            ('Gramformer', 'correct'), ('HappyTextToText', 'generate_text'), ('GingerIt', 'parse')]:
            for definition in ['class ' + cls + ': pass', 'def ' + cls + '(): pass']:
                for prefix, use in [('from x import ' + cls + '\n', cls),
                                    ('from x import ' + cls + ' as C\n', 'C')]:
                    self.assertFalse(evidence(prefix + definition + '\n' + use + '().' + method + '(text)'))
        for name in EXPECTED_GENERIC_NAMES:
            self.assertFalse(evidence('from x import ' + name + '\ndef ' + name + '(): pass\n' + name + '(text)'))
            self.assertFalse(evidence('from x import ' + name + ' as c\ndef ' + name + '(): pass\nc(text)'))
        self.assertFalse(evidence('import language_tool_python as t\nclass t: pass\nt.LanguageTool().correct(text)'))

    def test_split_modules(self):
        for cls, method in [('LanguageTool', 'correct'), ('Gramformer', 'correct'),
                            ('HappyTextToText', 'generate_text'), ('GingerIt', 'parse')]:
            root = self.fixture({'README.md': 'grammar correction', 'a.py': 'x=' + cls + '()',
                                 'b.py': 'from a import x\nx.' + method + '(text)'})
            self.assertEqual(audit(root)[0]['severity'], 'HIGH')

    def test_span_removal(self):
        self.assertEqual(match_phrases('does not support grammar correction')[0], [])
        self.assertEqual(audit(self.fixture({'README.md': 'does not support grammar correction'})), [])

    def test_longest_first(self):
        for phrase in ['grammar correction model', 'grammar correction models']:
            self.assertEqual(match_phrases(phrase), ([{'phrase': phrase, 'offset': 0}], []))
        self.assertEqual(len(match_phrases('grammar correction model; grammar correction models')[0]), 2)

    def test_case_insensitive(self):
        result = audit(self.fixture({'README.md': 'GRAMMAR CORRECTION'}))
        self.assertEqual(result[0]['severity'], 'HIGH')

    def test_collision_limitation(self):
        self.assertEqual(match_phrases('correct grammar is important for essays')[0][0]['phrase'], 'correct grammar')

    def test_fences(self):
        for marker in ['```', '~~~', '````']:
            self.assertEqual(match_phrases(prose(marker + 'text\ngrammar correction\n' + marker))[0], [])

    def test_inline_counts(self):
        self.assertTrue(match_phrases(prose('`grammar correction`'))[0])

    def test_cli_good(self):
        root = self.fixture({'README.md': 'grammar correction', 'app.py': 'LanguageTool().correct(text)'})
        self.assertEqual(self.cli('audit', root)[:2], (0, 'PASS\n'))

    def test_cli_bad_json(self):
        root = self.fixture({'README.md': 'grammar correction'})
        code, output, _ = self.cli('audit', root, '--json')
        self.assertEqual(code, 2)
        finding = json.loads(output)[0]
        self.assertEqual(finding['rule'], 'documented-grammar-correction-claim-false')
        self.assertEqual(finding['severity'], 'HIGH')
        self.assertEqual(finding['verdict'], 'FAIL')
        self.assertTrue(finding['message'])

    def test_cli_test_only(self):
        root = self.fixture({'tests/fixture.py': '"grammar correction"'})
        code, output, _ = self.cli('audit', root, '--json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)[0]['severity'], 'MEDIUM')
        self.assertEqual(self.cli('audit', root, '--fail-on', 'medium')[0], 2)

    def test_nested_test_fixtures(self):
        root = self.fixture({'docs/tests/fixture.md': 'grammar correction'})
        self.assertEqual(audit(root)[0]['severity'], 'MEDIUM')
        self.assertEqual(self.cli('audit', root)[0], 0)
        self.assertEqual(self.cli('audit', root, '--fail-on', 'medium')[0], 2)

    def test_cli_denial(self):
        root = self.fixture({'README.md': 'no grammar correction', 'a.py': 'x.correct_text(text)'})
        code, output, _ = self.cli('audit', root, '--json')
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)[0]['rule'], 'documented-no-grammar-correction-claim-false')
        self.assertEqual(json.loads(output)[0]['severity'], 'HIGH')

    def test_cli_no_claim(self):
        self.assertEqual(self.cli('audit', self.fixture({'README.md': 'Hello'}))[:2], (0, 'PASS\n'))

    def test_cli_denial_without_sources(self):
        self.assertEqual(self.cli('audit', self.fixture({'README.md': 'no grammar correction'}))[:2], (0, 'PASS\n'))

    def test_cli_version(self):
        self.assertEqual(self.cli('--version')[:2], (0, '0.1.0\n'))

    def test_ignore(self):
        root = self.fixture({'docs/drafts/a.md': 'grammar correction'})
        self.assertEqual(self.cli('audit', root)[0], 2)
        self.assertEqual(self.cli('audit', root, '--ignore', 'docs/drafts/')[0], 0)

    def test_ignore_before_repo(self):
        root = self.fixture({'README.md': 'grammar correction', 'docs/a.md': 'grammar correction'})
        self.assertEqual(self.cli('audit', '--ignore', 'README.md', '--ignore', 'docs/', root)[:2], (0, 'PASS\n'))

    def test_ignore_evidence(self):
        root = self.fixture({'README.md': 'grammar correction', 'app.py': 'x.correct_text(text)'})
        self.assertEqual(self.cli('audit', root, '--ignore', 'app.py')[0], 2)

    def test_verbose(self):
        root = self.fixture({'README.md': 'Hello', 'a.py': 'pass'})
        code, _, errors = self.cli('audit', root, '--verbose')
        self.assertEqual(code, 0)
        self.assertIn('Scope:', errors)
        self.assertIn('README.md', errors)
        self.assertIn('a.py', errors)

    def test_usage_io_errors(self):
        for args in [[], ['other'], ['audit', '--fail-on', 'low'], ['audit', '--ignore'], ['audit', '/no/such/repo']]:
            self.assertEqual(self.cli(*args)[0], 1)
        root = self.fixture({'README.md': 'hello'})
        (root / 'README.md').write_bytes(b'\xff')
        self.assertEqual(self.cli('audit', root)[0], 1)

    def test_scope_and_exclusions(self):
        for folder in ['.git', '__pycache__', '.venv', 'venv', 'env', '.tox', '.nox', 'custom-env']:
            files = {'README.md': 'grammar correction', folder + '/a.py': 'x.correct_text(text)'}
            if folder == 'custom-env':
                files[folder + '/pyvenv.cfg'] = 'home = /usr/bin'
            self.assertEqual(audit(self.fixture(files))[0]['severity'], 'HIGH')
        self.assertEqual(audit(self.fixture({'other.md': 'grammar correction'})), [])
        self.assertEqual(audit(self.fixture({'docs/nested/a.md': 'grammar correction'}))[0]['severity'], 'HIGH')

    def test_invalid_python(self):
        self.assertFalse(evidence('def syntax error'))

    def test_default_repo(self):
        import os
        root = self.fixture({'README.md': 'Hello'})
        previous = Path.cwd()
        try:
            os.chdir(root)
            self.assertEqual(self.cli('audit')[:2], (0, 'PASS\n'))
        finally:
            os.chdir(previous)

    def test_built_readme_self_audit(self):
        root = Path(__file__).resolve().parents[1]
        positive, negative = match_phrases(prose((root / 'README.md').read_text(encoding='utf-8')))
        self.assertEqual((positive, negative), ([], []))
        self.assertEqual(self.cli('audit', root)[0], 0)


if __name__ == '__main__':
    unittest.main()
