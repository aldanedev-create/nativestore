document.querySelector('#choose-folder').addEventListener('click', async () => {
  try {
    const folder = await NativeStore.native.openDialog({directory: true, multiple: false});
    document.querySelector('#folder').textContent = folder || 'No folder selected';
  } catch { document.querySelector('#folder').textContent = 'Open this app in Tauri to use the native dialog.'; }
});
