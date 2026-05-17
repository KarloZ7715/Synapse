import { render, screen } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { Badge } from "~/components/ui/badge";

describe("Badge", () => {
  it("renders with correct text", () => {
    render(() => <Badge>principiante</Badge>);
    expect(screen.getByText("principiante")).toBeTruthy();
  });

  it("applies variant classes", () => {
    render(() => <Badge variant="cyan">active</Badge>);
    expect(screen.getByText("active")).toBeTruthy();
  });
});
