# Android simulator (Windows)

Lyra uses **Capacitor** and includes an **Android** project so you can run the app in the Android emulator on Windows.

**Important:** The emulator uses `adb reverse` to reach your PC’s API. You must run `adb reverse tcp:8000 tcp:8000` after starting the emulator.

## 1. Install Android Studio

1. Download **Android Studio** from [developer.android.com/studio](https://developer.android.com/studio) and install it.
2. Open Android Studio → **More Actions** → **SDK Manager** (or **File → Settings → Android SDK**).
3. Under **SDK Platforms**, install a recent Android version (e.g. **API 34**).
4. Under **SDK Tools**, ensure **Android SDK Build-Tools**, **Android Emulator**, and **Android SDK Platform-Tools** are installed.

## 2. Create a virtual device (AVD)

1. In Android Studio: **More Actions** → **Virtual Device Manager** (or **Tools → Device Manager**).
2. Click **Create Device** → choose a phone (e.g. **Pixel 6**) → **Next**.
3. Select a system image (e.g. **API 34**), download if needed → **Next** → **Finish**.

## 3. Run the API on your PC

In a terminal (keep it running):

```bash
cd api_exploration
.\venv\Scripts\activate
uvicorn pyjhora_api:app --port 8000
```

## 4. Start emulator and set up adb reverse

1. Start the emulator from Android Studio (Run button).
2. In a new terminal (or the project root):

```powershell
adb reverse tcp:8000 tcp:8000
```

**Run this every time you restart the emulator.** It tunnels emulator `127.0.0.1:8000` to your PC’s `localhost:8000`.

## 5. Build the app for the emulator

Use the Android emulator build (uses `http://127.0.0.1:8000`):

```powershell
cd lyra_app
npm run cap:sync:android
```

Or in one step (build, sync, open Android Studio):

```powershell
npm run android
```

## 6. Run in the emulator

1. In Android Studio, wait for Gradle sync to finish.
2. Select your virtual device in the toolbar (e.g. **Pixel 6 API 34**).
3. Click the **Run** (green play) button. The app will install and launch.

## Commands

| Command | Description |
|--------|-------------|
| `npm run build:android` | Build web app with `VITE_API_URL=http://127.0.0.1:8000` |
| `npm run cap:sync:android` | Build for emulator + sync to Android |
| `npm run cap:sync` | Build web app + copy into Android (uses default API URL) |
| `npm run cap:open:android` | Open Android project in Android Studio |
| `npm run android` | Build for emulator, sync, and open Android Studio |

## Full rebuild (if nothing works)

If the app still fails to reach the API, try a full rebuild:

### 1. Verify API and emulator

1. **Start the API** (keep running):
   ```powershell
   cd C:\Users\91866\Desktop\prokeralaandvedic\api_exploration
   .\venv\Scripts\activate
   uvicorn pyjhora_api:app --port 8000
   ```
2. **Test API in browser:** Open http://localhost:8000/health — you should see `{"status":"ok",...}`
3. **Start emulator:** In Android Studio → Device Manager → Run (▶) next to your virtual device. Wait until it fully boots.
4. **Verify adb sees device:**
   ```powershell
   adb devices
   ```
   You should see something like `emulator-5554   device`. If it says `no devices`, the emulator is not ready.
5. **Set up port reverse:**
   ```powershell
   adb reverse tcp:8000 tcp:8000
   ```
   No output means success.
6. **Test from emulator:** In the emulator's Chrome app, open http://127.0.0.1:8000/health — you should see the JSON. If this fails, `adb reverse` or the emulator network is the issue.

### 2. Rebuild the Lyra app

1. **Clean and rebuild for Android emulator:**
   ```powershell
   cd C:\Users\91866\Desktop\prokeralaandvedic\lyra_app
   Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
   npm run cap:sync:android
   ```
2. **Open Android project:**
   ```powershell
   npx cap open android
   ```
3. **In Android Studio:** File → Invalidate Caches / Restart (optional, if you see odd errors).
4. **Run the app:** Select your emulator in the toolbar → click Run (▶).

### 3. What the error screen shows

If the app still fails, the error screen will now show the **API base URL** it is using (e.g. `http://127.0.0.1:8000`). If it shows `http://localhost:8000`, you did not use `npm run cap:sync:android` — rebuild with that command.

## Troubleshooting

- **"adb: no devices/emulators found":** Start the emulator first (Device Manager → Run). Wait until it fully boots, then run `adb devices` to confirm.
- **"Nothing coming" / stuck on "Loading cosmic data…":** Ensure (1) API is running, (2) emulator is running, (3) `adb reverse tcp:8000 tcp:8000` ran successfully, and (4) you used `npm run cap:sync:android`. Check the error screen — it shows the API URL being used.
- **ERR_CONNECTION_TIMED_OUT:** Use `adb reverse` + `127.0.0.1:8000` (not `10.0.2.2`).
- **Gradle errors:** In Android Studio try **File → Invalidate Caches / Restart** and check **File → Project Structure → SDK Location**.
