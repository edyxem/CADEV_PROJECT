import { describe, expect, it } from "vitest";

import { escapeHtml, textToHtml } from "./text";

describe("textToHtml", () => {
  it("crée des paragraphes et des retours à la ligne", () => {
    expect(textToHtml("Bonjour\nà tous\n\nSecond paragraphe")).toBe(
      "<p>Bonjour<br>à tous</p><p>Second paragraphe</p>",
    );
  });

  it("échappe toujours le HTML saisi", () => {
    const html = textToHtml('<script>alert("x")</script> & <b>gras</b>');

    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("&amp;");
  });

  it("gère le code en ligne et les blocs de code", () => {
    const html = textToHtml("Utilisez `select_related`.\n\n```python\nqs = Post.objects.all()\n```");

    expect(html).toBe(
      "<p>Utilisez <code>select_related</code>.</p><pre><code>qs = Post.objects.all()</code></pre>",
    );
  });

  it("échappe aussi le contenu des blocs de code", () => {
    expect(textToHtml("```\n<div>\n```")).toBe("<pre><code>&lt;div&gt;</code></pre>");
  });

  it("échappe les guillemets et apostrophes", () => {
    expect(escapeHtml(`"l'API"`)).toBe("&quot;l&#39;API&quot;");
  });
});
