"""The verbatim configuration contract, enforced on BYTES (review finding config 2).

The contract: `config.json`, the block of ARCHITECTURE_FINAL.md section 6.1 and
the block of protocol_FINAL.md Appendix B are one block. protocol_FINAL.md
Appendix B says "a freeze test compares the two byte for byte after stripping the
fences", and root's 16:30 decision 3 says "Synchronize ... byte-for-byte".

The finding, confirmed at 5a81c34:

    config 2: "The standing 'byte for byte' verbatim guard compares
    newline-normalized text, so a byte-divergent config.json or protocol block
    passes." Expected instead: "compare read_bytes() blocks (fence extraction on
    bytes) and assert zero CR bytes, so the suite enforces the byte-for-byte
    contract that the protocol text and root's ruling state."

`tests_lab_e2e.ConfigTests.test_config_is_appendix_b_verbatim` is under the
pinned glob experiments/live_ab/*.py, so it is NOT edited. It still reads text,
and Path.read_text decodes CRLF and a lone CR as LF. This file is its byte-level
twin, outside the pinned glob. It enforces two things:
  * the three blocks are byte-identical. Each block is extracted from
    read_bytes() with the same fence extraction the e2e test performs
    (marker, then the first ```json fence, then leading newlines stripped);
  * none of the three FILES carries a CR byte, inside or outside a block. A CR
    outside a block leaves the block unchanged, but it still moves config_sha256
    or a document digest, and the contract names the files.
It does NOT check that the block is the reviewed or frozen one (no digest is
pinned here; that is the freeze's job), nor that each fence lies inside its
section (the amendment tool checks that when it writes).

Negative controls, built in memory from the on-disk bytes, never written. These
are the reviewer's CRLF witnesses:
  B  config.json with CRLF line endings;
  C  one CRLF inside the protocol Appendix B block;
  D  one lone CR inside the ARCHITECTURE section 6.1 block.
Each one passes a newline-normalizing comparison, which is the e2e test's reading,
and must fail here. Two more: E, a real content change, which both readings
catch; and F, a CRLF outside every block, which only the no-CR rule catches.
"""

from __future__ import annotations

import io
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
FILES = {'config': LAB / 'config.json',
         'architecture': LAB / 'design' / 'ARCHITECTURE_FINAL.md',
         'protocol': LAB / 'design' / 'protocol_FINAL.md'}
MARKERS = {'architecture': b'### 6.1 Full key list', 'protocol': b'## Appendix B.'}


def block_bytes(raw: bytes, marker: bytes) -> bytes:
    """tests_lab_e2e.py's extraction, on bytes: the marker, the first ```json
    fence after it, the bytes up to the closing ```, leading newlines stripped."""
    i = raw.index(marker)
    j = raw.index(b'```json', i)
    k = raw.index(b'```', j + 7)
    return raw[j + 7:k].lstrip(b'\n')


def contract_failures(raw: dict) -> list:
    """Every way ``raw`` ({'config', 'architecture', 'protocol'} -> bytes) breaks
    the byte contract. An empty list means it holds."""
    fails = []
    for name in FILES:
        n = raw[name].count(b'\r')
        if n:
            fails.append('%s carries %d CR byte(s)' % (name, n))
    try:
        blocks = {'config': raw['config'],
                  'architecture': block_bytes(raw['architecture'], MARKERS['architecture']),
                  'protocol': block_bytes(raw['protocol'], MARKERS['protocol'])}
    except ValueError as e:
        return fails + ['a configuration block could not be extracted: %s' % e]
    if blocks['architecture'] != blocks['protocol']:
        fails.append('ARCHITECTURE 6.1 and protocol Appendix B differ as bytes')
    if blocks['config'] != blocks['architecture']:
        fails.append('config.json differs, as bytes, from the ARCHITECTURE 6.1 block')
    return fails


def newline_normalized_agree(raw: dict) -> bool:
    """The e2e test's reading, reproduced for the controls: Path.read_text decodes
    with universal newlines (CRLF and lone CR become LF), then the same
    extraction and a string comparison."""
    def text(b: bytes) -> str:
        return io.TextIOWrapper(io.BytesIO(b), encoding='utf-8').read()

    def block(t: str, marker: str) -> str:
        i = t.index(marker)
        j = t.index('```json', i)
        k = t.index('```', j + 7)
        return t[j + 7:k].lstrip('\n')
    a = block(text(raw['architecture']), '### 6.1 Full key list')
    p = block(text(raw['protocol']), '## Appendix B.')
    return a == p == text(raw['config'])


