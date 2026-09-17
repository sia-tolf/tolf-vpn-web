const headerSwitchers = document.querySelector(".header-switchers");

if (headerSwitchers && !document.getElementById("protocolSelector")) {
  const controlsCluster = document.createElement("div");
  controlsCluster.className = "header-control-cluster";

  const protocolSelector = document.createElement("div");
  protocolSelector.id = "protocolSelector";
  protocolSelector.className = "protocol-selector";
  protocolSelector.setAttribute("aria-label", "IKEv2 selected");

  const protocolLabel = document.createElement("span");
  protocolLabel.className = "protocol-label";
  protocolLabel.textContent = "IKEv2";

  const protocolColumn = document.createElement("span");
  protocolColumn.className = "protocol-column";
  protocolColumn.setAttribute("aria-hidden", "true");

  const activeDot = document.createElement("span");
  activeDot.className = "protocol-dot protocol-dot-active";

  const middleDot = document.createElement("span");
  middleDot.className = "protocol-dot protocol-dot-reserve";

  const reserveDot = document.createElement("span");
  reserveDot.className = "protocol-dot protocol-dot-reserve";

  protocolColumn.append(activeDot, middleDot, reserveDot);
  protocolSelector.append(protocolLabel, protocolColumn);

  headerSwitchers.parentNode.insertBefore(controlsCluster, headerSwitchers);
  controlsCluster.append(protocolSelector, headerSwitchers);

  const protocolStyle = document.createElement("style");
  protocolStyle.textContent = `
    .brand-copy::after {
      content: none !important;
      display: none !important;
    }

    .brand {
      padding-top: 0 !important;
      margin-bottom: 20px !important;
    }

    .brand-copy {
      display: block !important;
    }

    .brand-home-link {
      color: inherit;
      text-decoration: none;
      cursor: pointer;
    }

    .brand-home-link:focus-visible {
      outline: 2px solid var(--text);
      outline-offset: 3px;
      border-radius: 4px;
    }

    .brand-top {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      transform: none !important;
      z-index: 60 !important;
      width: 100% !important;
      min-height: 0 !important;
      box-sizing: border-box;
      padding-top: max(10px, env(safe-area-inset-top)) !important;
      padding-bottom: 10px !important;
      padding-left: max(24px, calc((100vw - 712px) / 2)) !important;
      padding-right: max(24px, calc((100vw - 712px) / 2)) !important;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      background: color-mix(in srgb, var(--background) 90%, transparent) !important;
      border: 0 !important;
      border-bottom: 1px solid var(--border) !important;
      border-radius: 0 !important;
      backdrop-filter: saturate(180%) blur(20px) !important;
      -webkit-backdrop-filter: saturate(180%) blur(20px) !important;
      box-shadow: none !important;
    }

    .header-control-cluster {
      min-width: 0;
      margin-left: auto;
      display: flex;
      align-items: stretch;
      justify-content: flex-end;
      gap: 12px;
    }

    .header-control-cluster .header-switchers,
    .header-control-cluster .header-switchers.three-platform-switchers {
      flex: 0 0 336px;
      width: 336px;
    }

    .protocol-selector {
      flex: 0 0 auto;
      display: grid;
      grid-template-columns: auto 28px;
      align-items: stretch;
      gap: 8px;
      color: var(--text);
      user-select: none;
      -webkit-user-select: none;
    }

    .protocol-label {
      align-self: start;
      margin-top: 8px;
      font-size: 13px;
      line-height: 12px;
      font-weight: 600;
      white-space: nowrap;
    }

    .protocol-column {
      width: 28px;
      height: auto;
      min-height: 100%;
      box-sizing: border-box;
      padding: 8px 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
    }

    .protocol-dot {
      width: 12px;
      height: 12px;
      box-sizing: border-box;
      display: block;
      border-radius: 50%;
    }

    .protocol-dot-active {
      background: var(--success);
      border: 1px solid color-mix(in srgb, var(--success) 76%, #1d1d1f 24%);
    }

    .protocol-dot-reserve {
      background: #ffffff;
      border: 1px solid var(--border);
    }

    @media (max-width: 759px) {
      .brand-top {
        padding-left: 24px !important;
        padding-right: 24px !important;
      }

      .header-control-cluster .header-switchers,
      .header-control-cluster .header-switchers.three-platform-switchers {
        flex-basis: 300px;
        width: 300px;
      }
    }

    @media (max-width: 520px) {
      .brand-top {
        padding-top: max(8px, env(safe-area-inset-top)) !important;
        padding-bottom: 8px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
      }

      .header-control-cluster {
        width: 100%;
        margin-left: 0;
        gap: 8px;
      }

      .header-control-cluster .header-switchers,
      .header-control-cluster .header-switchers.three-platform-switchers {
        flex: 1 1 auto;
        width: auto;
        min-width: 0;
      }

      .protocol-selector {
        grid-template-columns: auto 26px;
        gap: 6px;
      }

      .protocol-label {
        margin-top: 8px;
        font-size: 12px;
        line-height: 12px;
      }

      .protocol-column {
        width: 26px;
        height: auto;
        min-height: 100%;
      }
    }
  `;
  document.head.appendChild(protocolStyle);
}

