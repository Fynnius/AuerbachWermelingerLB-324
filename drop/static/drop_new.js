// Formular "Neuer Drop": verschlüsselt im Browser und schickt nur ciphertext + iv.
import { encrypt, exportKey, generateKey } from "./crypto.js";

const MAX_CIPHERTEXT_BYTES = 64 * 1024;
const GCM_TAG_BYTES = 16;

const form = document.getElementById("drop-form");
const textarea = document.getElementById("drop-text");
const expirySelect = document.getElementById("drop-expires-in");
const burnBox = document.getElementById("drop-burn");
const burnNote = document.getElementById("drop-burn-note");
const submitButton = form.querySelector("button[type=submit]");
const errorBox = document.getElementById("drop-error");
const result = document.getElementById("drop-result");
const linkInput = document.getElementById("drop-link");
const copyButton = document.getElementById("drop-copy");
const copyStatus = document.getElementById("drop-copy-status");
const anatomyServer = document.getElementById("drop-anatomy-server");
const anatomyKey = document.getElementById("drop-anatomy-key");

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearMessages() {
  errorBox.hidden = true;
  errorBox.textContent = "";
  copyStatus.textContent = "";
}

// Zeigt den Link zweigeteilt: was an den Server geht und was im Browser bleibt.
function showAnatomy(link) {
  const hash = link.indexOf("#");
  anatomyServer.textContent = link.slice(0, hash);
  anatomyKey.textContent = link.slice(hash);
  result.classList.add("has-anatomy");
}

async function errorMessageFor(response) {
  if (response.status === 401) {
    return "Du bist nicht mehr eingeloggt. Bitte melde dich neu an.";
  }
  try {
    const body = await response.json();
    if (body && body.error) {
      return `Der Server hat den Drop abgelehnt: ${body.error}`;
    }
  } catch {
    // keine JSON-Antwort
  }
  return `Der Drop konnte nicht gespeichert werden (HTTP ${response.status}).`;
}

// "" (Nie) wird zu null, sonst die Sekunden als Zahl.
function selectedExpiresIn() {
  return expirySelect.value === "" ? null : Number(expirySelect.value);
}

async function createDrop(text, expiresIn, burnAfterRead) {
  const key = await generateKey();
  const { ciphertext, iv } = await encrypt(text, key);

  let response;
  try {
    response = await fetch("/drops", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ciphertext,
        iv,
        expires_in: expiresIn,
        burn_after_read: burnAfterRead,
      }),
      credentials: "same-origin",
    });
  } catch {
    throw new Error("Keine Verbindung zum Server. Bitte versuche es nochmals.");
  }
  if (!response.ok) {
    throw new Error(await errorMessageFor(response));
  }
  const { url } = await response.json();
  return `${url}#${await exportKey(key)}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessages();

  const text = textarea.value;
  if (!text.trim()) {
    showError("Bitte gib zuerst einen Text ein.");
    return;
  }
  if (new TextEncoder().encode(text).length + GCM_TAG_BYTES > MAX_CIPHERTEXT_BYTES) {
    showError("Der Text ist zu lang (höchstens etwa 64 KB).");
    return;
  }

  submitButton.disabled = true;
  try {
    linkInput.value = await createDrop(text, selectedExpiresIn(), burnBox.checked);
    burnNote.hidden = !burnBox.checked;
    showAnatomy(linkInput.value);
    result.hidden = false;
    textarea.value = "";
    copyButton.focus();
  } catch (error) {
    showError(error.message || "Beim Verschlüsseln ist ein Fehler aufgetreten.");
  } finally {
    submitButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(linkInput.value);
    copyStatus.textContent = "Link kopiert.";
  } catch {
    result.classList.remove("has-anatomy");
    linkInput.select();
    copyStatus.textContent = "Kopieren nicht möglich, bitte manuell kopieren (Ctrl/Cmd+C).";
  }
});
