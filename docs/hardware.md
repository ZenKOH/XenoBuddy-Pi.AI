# Hardware guide

XenoBuddy-Pi.AI targets a small expressive tabletop robot rather than a load-bearing walking robot. The reference configuration uses Raspberry Pi 5, a PCA9685 16-channel PWM/servo driver, six leg/arm servos, one body tilt servo, microphone and speaker.

## Recommended bill of materials

- Raspberry Pi 5, 4GB or 8GB.
- microSD card with Raspberry Pi OS.
- PCA9685 servo HAT or I2C breakout.
- 6-8 hobby servos matched to your printed body.
- External 5-6V servo power supply sized for stall current.
- USB microphone or I2S microphone.
- Small powered speaker or I2S amplifier and speaker.
- Breadboard/jumper leads for prototyping.
- Optional emergency-stop switch in series with servo power.

## Why PCA9685

The Raspberry Pi has limited native PWM outputs for multi-servo control. A PCA9685 board offloads PWM timing over I2C and can address up to 16 servo/PWM channels, which makes it a clean fit for a seven-servo expressive robot.

## Servo power

Do not power several servos from the Raspberry Pi 5V rail. Servos can draw high transient current, especially at startup, end stops, or stall. Use an external supply for servo V+ and connect supply ground to Raspberry Pi ground.
