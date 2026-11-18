/* Aplica o tema antes da primeira pintura para evitar flash visual. */
(function () {
  var params = new URLSearchParams(window.location.search);
  var temaUrl = params.get("tema");
  var salvo = null;
  try {
    salvo = window.localStorage.getItem("biocompiler_tema");
  } catch (e) {
    salvo = null;
  }
  var tema = temaUrl === "claro" || temaUrl === "escuro"
    ? temaUrl
    : (salvo === "claro" || salvo === "escuro" ? salvo : "escuro");
  document.documentElement.setAttribute("data-tema", tema);
})();
