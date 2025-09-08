// Session-based TUS upload with pause/resume support and auto-resume
const tusSessions = new Map();

function toB64(s) { return btoa(unescape(encodeURIComponent(s || ''))); }

export async function startTusUploadFromInput(sessionId, inputId, fileIndex, endpoint, correlationId, chunkSizeMB = 4, dotNetRef) {
  if (!sessionId) throw new Error('Missing sessionId');
  const input = document.getElementById(inputId);
  if (!input || !input.files || input.files.length === 0) throw new Error('No files selected');
  const file = input.files[fileIndex] || input.files[0];

  // Notify total size to .NET side for progress UI
  if (dotNetRef && dotNetRef.invokeMethodAsync) {
    try { await dotNetRef.invokeMethodAsync('OnTusInit', file.size); } catch { /* ignore */ }
  }

  // Create or reuse session context
  let ctx = tusSessions.get(sessionId);
  if (!ctx) {
    // Create
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
    ctx = {
      file,
      uploadUrl,
      offset: 0,
      chunkSize: (chunkSizeMB || 4) * 1024 * 1024,
      paused: false,
      userPaused: false,
      autoPaused: false,
      dotNetRef,
      controller: null,
      onlineHandler: null,
      retryTimer: null
    };
    tusSessions.set(sessionId, ctx);
  }

  // Run the loop until paused or complete
  await runTusLoop(sessionId);
}

export async function startTusUploadFromUrl(sessionId, url, fileName, contentType, endpoint, correlationId, chunkSizeMB = 4, dotNetRef) {
  if (!sessionId) throw new Error('Missing sessionId');
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  const blob = await res.blob();
  // Polyfill a minimal File-like object; Blob already has slice() and size
  const file = blob;

  // Notify total size to .NET side for progress UI
  if (dotNetRef && dotNetRef.invokeMethodAsync) {
    try { await dotNetRef.invokeMethodAsync('OnTusInit', file.size); } catch { /* ignore */ }
  }

  let ctx = tusSessions.get(sessionId);
  if (!ctx) {
    const meta = `filename ${toB64(fileName || 'download.bin')},contentType ${toB64(contentType || 'application/octet-stream')},correlationId ${toB64(correlationId)}`;
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
    ctx = {
      file,
      uploadUrl,
      offset: 0,
      chunkSize: (chunkSizeMB || 4) * 1024 * 1024,
      paused: false,
      userPaused: false,
      autoPaused: false,
      dotNetRef,
      controller: null,
      onlineHandler: null,
      retryTimer: null
    };
    tusSessions.set(sessionId, ctx);
  }
  await runTusLoop(sessionId);
}

async function runTusLoop(sessionId) {
  const ctx = tusSessions.get(sessionId);
  if (!ctx) return;
  const { file, uploadUrl, chunkSize, dotNetRef } = ctx;
  // Sync local offset with server in case of pause/resume or last chunk uncertainty
  try {
    const head = await fetch(uploadUrl, { method: 'HEAD', headers: { 'Tus-Resumable': '1.0.0' } });
    if (head.ok) {
      const off = head.headers.get('Upload-Offset');
      if (off) {
        const parsed = parseInt(off, 10);
        if (!Number.isNaN(parsed)) ctx.offset = parsed;
      }
    }
  } catch { /* ignore HEAD sync errors; continue with local offset */ }
  while (ctx.offset < file.size && !ctx.paused) {
    const end = Math.min(ctx.offset + chunkSize, file.size);
    const slice = file.slice(ctx.offset, end);
    ctx.controller = new AbortController();
    let patchRes;
    try {
      patchRes = await fetch(uploadUrl, {
        method: 'PATCH',
        headers: {
          'Tus-Resumable': '1.0.0',
          'Upload-Offset': String(ctx.offset),
          'Content-Type': 'application/offset+octet-stream'
        },
        body: slice,
        signal: ctx.controller.signal
      });
    } catch (e) {
      if (ctx.paused) return; // Expected cancel
      await autoPause(sessionId, `network error: ${e && e.message ? e.message : 'fetch failed'}`);
      return;
    }
    if (patchRes.status !== 204) {
      await autoPause(sessionId, `server status ${patchRes.status}`);
      return;
    }
    const head = patchRes.headers.get('Upload-Offset');
    ctx.offset = head ? parseInt(head, 10) : end;
    if (dotNetRef && dotNetRef.invokeMethodAsync) {
      try { await dotNetRef.invokeMethodAsync('ReportTusProgress', ctx.offset); } catch { /* ignore */ }
    }
  }
  if (!ctx.paused && ctx.offset >= file.size && ctx.dotNetRef && ctx.dotNetRef.invokeMethodAsync) {
    try { await ctx.dotNetRef.invokeMethodAsync('OnTusCompleted'); } catch { /* ignore */ }
    cleanup(sessionId);
  }
}

