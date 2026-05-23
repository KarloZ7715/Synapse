import { describe, expect, it, vi } from "vitest";
import { scheduleStreamingUpdate } from "~/lib/scheduleUpdate";

describe("scheduleStreamingUpdate", () => {
  it("ejecuta el callback en un microtask posterior", async () => {
    const run = vi.fn();
    scheduleStreamingUpdate(run);
    expect(run).not.toHaveBeenCalled();
    await Promise.resolve();
    expect(run).toHaveBeenCalledOnce();
  });
});
