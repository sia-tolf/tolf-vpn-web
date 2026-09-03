function base64urlToBuffer(value) {
  const padding = "=".repeat((4 - value.length % 4) % 4);
  const base64 = (value + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);

  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }

  return bytes.buffer;
}

function bufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function prepareRegistrationOptions(options) {
  const result = {
    ...options,
    challenge: base64urlToBuffer(options.challenge),
    user: {
      ...options.user,
      id: base64urlToBuffer(options.user.id)
    }
  };

  if (Array.isArray(options.excludeCredentials)) {
    result.excludeCredentials = options.excludeCredentials.map(
      credential => ({
        ...credential,
        id: base64urlToBuffer(credential.id)
      })
    );
  }

  return result;
}

function prepareAuthenticationOptions(options) {
  const result = {
    ...options,
    challenge: base64urlToBuffer(options.challenge)
  };

  if (Array.isArray(options.allowCredentials)) {
    result.allowCredentials = options.allowCredentials.map(
      credential => ({
        ...credential,
        id: base64urlToBuffer(credential.id)
      })
    );
  }

  return result;
}

function serializeCredential(credential) {
  const response = credential.response;

  const serialized = {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment || null,
    clientExtensionResults: credential.getClientExtensionResults()
  };

  if (
    typeof AuthenticatorAttestationResponse !== "undefined" &&
    response instanceof AuthenticatorAttestationResponse
  ) {
    serialized.response = {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
      transports:
        typeof response.getTransports === "function"
          ? response.getTransports()
          : []
    };

    return serialized;
  }

  serialized.response = {
    clientDataJSON: bufferToBase64url(response.clientDataJSON),
    authenticatorData: bufferToBase64url(response.authenticatorData),
    signature: bufferToBase64url(response.signature),
    userHandle: response.userHandle
      ? bufferToBase64url(response.userHandle)
      : null
  };

  return serialized;
}
