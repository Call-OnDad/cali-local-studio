# Third-party components

The MIT licence covers the original code and original example character rigs in this repository. It does not replace third-party licences. This repository does not include model weights, compiled engines or third-party source trees; setup downloads them from their publishers.

| Component | Upstream | Terms / retained evidence |
|---|---|---|
| Piper 1.3.0 | [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | GPL-3.0 runtime; retain its installed distribution notices and the individual voice terms. |
| Cori medium | [individual model directory](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/cori/medium) | Model card identifies a LibriVox public-domain dataset and credits Bryce Beattie. Setup retains the card. |
| Northern English male medium | [individual model directory](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/northern_english_male/medium) | Card cites OpenSLR 83, CC BY-SA 4.0 dataset terms and fine-tuning from Lessac. Preserve attribution; this is distinct from a blanket output-rights claim. |
| Rhubarb Lip Sync 1.14.0 | [DanielSWolf/rhubarb-lip-sync](https://github.com/DanielSWolf/rhubarb-lip-sync) | MIT project; installed release retains its dependency licences. Installer checksum pins the tested archive; it is not a publisher signature. |
| FFmpeg | [FFmpeg](https://ffmpeg.org/legal.html) | The installed build/configuration determines LGPL/GPL obligations. Docker uses Debian's package. |
| DejaVu fonts | [DejaVu Fonts](https://dejavu-fonts.github.io/License.html) | Installed system font package, with its own notices. |
| FastAPI, Uvicorn, HTTPX, Pillow, NumPy, ONNX Runtime and transitive packages | Installed Python distributions | Preserve their package licences/notices when redistributing a built environment. |
| Optional VoiceStudio | [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | AGPL-3.0 application. Model/code/output terms are separate; no third-party licence gate is bypassed here. |
| Optional KittenTTS | [KittenML/KittenTTS](https://github.com/KittenML/KittenTTS), [mini 0.8 model](https://huggingface.co/KittenML/kitten-tts-mini-0.8) | Source and model-card metadata declare Apache-2.0. Retain upstream notices; no independent guarantee about every training-source right is made. |

No company production mascot artwork, provider clips, approved private recordings or account credentials are included. New user-supplied assets must have suitable rights for their intended use.
