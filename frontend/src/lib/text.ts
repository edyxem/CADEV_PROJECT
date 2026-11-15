/**
 * Convertit le texte saisi dans un formulaire en HTML simple accepté par l'API.
 *
 * - Le texte est toujours échappé : aucune balise saisie par l'utilisateur n'est interprétée.
 * - Les blocs entre ``` deviennent <pre><code>, `code` devient <code>.
 * - Une ligne vide sépare les paragraphes ; un retour à la ligne devient <br>.
 *
 * L'API assainit de toute façon le résultat (liste blanche nh3).
 */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function inline(text: string): string {
  return escapeHtml(text).replace(/`([^`\n]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
}

export function textToHtml(text: string): string {
  const parts = text.replace(/\r\n/g, "\n").split(/```/);
  return parts
    .map((part, index) => {
      if (index % 2 === 1) {
        const code = part.replace(/^[a-z0-9+-]*\n/i, "").replace(/\n$/, "");
        return `<pre><code>${escapeHtml(code)}</code></pre>`;
      }
      return part
        .split(/\n{2,}/)
        .map((paragraph) => paragraph.trim())
        .filter(Boolean)
        .map((paragraph) => `<p>${inline(paragraph)}</p>`)
        .join("");
    })
    .join("");
}
