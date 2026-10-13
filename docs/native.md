# Native APIs and Tauri permissions

NativeStore uses Tauri's own plugins and capability system. Enable only the features
needed by the application:

```toml
[app]
name = "my-desk"
native_features = ["dialog", "clipboard", "notifications", "window"]
```

The runtime derives a capability for the exact session origin and main window. Unknown
feature names are rejected. Defaults grant none of these native permissions. No general
shell or filesystem plugin is exposed.

```javascript
const selected = await NativeStore.native.openDialog({multiple: false});
await NativeStore.native.writeClipboard("Copied from Python's interface");
const text = await NativeStore.native.readClipboard();
const granted = await NativeStore.native.notificationPermission();
if (granted) await NativeStore.native.notify({title: "Saved", body: "Your expense is recorded."});
await NativeStore.native.window("minimize");
```

Also available: saveDialog, requestNotificationPermission, and window operations setTitle,
maximize, unmaximize, close and isMaximized. These delegate to the public global Tauri
APIs enabled by withGlobalTauri. Browser debugging rejects native operations explicitly.
The operating system can deny notification permissions; installed Windows notification
behavior must be validated separately from development mode.

Native source is implemented, but these operations have not been exercised in an actual
native window in this Linux container. Window/installer checks must run in native CI.
Menus, tray integration, global shortcuts, single-instance behavior and updater integration
remain follow-up features using Tauri facilities, not replacement implementations.

Sources: https://v2.tauri.app/plugin/dialog/,
https://v2.tauri.app/plugin/clipboard/,
https://v2.tauri.app/plugin/notification/,
https://v2.tauri.app/security/capabilities/.
