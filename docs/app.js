(() => {
  const API_BASE = window.DRUMSEP_API_BASE_URL.replace(/\/$/, "");

  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const submitBtn = document.getElementById("submit-btn");
  const statusEl = document.getElementById("status");
  const progressEl = document.getElementById("progress");
  const resultsEl = document.getElementById("results");

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function setBusy(busy) {
    submitBtn.disabled = busy;
    fileInput.disabled = busy;
    progressEl.hidden = !busy;
  }

  async function requestUploadUrl(file) {
    const res = await fetch(`${API_BASE}/v1/uploads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content_type: file.type }),
    });
    if (!res.ok) {
      throw new Error(`no se pudo obtener la URL de subida (${res.status})`);
    }
    return res.json();
  }

  async function uploadDirectToGcs(uploadUrl, file) {
    const res = await fetch(uploadUrl, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!res.ok) {
      throw new Error(`falló la subida a GCS (${res.status})`);
    }
  }

  async function requestProcessing(trackId, objectName) {
    const res = await fetch(`${API_BASE}/v1/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_id: trackId, object_name: objectName }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `falló el procesamiento (${res.status})`);
    }
    return res.json();
  }

  function renderStems(stems) {
    resultsEl.innerHTML = "";
    for (const stem of stems) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = stem.download_url;
      a.textContent = `Descargar ${stem.name}`;
      a.download = stem.name;
      li.appendChild(a);
      resultsEl.appendChild(li);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    resultsEl.innerHTML = "";
    setBusy(true);
    try {
      setStatus("Solicitando URL de subida...");
      const { track_id, object_name, upload_url } = await requestUploadUrl(file);

      setStatus("Subiendo archivo...");
      await uploadDirectToGcs(upload_url, file);

      setStatus("Separando stems (esto puede tardar unos minutos)...");
      const { stems } = await requestProcessing(track_id, object_name);

      setStatus("¡Listo! Los links de descarga vencen en 24hs.");
      renderStems(stems);
    } catch (err) {
      console.error(err);
      setStatus(`Error: ${err.message}`);
    } finally {
      setBusy(false);
    }
  });
})();
