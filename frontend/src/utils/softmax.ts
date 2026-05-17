/** Softmax estable en Float32Array (copia). */
export function softmax(logits: Float32Array): Float32Array {
  if (logits.length === 0) {
    return new Float32Array();
  }
  let max = Number.NEGATIVE_INFINITY;
  for (let i = 0; i < logits.length; i++) {
    const v = logits[i];
    if (v > max) {
      max = v;
    }
  }
  let sum = 0;
  const exp = new Float32Array(logits.length);
  for (let i = 0; i < logits.length; i++) {
    exp[i] = Math.exp(logits[i] - max);
    sum += exp[i];
  }
  for (let i = 0; i < logits.length; i++) {
    exp[i] /= sum;
  }
  return exp;
}

export function argmax(values: Float32Array): number {
  let best = 0;
  let bestVal = values[0] ?? Number.NEGATIVE_INFINITY;
  for (let i = 1; i < values.length; i++) {
    if (values[i] > bestVal) {
      bestVal = values[i];
      best = i;
    }
  }
  return best;
}

/** Media geométrica de valores en (0,1]; evita 0. */
export function geometricMean(values: readonly number[]): number {
  const filtered = values.filter((v) => v > 0);
  if (filtered.length === 0) {
    return 0;
  }
  const logSum = filtered.reduce((acc, v) => acc + Math.log(v), 0);
  return Math.exp(logSum / filtered.length);
}