def _in_block_newline(raw: bytes, marker: bytes, repl: bytes) -> bytes:
    """Replace the newline at the end of the block's SECOND line with ``repl``."""
    i = raw.index(marker)
    f = raw.index(b'```json', i) + 7
    e = raw.index(b'```', f)
    first = raw.index(b'\n', f + 1)
    target = raw.index(b'\n', first + 1)
    assert f < target < e
    return raw[:target] + repl + raw[target + 1:]


class ConfigByteContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not all(p.is_file() for p in FILES.values()):
            raise unittest.SkipTest('the design documents are not present in this checkout')
        cls.disk = {k: p.read_bytes() for k, p in FILES.items()}

    # -- the standing contract, on the files as committed -------------------
    def test_no_cr_byte_in_any_of_the_three_files(self):
        for name, raw in self.disk.items():
            with self.subTest(file=name):
                self.assertNotIn(b'\r', raw, '%s carries a CR byte' % FILES[name])

    def test_the_three_blocks_are_byte_identical(self):
        a = block_bytes(self.disk['architecture'], MARKERS['architecture'])
        p = block_bytes(self.disk['protocol'], MARKERS['protocol'])
        self.assertEqual(a, p, 'ARCHITECTURE 6.1 and protocol Appendix B differ as bytes')
        self.assertEqual(self.disk['config'], a,
                         'config.json is not, byte for byte, the ARCHITECTURE 6.1 block')

    def test_the_files_on_disk_satisfy_the_contract(self):
        self.assertEqual(contract_failures(self.disk), [])

    # -- negative controls, in memory ----------------------------------------
    def _witness(self, **changed):
        w = dict(self.disk)
        w.update(changed)
        return w

    def _assert_byte_only_divergence_is_caught(self, w, label):
        self.assertTrue(newline_normalized_agree(w),
                        '%s: not a newline-only divergence; fix the control' % label)
        self.assertNotEqual(contract_failures(w), [],
                            '%s: the byte contract did not notice' % label)

    def test_B_a_crlf_config_json_is_caught(self):
        w = self._witness(config=self.disk['config'].replace(b'\n', b'\r\n'))
        self._assert_byte_only_divergence_is_caught(w, 'B')
        self.assertTrue(any('config.json differs' in f for f in contract_failures(w)))

    def test_C_one_crlf_inside_the_protocol_appendix_b_block_is_caught(self):
        w = self._witness(protocol=_in_block_newline(
            self.disk['protocol'], MARKERS['protocol'], b'\r\n'))
        self._assert_byte_only_divergence_is_caught(w, 'C')
        self.assertTrue(any('differ as bytes' in f for f in contract_failures(w)))

    def test_D_a_lone_cr_inside_the_architecture_6_1_block_is_caught(self):
        w = self._witness(architecture=_in_block_newline(
            self.disk['architecture'], MARKERS['architecture'], b'\r'))
        self._assert_byte_only_divergence_is_caught(w, 'D')
        self.assertTrue(any('differ as bytes' in f for f in contract_failures(w)))

    def test_E_a_content_change_is_caught_by_both_readings(self):
        cfg = self.disk['config']
        self.assertIn(b'2048', cfg)
        w = self._witness(config=cfg.replace(b'2048', b'2049', 1))
        self.assertFalse(newline_normalized_agree(w))
        self.assertNotEqual(contract_failures(w), [])

    def test_F_a_crlf_outside_every_block_is_caught_by_the_cr_rule(self):
        arch = self.disk['architecture']
        nl = arch.index(b'\n')
        self.assertLess(nl, arch.index(MARKERS['architecture']))
        w = self._witness(architecture=arch[:nl] + b'\r' + arch[nl:])
        self._assert_byte_only_divergence_is_caught(w, 'F')
        self.assertEqual(contract_failures(w), ['architecture carries 1 CR byte(s)'])


if __name__ == '__main__':                                     # pragma: no cover
    unittest.main()
