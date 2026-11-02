// Drop anzeigen: Schlüssel aus dem #-Teil lesen, Daten holen, im Browser entschlüsseln.
import { decrypt, importKey } from "./crypto.js";

const container = document.getElementById("drop");
const statusLine = document.getElementById("drop-status");
const errorBox = document.getElementById("drop-error");
const output = document.getElementById("drop-text");

function showError(message) {
  statusLine.hidden = true;
  errorBox.textContent = message;
  errorBox.hidden = false;
}

async function loadKey(fragment) {
  try {
    return await importKey(fragment);
  } catch {
    throw new Error("Link ungültig: Der Schlüssel im Link ist beschädigt.");
  }
}

async function loadData(slug) {
  let response;
  try {
    response = await fetch(`/d/${encodeURIComponent(slug)}/data`);
  } catch {
    throw new Error("Keine Verbindung zum Server. Bitte lade die Seite neu.");
  }
  if (response.status === 410) {
    throw new Error("Dieser Drop ist abgelaufen.");
  }
  if (response.status === 404) {
    throw new Error("Diesen Drop gibt es nicht (mehr).");
  }
  if (!response.ok) {
    throw new Error(`Der Drop konnte nicht geladen werden (HTTP ${response.status}).`);
  }
  return response.json();
}

async function show() {
  const fragment = location.hash.slice(1);
  if (!fragment) {
    showError("Link unvollständig: Schlüssel fehlt");
    return;
  }
  try {
    const key = await loadKey(fragment);
    const data = await loadData(container.dataset.slug);
    let text;
    try {
      text = await decrypt(data, key);
    } catch {
      throw new Error("Entschlüsseln fehlgeschlagen: Der Schlüssel im Link passt nicht.");
    }
    output.textContent = text;
    output.hidden = false;
    statusLine.hidden = true;
  } catch (error) {
    showError(error.message);
  }
}

show();
