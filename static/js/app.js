// Theme toggle: explicit choice is stored; otherwise the OS setting applies.
(function () {
  const root = document.documentElement;
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const current = () => root.dataset.theme || (media.matches ? "dark" : "light");
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-theme-toggle]");
    if (!button) return;
    const next = current() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) { /* private mode */ }
  });
  // Close the account menu when clicking elsewhere or pressing Escape.
  document.addEventListener("click", (event) => {
    document.querySelectorAll("details.menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll("details.menu[open]").forEach((menu) => {
      menu.removeAttribute("open");
      menu.querySelector("summary").focus();
    });
  });
})();
