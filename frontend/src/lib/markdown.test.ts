import { describe, it, expect } from "vitest";
import { renderMarkdown, escapeHtml, highlight } from "./markdown";

describe("escapeHtml", () => {
  it("escapes all HTML-significant characters", () => {
    expect(escapeHtml(`<a href="x">'&'</a>`)).toBe(
      "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;",
    );
  });
});

describe("renderMarkdown", () => {
  it("renders basic markdown to HTML", () => {
    const html = renderMarkdown("**bold** and *italic*");
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("<em>italic</em>");
  });

  it("strips dangerous tags (XSS sanitisation)", () => {
    const html = renderMarkdown("<script>alert(1)</script><img src=x onerror=alert(1)>");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("onerror");
    expect(html).not.toContain("<img");
  });

  it("hardens links with target and rel attributes", () => {
    const html = renderMarkdown("[link](https://example.com)");
    expect(html).toContain('target="_blank"');
    expect(html).toContain("noopener");
    expect(html).toContain("noreferrer");
  });
});

describe("highlight", () => {
  it("wraps matching terms in <mark> while escaping the rest", () => {
    const out = highlight("Security policy & rules", "security");
    expect(out).toContain("<mark>Security</mark>");
    expect(out).toContain("&amp;");
  });

  it("returns escaped text unchanged when query is empty", () => {
    expect(highlight("<b>", "")).toBe("&lt;b&gt;");
  });

  it("ignores single-character terms", () => {
    expect(highlight("a big cat", "a")).not.toContain("<mark>");
  });

  it("treats regex metacharacters in the query as literals", () => {
    // Must not throw and must not match everything.
    const out = highlight("plain text", "(.*)");
    expect(out).toBe("plain text");
  });
});
