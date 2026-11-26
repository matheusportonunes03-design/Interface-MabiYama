/* Monta o Replay da frota sozinho (aba Máquinas) e ajusta a altura do iframe ao conteúdo. */
ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(window.Replay));
function ajustarAltura() {
  const f = window.frameElement;
  if (!f) return;
  const h = Math.ceil(document.getElementById("root").getBoundingClientRect().height) + 4;
  f.style.height = h + "px"; f.setAttribute("height", h);
  if (f.parentElement) f.parentElement.style.height = h + "px";
}
new ResizeObserver(ajustarAltura).observe(document.getElementById("root"));
window.addEventListener("load", ajustarAltura);
setTimeout(ajustarAltura, 300);
