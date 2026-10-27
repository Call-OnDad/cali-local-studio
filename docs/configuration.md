# Configuration

Set these in the process environment (native Linux) or via Compose environment entries. `.env` is ignored by git; `.env.example` contains examples only.

| Variable | Default / purpose |
|---|---|
| `STUDIO_DATA` | `data/` beside `app.py`; SQLite jobs, audio, frames and exports. |
| `STUDIO_MODELS_DIR` | `models/` beside `app.py`; downloaded Piper weights/configs/cards. |
| `RHUBARB_PATH` | `rhubarb` on PATH, otherwise `tools/rhubarb/rhubarb`. |
| `STUDIO_ALLOWED_NETWORKS` | Loopback and RFC1918 private networks, comma-separated CIDRs. Restrict to your own LAN if preferred. |
| `STUDIO_ALLOWED_HOSTS` | Extra exact local DNS names, comma-separated. Local/private IP literals and loopback names work by default. |
| `STUDIO_DOWNLOAD_MODELS` | Docker entrypoint: `1` checks/downloads models; `0` starts using installed files only. |
| `VOICESTUDIO_URL` | Optional backend, default `http://127.0.0.1:3900`. Set to an instance you control. |
| `VOICESTUDIO_API_KEY_FILE` | Optional backend's internal admin-key file; default `private/voicestudio-key`. Not needed for Piper-only operation. |

The optional VoiceStudio presets stay disabled until the backend check writes `data/voicestudio-ready.json`. Do not create that marker by hand to claim a working integration. A hostname outside the allowed set is rejected even when the client is local. Requests from public client addresses are rejected. No user login is included, so never treat the network checks as a general-purpose public authentication system.

The renderer supports scripts up to 1,800 characters and generated speech up to 180 seconds. The queue runs one heavy job at a time and caps waiting work. For slower CPUs use previews first; full HD involves substantially more pixels. Runtime ONNX threads are bounded in `runtime/sitecustomize.py`; this also disables ONNX telemetry.

Use a private local deployment or your own authenticated access layer. Do not add public Host names and port forwarding merely to bypass a rejection. Closing the browser is safe after a job is submitted; deleting the data volume is not.
