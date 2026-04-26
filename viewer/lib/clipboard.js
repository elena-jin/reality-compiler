function getDocumentSelection(doc) {
  if (!doc || typeof doc.getSelection !== "function") {
    return null;
  }
  try {
    return doc.getSelection();
  } catch {
    return null;
  }
}

function preserveSelection(selection) {
  if (!selection || typeof selection.rangeCount !== "number" || typeof selection.getRangeAt !== "function") {
    return [];
  }

  const ranges = [];
  for (let index = 0; index < selection.rangeCount; index += 1) {
    try {
      ranges.push(selection.getRangeAt(index));
    } catch {
      return ranges;
    }
  }
  return ranges;
}

function restoreSelection(selection, ranges) {
  if (!selection || typeof selection.removeAllRanges !== "function" || typeof selection.addRange !== "function") {
    return;
  }
  try {
    selection.removeAllRanges();
    for (const range of ranges) {
      selection.addRange(range);
    }
  } catch {
    // Selection restoration is a courtesy; copying already happened.
  }
}

function focusElement(element) {
  if (!element || typeof element.focus !== "function") {
    return;
  }
  try {
    element.focus({ preventScroll: true });
  } catch {
    try {
      element.focus();
    } catch {
      // Ignore focus restoration failures.
    }
  }
}

function execCommandCopyText(text) {
  const doc = globalThis.document;
  if (!doc?.body || typeof doc.createElement !== "function" || typeof doc.execCommand !== "function") {
    return false;
  }

  const activeElement = doc.activeElement;
  const selection = getDocumentSelection(doc);
  const preservedRanges = preserveSelection(selection);
  const textarea = doc.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.setAttribute("aria-hidden", "true");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "-9999px";
  textarea.style.width = "1px";
  textarea.style.height = "1px";
  textarea.style.opacity = "0";

  doc.body.appendChild(textarea);
  focusElement(textarea);
  textarea.select();

  let copied = false;
  try {
    copied = doc.execCommand("copy");
  } finally {
    doc.body.removeChild(textarea);
    restoreSelection(selection, preservedRanges);
    if (activeElement && activeElement !== textarea) {
      focusElement(activeElement);
    }
  }

  return copied;
}

export async function copyTextToClipboard(text) {
  const clipboardText = String(text ?? "");
  const clipboard = globalThis.navigator?.clipboard;
  let clipboardError = null;

  if (typeof clipboard?.writeText === "function") {
    try {
      await clipboard.writeText(clipboardText);
      return;
    } catch (error) {
      clipboardError = error;
    }
  }

  if (execCommandCopyText(clipboardText)) {
    return;
  }

  if (clipboardError instanceof Error) {
    throw clipboardError;
  }
  throw new Error("Clipboard is unavailable");
}

