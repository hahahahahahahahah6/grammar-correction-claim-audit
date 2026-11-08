# Documentation claim auditor

An offline, deterministic Python 3.9+ utility comparing documentation with static
source evidence for repairing word order, agreement, tense, articles, or
punctuation in an existing sentence. Runtime uses only the standard library.
There is no network access, telemetry, target code execution, or file writing.

## Usage

```sh
python3 -m pip install .
grammar-correction-claim-audit --version
grammar-correction-claim-audit audit /path/to/repo --json
python3 -m grammar_correction_claim_audit audit --ignore docs/drafts/ /path/to/repo
python3 -m unittest discover
python3 -m build
```

The repository defaults to the current directory. Each ignore option takes one
relative path prefix and may be repeated. Ignored paths contribute neither
claims nor evidence. Exit codes are 0 for no findings at the chosen threshold,
2 for findings at that threshold, and 1 for usage or IO errors. The default
threshold is high; medium also fails on test fixtures. Version output is 0.1.0.
JSON output is a list with rule, severity, path, phrase, verdict, and message
fields per finding. Each finding has verdict FAIL. An empty list means no
findings. Verbose output reports scope and file decisions on stderr.

```text
documented-grammar-correction-claim-false HIGH
documented-no-grammar-correction-claim-false HIGH
Positive claims confined to tests: MEDIUM
```

## Matching and evidence

Shipped prose is the root README.md and Markdown under docs. Files beneath a
tests directory may supply test-only claims. Backtick or tilde fenced code is
excluded. Inline code counts as prose. Matching uses case-insensitive exact
substrings, removes denial spans first, and has no stemming or hyphen
normalization. Longest-first matching makes each occurrence match once under
its longest phrase. A positive claim needs evidence; a denial conflicts with
evidence. No claims passes; a denial with no sources also passes.

Each Python module is checked independently. Imports and aliases resolve
structurally. Local function and class definitions shadow route names throughout
that module. Construction and its instance call must occur in the same module;
assigned and chained forms count. Supported pairs are:

```text
LanguageTool or LanguageToolPublicAPI construction + instance.correct()
Gramformer construction + instance.correct()
HappyTextToText construction + instance.generate_text()
GingerIt construction + instance.parse()
```

Generic attribute calls on any base, or imported bare calls, also count when
their names belong to the vocabulary. Bare imports, unbound references, strings,
comments, subprocess invocations, lone constructions, and unmatched instance
calls contribute no evidence. Git metadata, bytecode caches, conventional
virtual environments, directories containing pyvenv.cfg, and symlinks are
excluded. Unreadable scoped files cause an IO error. Invalid Python contributes
no evidence.

## Differentiation

```text
paraphrasing-claim-audit
```

That utility checks restating a sentence in different words. This one checks
repairing errors inside the same sentence.

```text
text-generation-claim-audit
```

That utility checks writing new text. This one checks repairing existing text.

```text
translation-claim-audit
```

That utility checks changing the language of a text. This one checks repairing
errors inside one language.

## Limitations

This is static pattern matching, not semantic judgement. Exact phrases miss
restatements. Calls do not prove execution, input suitability, or output quality.
Dynamic imports, runtime mutation, control flow, and intermodule data flow are
outside the analysis. Simple assignment aliases are recognized.

A spell-checking call is deliberately not counted: fixing individual misspelled
words does not repair sentence structure. Restating, generating, and translating
alone also do not establish the checked capability.

A generic call on an unrelated object counts because its method name is shared:

```python
unrelated.correct_text(text)
```

These phrases can describe grammatically correct language in general, a school
exercise, or a person reviewing writing. They still match; intent is unknown:

```text
correct grammar is important for essays
grammar correction worksheet
our grammar checker reviews every draft
```

## Distribution

The source archive includes the test suite and its discovery marker. The
installed utility exposes both a console command and a module entry point.