const brandHeading = document.querySelector(".brand-copy h1");
if (brandHeading && !brandHeading.closest("a")) {
  const brandHomeLink = document.createElement("a");
  brandHomeLink.className = "brand-home-link";
  brandHomeLink.href = "https://tolf.is";
  brandHomeLink.setAttribute("aria-label", "TOLF home");
  brandHeading.replaceWith(brandHomeLink);
  brandHomeLink.appendChild(brandHeading);
}

function syncHeaderVerticalSpacing() {
  const page = document.querySelector(".page");
  const brand = document.querySelector(".brand");
  const brandTop = document.querySelector(".brand-top");

  if (!page || !brand || !brandTop) return;

  const pageStyle = getComputedStyle(page);
  const brandTopStyle = getComputedStyle(brandTop);
  const pagePaddingTop = parseFloat(pageStyle.paddingTop) || 0;
  const fixedTop = parseFloat(brandTopStyle.top) || 0;
  const desiredGap = 20;

  const paddingTop = Math.max(
    0,
    fixedTop + brandTop.offsetHeight + desiredGap - pagePaddingTop
  );

  brand.style.setProperty("padding-top", `${paddingTop}px`, "important");
  brand.style.setProperty("margin-bottom", `${desiredGap}px`, "important");
}

requestAnimationFrame(syncHeaderVerticalSpacing);
window.addEventListener("resize", syncHeaderVerticalSpacing);
if (typeof ResizeObserver === "function") {
  const brandTop = document.querySelector(".brand-top");
  if (brandTop) {
    new ResizeObserver(syncHeaderVerticalSpacing).observe(brandTop);
  }
}

languageEn.addEventListener(
  "click",
  () => setLanguage("en")
);

languageRu.addEventListener(
  "click",
  () => setLanguage("ru")
);

languageLv.addEventListener(
  "click",
  () => setLanguage("lv")
);

document
  .getElementById("profileQrButton")
  ?.classList.replace("secondary", "constructive");

let promoFocusAllowed = false;

function allowPromoFocusFromUser() {
  promoFocusAllowed = true;
}

promoInput.addEventListener("pointerdown", allowPromoFocusFromUser, true);
redeemPromoButton.addEventListener("pointerdown", allowPromoFocusFromUser, true);
window.addEventListener("keydown", event => {
  if (event.key === "Tab") promoFocusAllowed = true;
}, true);

promoInput.addEventListener("focus", () => {
  if (!promoFocusAllowed) {
    promoInput.blur();
    return;
  }
  promoFocusAllowed = false;
}, true);

function clearRestoredPromoFocus() {
  if (document.activeElement === promoInput && !promoFocusAllowed) {
    promoInput.blur();
  }
}

window.addEventListener("pageshow", () => {
  clearRestoredPromoFocus();
  requestAnimationFrame(clearRestoredPromoFocus);
  setTimeout(clearRestoredPromoFocus, 100);
  setTimeout(clearRestoredPromoFocus, 500);
  requestAnimationFrame(syncHeaderVerticalSpacing);
});

setLanguage(currentLanguage);
loadAccount();