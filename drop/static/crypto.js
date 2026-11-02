// Verschlüsselung im Browser mit der Web Crypto API (AES-GCM, 256 Bit).
// Der Schlüssel verlässt den Browser nur im #-Teil des Links, nie Richtung Server.

const ALGORITHM = "AES-GCM";
const IV_BYTES = 12;

function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function toBase64Url(base64) {
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(base64url) {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  return base64 + "=".repeat((4 - (base64.length % 4)) % 4);
}

export function generateKey() {
  return crypto.subtle.generateKey({ name: ALGORITHM, length: 256 }, true, [
    "encrypt",
    "decrypt",
  ]);
}

export async function encrypt(text, key) {
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const encoded = new TextEncoder().encode(text);
  const ciphertext = await crypto.subtle.encrypt({ name: ALGORITHM, iv }, key, encoded);
  return {
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
    iv: bytesToBase64(iv),
  };
}

export async function decrypt({ ciphertext, iv }, key) {
  const plain = await crypto.subtle.decrypt(
    { name: ALGORITHM, iv: base64ToBytes(iv) },
    key,
    base64ToBytes(ciphertext),
  );
  return new TextDecoder().decode(plain);
}

export async function exportKey(key) {
  const raw = await crypto.subtle.exportKey("raw", key);
  return toBase64Url(bytesToBase64(new Uint8Array(raw)));
}

export function importKey(str) {
  const raw = base64ToBytes(fromBase64Url(str));
  return crypto.subtle.importKey("raw", raw, { name: ALGORITHM }, false, [
    "decrypt",
  ]);
}
