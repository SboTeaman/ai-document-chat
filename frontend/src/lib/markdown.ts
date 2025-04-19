import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ gfm: true, breaks: true });

// Force every <a> through external-link hardening: no window.opener access,
// no referrer leak, and (where supported) no SEO inheritance.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer nofollow");
  }
});

/** Render Markdown to HTML, then sanitise it with DOMPurify (XSS-safe). */
export function renderMarkdown(text: string): string {
  const html = marked.parse(text, { async: false }) as string;
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      "p", "br", "strong", "em", "del", "code", "pre", "blockquote",
      "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "h6",
      "table", "thead", "tbody", "tr", "th", "td", "hr", "span",
    ],
    ALLOWED_ATTR: ["href", "title", "target", "rel", "class"],
  });
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Escape text, then wrap each query term (>1 char, regex-safe) in <mark>. */
export function highlight(text: string, query: string): string {
  const safe = escapeHtml(text);
  if (!query.trim()) return safe;
  const terms = query
    .split(/\s+/)
    .filter((t) => t.length > 1)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!terms.length) return safe;
  const re = new RegExp(`(${terms.join("|")})`, "gi");
  return safe.replace(re, '<mark>$1</mark>');
}
