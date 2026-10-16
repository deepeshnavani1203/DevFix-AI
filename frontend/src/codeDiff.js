import { diffArrays } from 'diff';

export function buildLineDiff(original, corrected) {
  const changes = diffArrays(original.split('\n'), corrected.split('\n'));
  const rows = [];

  for (let index = 0; index < changes.length; index += 1) {
    const change = changes[index];
    if (!change.added && !change.removed) {
      change.value.forEach((line) => rows.push({ type: 'context', original: line, corrected: line }));
      continue;
    }

    const removed = change.removed ? change.value : [];
    const next = changes[index + 1];
    const added = change.added ? change.value : next?.added ? next.value : [];
    if (change.removed && next?.added) index += 1;

    const modifiedCount = Math.min(removed.length, added.length);
    for (let rowIndex = 0; rowIndex < modifiedCount; rowIndex += 1) {
      rows.push({ type: 'modified', original: removed[rowIndex], corrected: added[rowIndex] });
    }
    for (let rowIndex = modifiedCount; rowIndex < removed.length; rowIndex += 1) {
      rows.push({ type: 'removed', original: removed[rowIndex], corrected: null });
    }
    for (let rowIndex = modifiedCount; rowIndex < added.length; rowIndex += 1) {
      rows.push({ type: 'added', original: null, corrected: added[rowIndex] });
    }
  }

  let originalLine = 0;
  let correctedLine = 0;
  return rows.map((row) => {
    if (row.original !== null) originalLine += 1;
    if (row.corrected !== null) correctedLine += 1;
    return { ...row, originalLine: row.original !== null ? originalLine : null, correctedLine: row.corrected !== null ? correctedLine : null };
  });
}
