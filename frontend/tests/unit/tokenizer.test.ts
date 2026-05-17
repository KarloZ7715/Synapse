import { describe, expect, it } from "vitest";
import { encodeText, padIds, tokenize } from "~/utils/tokenizer";

describe("tokenize", () => {
  it("extrae tokens alfabéticos en Unicode (paridad con Python)", () => {
    expect(tokenize("¿Cómo hago un deploy?")).toEqual(["cómo", "hago", "un", "deploy"]);
  });

  it("normaliza a minúsculas", () => {
    expect(tokenize("Python Django")).toEqual(["python", "django"]);
  });
});

describe("encodeText + padIds", () => {
  const w2i: Record<string, number> = {
    "<pad>": 0,
    "<unk>": 1,
    cómo: 2,
    hago: 3,
  };

  it("pad hasta maxLen", () => {
    const ids = encodeText("¿Cómo hago", w2i, 8);
    const padded = padIds(ids, 8, 0);
    expect(padded).toHaveLength(8);
    expect(padded.slice(0, 2)).toEqual([2, 3]);
    expect(padded.slice(2)).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it("usa unk para token desconocido", () => {
    const ids = encodeText("xyzunknown", w2i, 10);
    expect(ids.every((id) => id === 1)).toBe(true);
  });
});
