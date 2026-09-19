const headerSwitchers = document.querySelector(".header-switchers");

function syncHeaderVerticalSpacing() {
  const page = document.querySelector(".page");
  const brand = document.querySelector(".brand");
  const brandTop = document.querySelector(".brand-top");

  if (!page || !brand || !brandTop) return;

  // On narrow screens the header stays in normal flow. Only its final
  // two rows remain visible when the upper part scrolls out of view.
  if (window.matchMedia("(max-width: 699px)").matches && headerSwitchers) {
    brand.style.setProperty("padding-top", "0px", "important");
    brand.style.setProperty("margin-bottom", "16px", "important");
    const hiddenHeight = headerSwitchers.getBoundingClientRect().top
      - brand.getBoundingClientRect().top;
    brand.style.setProperty("top", `calc(env(safe-area-inset-top, 0px) - ${hiddenHeight}px)`, "important");
    return;
  }
  brand.style.removeProperty("top");

  const pageStyle = getComputedStyle(page);
  const brandTopStyle = getComputedStyle(brandTop);
  const pagePaddingTop = parseFloat(pageStyle.paddingTop) || 0;
  const fixedTop = parseFloat(brandTopStyle.top) || 0;
  const desiredGap = 16;

  const paddingTop = Math.max(
    0,
    fixedTop + brandTop.offsetHeight - pagePaddingTop
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