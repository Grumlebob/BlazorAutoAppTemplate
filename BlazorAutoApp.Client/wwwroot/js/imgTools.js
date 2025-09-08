export function triggerClick(id) {
  const el = document.getElementById(id);
  if (el) el.click();
}

export async function validateImageFromInput(inputId) {
  const input = document.getElementById(inputId);
  if (!input || !input.files || input.files.length === 0) {
    return { ok: false, error: 'No file selected' };
  }
  const file = input.files[0];
  const url = URL.createObjectURL(file);
  try {
    const dims = await decodeImage(url);
    return {
      ok: true,
      width: dims.width,
      height: dims.height,
      type: file.type || null,
      name: file.name || null,
      size: file.size ?? 0,
      error: null
    };
  } catch (e) {
    return { ok: false, error: (e && e.message) ? e.message : 'Decode failed' };
  } finally {
    URL.revokeObjectURL(url);
  }
}

function decodeImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => reject(new Error('Browser failed to decode image'));
    img.src = url;
  });
}

