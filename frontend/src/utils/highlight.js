// Small, dependency-free Python highlighter. Produces tokens rendered as React text (never as HTML),
// so repository code cannot inject markup. Triple-quoted strings are tracked across lines.

const KEYWORDS = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del',
  'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'match',
  'case', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield', 'self', 'cls',
]);

const BUILTINS = new Set([
  'abs', 'all', 'any', 'bool', 'bytes', 'bytearray', 'dict', 'enumerate', 'filter', 'float', 'getattr', 'hasattr',
  'int', 'isinstance', 'len', 'list', 'map', 'max', 'min', 'open', 'print', 'range', 'repr', 'set', 'setattr',
  'sorted', 'str', 'sum', 'super', 'tuple', 'type', 'zip', 'Exception', 'ValueError', 'TypeError', 'KeyError',
]);

const TOKEN = /(#.*$)|([rRbBuUfF]{0,2}(?:"""|'''|"(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?))|(@[\w.]+)|(\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b|\b0[xXoObB][\da-fA-F_]+\b)|([A-Za-z_]\w*)/g;

function scanLine(line, state) {
  const tokens = [];
  let position = 0;

  if (state.openQuote) {
    const close = line.indexOf(state.openQuote);
    if (close === -1) return { tokens: [{ type: 'string', text: line }], state };
    tokens.push({ type: 'string', text: line.slice(0, close + 3) });
    position = close + 3;
    state = { openQuote: null };
  }

  TOKEN.lastIndex = position;
  let match;
  while ((match = TOKEN.exec(line))) {
    if (match.index > position) tokens.push({ type: 'plain', text: line.slice(position, match.index) });
    const [text, comment, string, decorator, number, word] = match;
    if (comment) tokens.push({ type: 'comment', text });
    else if (string) {
      const triple = /("""|''')/.exec(string);
      if (triple) {
        const rest = line.slice(match.index + triple.index + 3);
        const close = rest.indexOf(triple[1]);
        if (close === -1) {
          tokens.push({ type: 'string', text: line.slice(match.index) });
          return { tokens, state: { openQuote: triple[1] } };
        }
        const end = match.index + triple.index + 3 + close + 3;
        tokens.push({ type: 'string', text: line.slice(match.index, end) });
        position = end;
        TOKEN.lastIndex = end;
        continue;
      }
      tokens.push({ type: 'string', text });
    } else if (decorator) tokens.push({ type: 'decorator', text });
    else if (number) tokens.push({ type: 'number', text });
    else if (word) tokens.push({ type: KEYWORDS.has(word) ? 'keyword' : BUILTINS.has(word) ? 'builtin' : 'plain', text });
    position = match.index + text.length;
  }
  if (position < line.length) tokens.push({ type: 'plain', text: line.slice(position) });
  return { tokens, state };
}

/** Tokenise source into lines of tokens. Non-Python languages are returned as plain text. */
export function highlight(code = '', language = 'python') {
  const lines = code.replace(/\n$/, '').split('\n');
  if (language !== 'python') return lines.map((text) => [{ type: 'plain', text }]);
  let state = { openQuote: null };
  return lines.map((line) => {
    const result = scanLine(line, state);
    state = result.state;
    return result.tokens;
  });
}

export function languageFromPath(path = '') {
  const ext = path.split('.').pop()?.toLowerCase();
  return { py: 'python', pyi: 'python', js: 'javascript', ts: 'typescript', md: 'markdown', json: 'json' }[ext] || 'text';
}

export const LANGUAGE_LABELS = { python: 'Python', javascript: 'JavaScript', typescript: 'TypeScript', markdown: 'Markdown', json: 'JSON', text: 'Text' };
