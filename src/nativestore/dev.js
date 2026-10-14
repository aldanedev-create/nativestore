(async () => {
  const panel = document.querySelector('#diagnostics');
  let previous;
  async function poll() {
    try {
      if (panel) {
        const response = await fetch('/__nativestore/dev/data');
        if (response.ok) panel.textContent = JSON.stringify(await response.json(), null, 2);
      } else {
        const response = await fetch('/__nativestore/dev/revision');
        if (!response.ok) return;
        const next = await response.json();
        if (previous && (previous.templates !== next.templates || previous.scripts !== next.scripts)) location.reload();
        else if (previous && previous.styles !== next.styles) {
          for (const link of document.querySelectorAll('link[rel="stylesheet"]')) {
            const url = new URL(link.href); url.searchParams.set('ns-reload', next.styles); link.href = url.href;
          }
          console.info('NativeStore: styles refreshed');
        }
        previous = next;
      }
    } catch { /* Python restarts can temporarily interrupt polling. */ }
  }
  await poll();
  setInterval(poll, 1000);
})();