export function pauseTusUpload(sessionId) {
  const ctx = tusSessions.get(sessionId);
  if (!ctx) return;
  ctx.paused = true;
  ctx.userPaused = true;
  if (ctx.controller) {
    try { ctx.controller.abort(); } catch { /* ignore */ }
  }
}

export async function resumeTusUpload(sessionId) {
  const ctx = tusSessions.get(sessionId);
  if (!ctx) return;
  if (!ctx.paused) return;
  ctx.paused = false;
  ctx.userPaused = false;
  ctx.autoPaused = false;
  // Re-sync offset with server before resuming
  try {
    const head = await fetch(ctx.uploadUrl, { method: 'HEAD', headers: { 'Tus-Resumable': '1.0.0' } });
    if (head.ok) {
      const off = head.headers.get('Upload-Offset');
      if (off) {
        const parsed = parseInt(off, 10);
        if (!Number.isNaN(parsed)) ctx.offset = parsed;
      }
    }
  } catch { /* ignore */ }
  // Notify .NET that we are resuming (auto or manual)
  if (ctx.dotNetRef && ctx.dotNetRef.invokeMethodAsync) {
    try { await ctx.dotNetRef.invokeMethodAsync('OnTusResumed'); } catch { /* ignore */ }
  }
  await runTusLoop(sessionId);
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

async function autoPause(sessionId, reason) {
  const ctx = tusSessions.get(sessionId);
  if (!ctx) return;
  if (ctx.userPaused) return; // don't override explicit user pause
  ctx.paused = true;
  ctx.autoPaused = true;
  if (ctx.controller) {
    try { ctx.controller.abort(); } catch { /* ignore */ }
  }
  // Inform .NET side to show Resume button
  if (ctx.dotNetRef && ctx.dotNetRef.invokeMethodAsync) {
    try { await ctx.dotNetRef.invokeMethodAsync('OnTusAutoPaused', String(reason || 'stalled')); } catch { /* ignore */ }
  }
  // Setup auto-resume when browser reports back online
  if (!ctx.onlineHandler) {
    ctx.onlineHandler = async () => {
      const latest = tusSessions.get(sessionId);
      if (!latest || latest.userPaused) return; // do not auto-resume if user paused
      // small delay to allow network to settle
      setTimeout(() => resumeTusUpload(sessionId), 250);
    };
    try { window.addEventListener('online', ctx.onlineHandler); } catch { /* ignore */ }
  }
  // Also set a periodic retry (in case 'online' doesn't fire correctly)
  if (!ctx.retryTimer) {
    ctx.retryTimer = setInterval(async () => {
      const latest = tusSessions.get(sessionId);
      if (!latest || latest.userPaused || !latest.paused) return;
      try {
        const head = await fetch(latest.uploadUrl, { method: 'HEAD', headers: { 'Tus-Resumable': '1.0.0' } });
        if (head.ok) {
          clearInterval(latest.retryTimer);
          latest.retryTimer = null;
          resumeTusUpload(sessionId);
        }
      } catch {
        // still offline or server unreachable; keep waiting
      }
    }, 3000);
  }
}

function cleanup(sessionId) {
  const ctx = tusSessions.get(sessionId);
  if (!ctx) return;
  if (ctx.retryTimer) {
    try { clearInterval(ctx.retryTimer); } catch { /* ignore */ }
    ctx.retryTimer = null;
  }
  if (ctx.onlineHandler) {
    try { window.removeEventListener('online', ctx.onlineHandler); } catch { /* ignore */ }
    ctx.onlineHandler = null;
  }
}
