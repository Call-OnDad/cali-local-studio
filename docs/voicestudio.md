# Optional local VoiceStudio speech

The default Piper workflow is complete without VoiceStudio. This optional adapter provides two KittenTTS presets from a separate **local** VoiceStudio service. It does not turn the app into a cloning or custom-timbre editor.

1. Install [VoiceStudio](https://github.com/debpalash/VoiceStudio) using its official server instructions. Keep it private and review its application/model terms. The integration was tested with source commit `f3731e237cec3aa9f6234b03b7cf384b0fbf3a67` and CPU PyTorch 2.8.0; future releases need validation.
2. Select/install `kittentts` and its mini 0.8 model. Do **not** assume the default OmniVoice weights are Apache-licensed merely because some code is. Restricted/unresolved model terms were not accepted during this project's integration work.
3. Configure the backend's admin key, but keep it out of git. Point `VOICESTUDIO_URL` and `VOICESTUDIO_API_KEY_FILE` at that private service and key file. Docker needs an explicit reachable local service address and a read-only secret-file mount; loopback inside a container is that container, not the host.
4. Warm the selected model deliberately during setup. If operating fully offline, disable optional uncached modules rather than letting a generation silently fetch more assets. In the tested release the supported endpoint is `POST /watermark/settings?invisible=false`; we disabled optional AudioSeal after it attempted a checkpoint download. Synthetic-source records remain in the studio's job evidence. Do not remove watermarks from third-party supplied media.
5. Run `python scripts/check_voicestudio.py` in the studio environment. This requests a real small local KittenTTS recording, checks it is a WAV and writes the readiness marker only on success. The adapter requests `engine=kittentts`, raw output, no denoising or postprocessing, and preserves the generated source WAV.

Only a local service credential is involved, not a paid-generation API key. The adapter has no hosted provider fallback. Model setup still requires its free downloads unless you provision the cache yourself.
