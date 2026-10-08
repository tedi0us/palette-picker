/* Palette Picker — the only hand-written JS.
   Everything stateful goes through HTMX; this covers the few things the
   platform can't: clipboard, a modal toggle, keyboard undo/redo, toasts. */

(function () {
  "use strict";

  // ---- submit modal ---------------------------------------------------
  window.ppOpenSubmit = function () {
    var m = document.getElementById("submit-modal");
    if (m) { m.hidden = false; var i = m.querySelector("input[name=client]"); if (i) i.focus(); }
  };
  window.ppCloseSubmit = function () {
    var m = document.getElementById("submit-modal");
    if (m) m.hidden = true;
  };

  // ---- toasts -------------------------------------------------------
  function toast(msg, kind) {
    var stack = document.getElementById("toasts");
    if (!stack) return;
    var el = document.createElement("div");
    el.className = "toast" + (kind ? " " + kind : "");
    el.textContent = msg;
    stack.appendChild(el);
    setTimeout(function () { el.style.transition = "opacity .3s"; el.style.opacity = "0"; }, 2200);
    setTimeout(function () { el.remove(); }, 2600);
  }
  window.ppToast = toast;

  // ---- clipboard: any [data-copy="#selector"] -----------------------
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy]");
    if (!btn) return;
    var target = document.querySelector(btn.getAttribute("data-copy"));
    if (!target) return;
    var text = target.value !== undefined && target.value !== "" ? target.value : target.textContent;
    navigator.clipboard.writeText(text).then(
      function () { toast("Copied to clipboard", "good"); },
      function () { toast("Copy failed — select the text manually", "bad"); }
    );
  });

  // ---- keyboard undo / redo --------------------------------------------
  document.addEventListener("keydown", function (e) {
    var mod = e.ctrlKey || e.metaKey;
    if (!mod || e.key.toLowerCase() !== "z") return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    e.preventDefault();
    var sel = e.shiftKey ? '[hx-post="/redo"]' : '[hx-post="/undo"]';
    var b = document.querySelector(sel);
    if (b && !b.disabled) b.click();
  });

  // ---- htmx feedback ------------------------------------------------
  document.body.addEventListener("htmx:responseError", function () {
    toast("Something went wrong — try again", "bad");
  });
  document.body.addEventListener("htmx:sendError", function () {
    toast("Lost connection to the server", "bad");
  });
})();
