/*
 * AfriDev — animations de l'administration (aucune dépendance).
 * Fond aurora, page de connexion avec carte de l'Afrique, apparitions en cascade,
 * halo qui suit le curseur, onde au clic et indicateurs animés du tableau de bord.
 */
(function () {
  "use strict";

  // Les images (carte, logo) sont des fonds CSS : leurs URL hachées sont réécrites par collectstatic.
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Le thème est toujours sombre, comme le site public.
  document.documentElement.setAttribute("data-bs-theme", "dark");
  try {
    localStorage.setItem("jazzmin-theme-mode", "dark");
  } catch (error) {
    /* stockage indisponible : sans conséquence */
  }

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
    });
  }

  /** Titre révélé mot par mot (chaque mot glisse hors d'un masque). */
  function kinetic(text) {
    return text
      .split(" ")
      .map(function (word, index) {
        return '<span class="afd-word"><span style="--i:' + index + '">' + escapeHtml(word) + "</span></span>";
      })
      .join(" ");
  }

  function addAurora() {
    var aurora = el("div", "afd-aurora", "<span></span><span></span><span></span>");
    aurora.setAttribute("aria-hidden", "true");
    document.body.prepend(aurora);
  }

  function buildLogin() {
    if (!document.body.classList.contains("login-page")) return;
    var points = [
      ["fa-shield-halved", "Modération des signalements et journal d'audit"],
      ["fa-users", "Gestion des membres, rôles et profils"],
      ["fa-diagram-project", "Suivi des projets, opportunités et événements"],
    ];
    var hero = el(
      "aside",
      "afd-login-hero",
      '<div class="afd-login-hero__map" aria-hidden="true"></div>' +
        '<div class="afd-login-hero__brand"><span class="afd-logo-mark" aria-hidden="true"></span>AfriDev<span style="color:#fbbf24">.</span></div>' +
        "<h1>" + kinetic("Échanger. Se connecter.") + ' <span class="afd-gradient-text">' + kinetic("Construire.") + "</span></h1>" +
        '<p style="color:var(--afd-muted);max-width:26rem;position:relative">Administration de la communauté des développeurs africains.</p>' +
        "<ul>" +
        points
          .map(function (point, index) {
            return '<li style="--i:' + index + '"><i class="fas ' + point[0] + '"></i>' + escapeHtml(point[1]) + "</li>";
          })
          .join("") +
        "</ul>"
    );
    document.body.prepend(hero);
  }

  /** Apparitions en cascade : chaque élément reçoit son rang dans --i. */
  function stagger(selector, limit) {
    var nodes = document.querySelectorAll(selector);
    for (var index = 0; index < nodes.length && index < limit; index += 1) {
      nodes[index].style.setProperty("--i", String(index));
    }
  }

  /** Halo radial qui suit le curseur sur les cartes. */
  function spotlight() {
    document.addEventListener("pointermove", function (event) {
      var card = event.target.closest && event.target.closest(".card, .afd-kpi");
      if (!card) return;
      var box = card.getBoundingClientRect();
      card.style.setProperty("--mx", event.clientX - box.left + "px");
      card.style.setProperty("--my", event.clientY - box.top + "px");
    });
  }

  /** Onde au clic sur les boutons. */
  function ripple() {
    document.addEventListener("pointerdown", function (event) {
      var button = event.target.closest && event.target.closest(".btn");
      if (!button || reduced) return;
      var box = button.getBoundingClientRect();
      var size = Math.max(box.width, box.height);
      var wave = el("span", "afd-ripple");
      wave.style.width = wave.style.height = size + "px";
      wave.style.left = event.clientX - box.left - size / 2 + "px";
      wave.style.top = event.clientY - box.top - size / 2 + "px";
      button.appendChild(wave);
      window.setTimeout(function () {
        wave.remove();
      }, 650);
    });
  }

  /** Compteur qui monte jusqu'à sa valeur (décélération exponentielle). */
  function countUp(node, target) {
    if (reduced || target === 0) {
      node.textContent = target.toLocaleString("fr-FR");
      return;
    }
    var duration = 1400;
    var start = null;
    function frame(time) {
      if (start === null) start = time;
      var progress = Math.min(1, (time - start) / duration);
      var eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      node.textContent = Math.round(target * eased).toLocaleString("fr-FR");
      if (progress < 1) window.requestAnimationFrame(frame);
    }
    window.setTimeout(function () {
      window.requestAnimationFrame(frame);
    }, 350);
  }

  /** Courbe d'activité sur 14 jours, tracée progressivement. */
  function sparkline(values, color, id) {
    var width = 300;
    var height = 70;
    var max = Math.max.apply(null, values.concat([1]));
    var step = width / Math.max(values.length - 1, 1);
    var points = values.map(function (value, index) {
      return [index * step, height - 6 - (value / max) * (height - 12)];
    });
    var line = points
      .map(function (point, index) {
        return (index ? "L" : "M") + point[0].toFixed(1) + " " + point[1].toFixed(1);
      })
      .join(" ");
    var area = line + " L" + width + " " + height + " L0 " + height + " Z";
    return (
      '<svg viewBox="0 0 ' + width + " " + height + '" preserveAspectRatio="none" aria-hidden="true">' +
      '<defs><linearGradient id="' + id + '" x1="0" x2="0" y1="0" y2="1">' +
      '<stop offset="0" stop-color="' + color + '" stop-opacity=".35"/><stop offset="1" stop-color="' + color + '" stop-opacity="0"/>' +
      "</linearGradient></defs>" +
      '<path class="area" d="' + area + '" fill="url(#' + id + ')"/>' +
      '<path class="line" d="' + line + '" stroke="' + color + '" style="--len:' + Math.ceil(width * 2) + '"/>' +
      "</svg>"
    );
  }

  var LINKS = {
    members: "accounts/user/",
    posts: "community/post/",
    projects: "projects/project/",
    reports: "moderation/report/?status__exact=PENDING",
    opportunities: "opportunities/opportunity/?status__exact=PENDING_REVIEW",
    events: "events/event/",
  };

  function buildDashboard() {
    if (!document.body.classList.contains("dashboard")) return;
    var container = document.querySelector(".app-content .container-fluid");
    var logo = document.getElementById("jazzy-logo");
    if (!container || !logo) return;
    var adminRoot = logo.getAttribute("href") || "/admin/";
    var user = document.querySelector(".user-panel .info");
    var name = user ? user.textContent.trim() : "";

    var hero = el(
      "section",
      "afd-hero",
      '<div class="afd-hero__eyebrow">Tableau de bord</div>' +
        '<h2 class="afd-hero__title">' + kinetic("Bonjour" + (name ? " " + name : "")) + ' <span class="afd-gradient-text">✦</span></h2>' +
        '<p class="afd-hero__subtitle">Vue d\'ensemble de la communauté AfriDev en temps réel.</p>' +
        '<div class="afd-kpis" aria-live="polite"></div><div class="afd-activity"></div>'
    );
    container.prepend(hero);

    fetch(adminRoot + "afridev-stats/", { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
      })
      .then(function (data) {
        var grid = hero.querySelector(".afd-kpis");
        data.kpis.forEach(function (kpi, index) {
          var classes = "afd-kpi" + (kpi.alert ? " afd-kpi--alert" : "") + (kpi.alert && kpi.value > 0 ? " afd-kpi--hot" : "");
          var card = el(
            "a",
            classes,
            '<span class="afd-kpi__icon"><i class="fas ' + kpi.icon + '"></i></span>' +
              '<div class="afd-kpi__value">0</div><div class="afd-kpi__label">' + escapeHtml(kpi.label) + "</div>"
          );
          card.href = adminRoot + (LINKS[kpi.key] || "");
          card.style.setProperty("--i", String(index));
          grid.appendChild(card);
          countUp(card.querySelector(".afd-kpi__value"), kpi.value);
        });

        var activity = hero.querySelector(".afd-activity");
        var series = [
          ["Nouveaux membres", data.activity.members, "#34d399"],
          ["Publications", data.activity.posts, "#fbbf24"],
        ];
        series.forEach(function (serie, index) {
          var total = serie[1].reduce(function (sum, value) {
            return sum + value;
          }, 0);
          activity.appendChild(
            el(
              "div",
              "afd-spark",
              '<div class="afd-spark__head"><span>' + serie[0] + " · " + data.activity.days + " derniers jours</span><strong>" + total + "</strong></div>" +
                sparkline(serie[1], serie[2], "afd-spark-" + index)
            )
          );
        });
      })
      .catch(function () {
        hero.querySelector(".afd-kpis").innerHTML = '<p class="afd-hero__subtitle">Indicateurs indisponibles pour le moment.</p>';
      });
  }

  function init() {
    addAurora();
    buildLogin();
    buildDashboard();
    stagger(".sidebar-menu > .nav-item, .sidebar-menu > .nav-header", 60);
    stagger(".app-content .card", 30);
    stagger("#result_list tbody tr", 40);
    document.body.classList.add("afd-ready");
    spotlight();
    ripple();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
