# Safety guide

XenoBuddy-Pi.AI is a maker robotics framework. Treat moving servos and external power supplies with care.

## Software safety

- Start in simulation mode.
- Calibrate one servo at a time.
- Use conservative min/max angle bounds.
- Keep `max_speed_deg_per_sec` low until the mechanism is validated.
- Never allow an LLM to output raw servo angles directly.
- Disconnect servo power if motion looks wrong.

## Mechanical safety

- Keep fingers away from linkages during tests.
- Avoid sharp printed edges.
- Do not use the framework for load-bearing walking robots without a separate mechanical safety analysis.
- Use strain relief for wiring.
- Test with horns detached when discovering servo direction and centre points.

## Electrical safety

- Use an external servo supply.
- Match servo voltage ratings.
- Keep common ground between Pi and servo controller.
- Check polarity before powering.
- Avoid drawing servo current through breadboard rails beyond their rating.
