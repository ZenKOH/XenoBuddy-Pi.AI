from pathlib import Path

import pytest

from xenobuddy.core import (
    GestureLibrary,
    OfflineIntentRouter,
    load_robot_config,
    parse_behaviour_json,
    render_timeline,
)

ROOT = Path(__file__).resolve().parents[1]


def test_all_gestures_render_inside_limits():
    config = load_robot_config(ROOT / 'configs' / 'servos.seven_servo_tripod.yaml')
    library = GestureLibrary.from_dir(ROOT / 'gestures')
    for name in library.names():
        frames = render_timeline(library.get(name), config.servos, step_ms=100)
        assert frames
        for frame in frames:
            for servo, angle in frame.angles.items():
                cal = config.servos[servo]
                assert cal.min_angle <= angle <= cal.max_angle


def test_fist_bump_intent_maps_to_gesture():
    library = GestureLibrary.from_dir(ROOT / 'gestures')
    plan = OfflineIntentRouter(library).plan('please give me a fist bump')
    assert plan.motion == 'fist_bump'
    assert 0 <= plan.intensity <= 1


def test_unknown_json_motion_falls_back_to_idle():
    plan = parse_behaviour_json(
        '{"reply":"ok","emotion":"happy","motion":"unsafe_jump","intensity":1}',
        {'idle', 'wave'},
    )
    assert plan.motion == 'idle'


def test_rejects_non_json():
    with pytest.raises(ValueError):
        parse_behaviour_json('not-json', {'idle'})
