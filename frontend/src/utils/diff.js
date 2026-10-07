// Parse a unified diff into the line numbers removed from the original and added in the repair.
export function changedLines(diff = '') {
  const removed = new Set();
  const added = new Set();
  let oldLine = 0;
  let newLine = 0;
  for (const line of diff.split('\n')) {
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(line);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      continue;
    }
    if (line.startsWith('---') || line.startsWith('+++') || !oldLine) continue;
    if (line.startsWith('-')) {
      removed.add(oldLine);
      oldLine += 1;
    } else if (line.startsWith('+')) {
      added.add(newLine);
      newLine += 1;
    } else {
      oldLine += 1;
      newLine += 1;
    }
  }
  return { removed, added };
}
