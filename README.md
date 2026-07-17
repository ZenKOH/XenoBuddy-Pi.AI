# XenoBuddy-Pi.AI

**Voice-to-motion Raspberry Pi framework for expressive tabletop robots.**

XenoBuddy-Pi.AI turns a small servo robot into an embodied voice agent: typed or spoken commands are interpreted into safe, named gestures; the robot replies through text-to-speech; and all physical motion is constrained by calibration and speed limits.

The project was inspired by a Raspberry Pi maker build of an AI-enabled alien robot companion, but it is deliberately implemented as a general-purpose open framework rather than a replica of any copyrighted character, voice, script, CAD model, or film asset.

## Core pipeline

```text
voice/text input
   -> intent router
   -> behaviour plan {reply, emotion, gesture, intensity}
   -> gesture library
   -> motion safety limiter
   -> simulation or PCA9685 servo bus
   -> spoken/printed response
```

The key design rule is: **AI may select behaviours, but it cannot directly command arbitrary servo angles.** Motion is executed only from a validated gesture library and bounded by servo calibration.

## Features

- Offline rule-based intent router for reliable maker and classroom demos.
- Motion DSL for reusable gestures such as `idle`, `wave`, `fist_bump`, `celebrate`, `confused`, and `explain`.
- Simulation servo bus for development without hardware.
- Optional PCA9685 hardware bus for Raspberry Pi servo control.
- Servo calibration with min/max angle and speed bounds.
- Safe JSON plan parser for future cloud/local LLM adapters.
- Piper TTS and whisper.cpp integration guidance.
- Pytest suite and GitHub Actions workflow.

## Hardware target

| Component | Purpose |
|---|---|
| Raspberry Pi 5, 4GB or 8GB | Main compute |
| PCA9685 16-channel PWM/servo HAT or breakout | Multi-servo output over I2C |
| 6–8 hobby servos | Legs/arms/body gestures |
| USB or I2S microphone | Voice input |
| Speaker or I2S amplifier | Voice output |
| Separate 5–6V servo power supply | Prevents Pi brownouts |
| 3D-printed or laser-cut body | Robot form factor |

> Safety: do **not** power multiple servos directly from the Raspberry Pi 5V rail. Use an external servo supply with common ground and conservative current headroom.

## Quick start: simulation mode

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

xenobuddy list-gestures
xenobuddy say "give me a fist bump"
xenobuddy preview gestures/fist_bump.yaml --step-ms 200
pytest -q
```

## Raspberry Pi hardware mode

```bash
pip install -e .[hardware]
xenobuddy say "wave hello" \
  --servo-config configs/servos.seven_servo_tripod.yaml \
  --bus pca9685
```

Enable I2C with `raspi-config`, connect the PCA9685, use a separate servo supply, and test each servo with conservative calibration limits before running full gestures.

## Repository map

```text
xenobuddy/        Python package and CLI
configs/         Servo calibration examples
gestures/        Motion DSL gesture YAML files
docs/            Hardware, safety and voice notes
tests/           Pytest coverage
```

## Roadmap

- [x] V0.1 software skeleton with motion DSL and simulation bus.
- [x] Safe offline intent-to-gesture router.
- [x] PCA9685 hardware abstraction.
- [x] Documentation and tests.
- [ ] Add permissively licensed CAD/body templates.
- [ ] Add browser-based calibration UI.
- [ ] Add OpenWakeWord and local LLM profiles.

## License

Software is released under the MIT License. Future CAD assets should use a clearly stated open hardware licence such as CERN-OHL-S or CC BY-SA.
