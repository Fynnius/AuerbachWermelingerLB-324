// Kopier-Knöpfe: jeder Button mit data-copy="<text>" kopiert den Text
// über die Clipboard API und zeigt kurz eine Rückmeldung an.
document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-copy]");
  if (!button) {
    return;
  }
  const label = button.dataset.label || button.textContent;
  button.dataset.label = label;
  try {
    await navigator.clipboard.writeText(button.dataset.copy);
    button.textContent = "Kopiert!";
  } catch (error) {
    button.textContent = "Fehler";
  }
  setTimeout(() => {
    button.textContent = label;
  }, 1500);
});
