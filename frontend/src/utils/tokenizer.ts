/**
 * Tokenización alineada con `train_textcnn.py` (`[^\W\d_]+` + UNICODE).
 * En JS, `\W` con `u` no replica exactamente Unicode word de Python; usamos
 * propiedades Unicode equivalentes para letras + marcas combinantes.
 */
const TOKEN_RE = /\p{L}[\p{L}\p{M}]*/gu;

/**
 * Replica `tokenize(text)` en Python: minúsculas + findall + filtro vacío.
 */
export function tokenize(text: string): string[] {
  const lower = text.toLowerCase();
  const raw = lower.match(TOKEN_RE) ?? [];
  return raw.map((t) => t.toLowerCase()).filter((t) => t.trim().length > 0);
}

export type Word2Idx = Readonly<Record<string, number>>;

/**
 * Replica `encode_text` (sin padding final; el caller hace pad).
 */
export function encodeText(text: string, word2idx: Word2Idx, maxLen: number): number[] {
  const unk = word2idx["<unk>"] ?? 1;
  const toks = tokenize(text).slice(0, maxLen);
  return toks.map((t) => (word2idx[t] !== undefined ? word2idx[t] : unk));
}

export function padIds(ids: number[], maxLen: number, padId: number): number[] {
  const sliced = ids.slice(0, maxLen);
  const out = sliced.slice();
  while (out.length < maxLen) {
    out.push(padId);
  }
  return out;
}
