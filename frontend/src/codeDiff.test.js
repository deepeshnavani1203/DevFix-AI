import test from 'node:test';
import assert from 'node:assert/strict';
import { buildLineDiff } from './codeDiff.js';

test('line diff aligns context and highlights added, removed, and modified lines', () => {
  const rows = buildLineDiff('keep\nold\nstay\nremove\ntail', 'keep\nnew\nstay\ntail\nadd');
  assert.deepEqual(rows, [
    { type: 'context', original: 'keep', corrected: 'keep', originalLine: 1, correctedLine: 1 },
    { type: 'modified', original: 'old', corrected: 'new', originalLine: 2, correctedLine: 2 },
    { type: 'context', original: 'stay', corrected: 'stay', originalLine: 3, correctedLine: 3 },
    { type: 'removed', original: 'remove', corrected: null, originalLine: 4, correctedLine: null },
    { type: 'context', original: 'tail', corrected: 'tail', originalLine: 5, correctedLine: 4 },
    { type: 'added', original: null, corrected: 'add', originalLine: null, correctedLine: 5 },
  ]);
});
