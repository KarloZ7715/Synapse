import { render, screen } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { ChatBubble } from "~/components/chat/ChatBubble";

describe("ChatBubble", () => {
  it("renders user variant", () => {
    render(() => <ChatBubble variant="user">Hello</ChatBubble>);
    expect(screen.getByText("Hello")).toBeTruthy();
  });

  it("renders assistant variant", () => {
    render(() => <ChatBubble variant="assistant">Response</ChatBubble>);
    expect(screen.getByText("Response")).toBeTruthy();
  });
});
