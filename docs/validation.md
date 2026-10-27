# Validation and current limits

The project originates from a real CPU server deployment. That deployment verified new Piper and VoiceStudio/KittenTTS speech, Rhubarb cues, fresh human/canine animation, complete video decoding, hashes/audio levels, HD landscape export, cancellation, non-destructive revisions and interrupted-job recovery. Browser checks covered desktop/mobile layout, no-login local access, actual decoded video frames and no external page requests. A cold server restart preserved jobs and exports. These facts do not certify every host, model, accent or script.

`python -m unittest -v test_controls` verifies API/control behaviour with the renderer worker stubbed. It is not an end-to-end media test. `scripts/smoke_test.py` uses a real running service with installed weights/tooling and must produce a fresh export with a successful complete decode.

The public Docker package is validated separately from the original deployment. Record the outcome of clean-install tests below, rather than inferring that a native server test proves a Docker image works.

Automatic mouth cues are speech-informed estimates. Simple 2D poses are not anatomical simulation; still/decoded frame checks cannot approve lip-sync by ear. Sentence captions are approximate, and the SRT is editable. Review at normal speed, especially word endings, pauses and canine jaw closure.

The source includes original example rigs only. There is no automatic rig creation, photorealistic character generation, image upload workflow, 3D editor or local clone/timbre-design workflow. There is no claim of provider-equivalent video quality. Longer scenes and HD renders can take minutes on a CPU; measure your own hardware.

No hosted CI or paid inference is required to run these checks. Setup downloads are distinct from local generation; network enforcement must preserve the access path on the target host.

## Clean public package checks — 26 October 2026

A fresh Debian Linux x86-64 environment built the Docker image with the committed dependency lock. All seven packaged control tests passed. A real new Piper/Rhubarb/animation render produced a completely decoded 6.10-second MP4. A second fresh 5.80-second render completed with Docker public egress blocked. Named-volume projects and cached models survived service/network recreation.

The normal LAN deployment passed fresh Chrome checks at 1920px and 390px: wide editor/workspace layout, no horizontal overflow, decoded video frames, no JavaScript errors and no external page requests. The internal-network experiment blocked LAN ports, so it is not included as an install option. No paid provider or account key was used.
