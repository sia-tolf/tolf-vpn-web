async function apiRequest(path, options = {}) {
  const { timeoutMs = 0, ...requestOptions } = options;
  if (timeoutMs > 0) {
    const controller = new AbortController();
    let timer;
    try {
      return await Promise.race([
        apiRequest(path, { ...requestOptions, signal: controller.signal }),
        new Promise((_, reject) => {
          timer = setTimeout(() => {
            reject(new Error("Request timed out"));
            controller.abort();
          }, timeoutMs);
        })
      ]);
    } finally {
      clearTimeout(timer);
    }
  }
  const response = await fetch(API + path, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.detail || "Request failed");
    error.status = response.status;
    throw error;
  }

  return data;
}

async function copyText(value) {
  if (
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");

  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";

  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}
