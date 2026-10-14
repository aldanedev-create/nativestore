/* Managed integrations; no inline scripts or dynamic JavaScript evaluation. */
if (window.htmx) {
  htmx.config.allowEval = false;
  htmx.config.allowScriptTags = false;
  htmx.config.historyCacheSize = 0;
  document.addEventListener("htmx:beforeSwap", event => {
    if (event.detail.xhr.status === 422) {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  });
}
document.addEventListener("alpine:init", () => {
  Alpine.data("nsDisclosure", () => ({
    open: false,
    get expanded() { return String(this.open); },
    toggle() { this.open = !this.open; },
    close() { this.open = false; }
  }));
  Alpine.data("nsDialog", () => ({
    trigger: null,
    show() { this.trigger = document.activeElement; this.$refs.dialog.showModal(); },
    close() { this.$refs.dialog.close(); },
    restore() { this.trigger?.focus(); },
    backdrop(event) { if (event.target === this.$refs.dialog) this.close(); }
  }));
  Alpine.data("nsTabs", () => ({
    selected: 0,
    get firstSelected() { return this.selected === 0; },
    get secondSelected() { return this.selected === 1; },
    get firstIndex() { return this.selected === 0 ? 0 : -1; },
    get secondIndex() { return this.selected === 1 ? 0 : -1; },
    first() { this.selected = 0; },
    second() { this.selected = 1; },
    next(event) { this.selected = 1 - this.selected; event.currentTarget.querySelectorAll('[role="tab"]')[this.selected].focus(); }
  }));
});
function nativeStoreIcons() { window.lucide?.createIcons(); }
document.addEventListener("DOMContentLoaded", nativeStoreIcons);
document.addEventListener("htmx:afterSwap", nativeStoreIcons);
