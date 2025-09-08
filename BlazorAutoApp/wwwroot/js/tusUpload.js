export async function uploadTusFromInput(inputId, fileIndex, endpoint, correlationId, chunkSizeMB = 4, dotNetRef) {
  const input = document.getElementById(inputId);
  if (!input || !input.files || input.files.length === 0) throw new Error('No files selected');
  const file = input.files[fileIndex] || input.files[0];
  const toB64 = (s) => btoa(unescape(encodeURIComponent(s || '')));
  const meta = `filename ${toB64(file.name)},contentType ${toB64(file.type || 'application/octet-stream')},correlationId ${toB64(correlationId)}`;

  const createRes = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Tus-Resumable': '1.0.0',
      'Upload-Length': String(file.size),
      'Upload-Metadata': meta
    },
    body: new Blob([])
  });
  if (createRes.status !== 201) throw new Error(`TUS create failed: ${createRes.status}`);
  let location = createRes.headers.get('Location');
  if (!location) throw new Error('No Location header returned');
  const uploadUrl = new URL(location, window.location.origin).toString();

  const chunkSize = (chunkSizeMB || 4) * 1024 * 1024;
  let offset = 0;
  while (offset < file.size) {
    const end = Math.min(offset + chunkSize, file.size);
    const slice = file.slice(offset, end);
    const patchRes = await fetch(uploadUrl, {
      method: 'PATCH',
      headers: {
        'Tus-Resumable': '1.0.0',
        'Upload-Offset': String(offset),
        'Content-Type': 'application/offset+octet-stream'
      },
      body: slice
    });
    if (patchRes.status !== 204) throw new Error(`TUS patch failed: ${patchRes.status}`);
    const head = patchRes.headers.get('Upload-Offset');
    offset = head ? parseInt(head, 10) : end;
    if (dotNetRef && dotNetRef.invokeMethodAsync) {
      try { await dotNetRef.invokeMethodAsync('ReportTusProgress', offset); } catch { /* ignore */ }
    }
  }
}

// Fetch a URL and return its bytes as a base64 string (browser-side)
export async function fetchAsBase64(url) {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) return '';
  const buf = await res.arrayBuffer();
  const bytes = new Uint8Array(buf);
  const chunk = 0x8000;
  let binary = '';
  for (let i = 0; i < bytes.length; i += chunk) {
    const slice = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode.apply(null, [...slice]);
  }
  return btoa(binary);
}

export function triggerClick(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.click();
}
