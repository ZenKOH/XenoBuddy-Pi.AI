from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml


@dataclass(frozen=True)
class ServoCalibration:
    name: str
    channel: int
    min_angle: float = 0.0
    max_angle: float = 180.0
    home_angle: float = 90.0
    min_pulse: int = 500
    max_pulse: int = 2500
    max_speed_deg_per_sec: float = 120.0

    def clamp(self, angle: float) -> float:
        return min(max(angle, self.min_angle), self.max_angle)


@dataclass(frozen=True)
class RobotConfig:
    name: str
    pwm_frequency: int
    servos: dict[str, ServoCalibration]


@dataclass(frozen=True)
class BehaviourPlan:
    reply: str
    emotion: str
    motion: str
    intensity: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return {'reply': self.reply, 'emotion': self.emotion, 'motion': self.motion, 'intensity': self.intensity}

    @classmethod
    def safe(cls, reply: str, emotion: str, motion: str, intensity: float = 1.0) -> 'BehaviourPlan':
        return cls(
            reply.strip()[:500],
            emotion.strip().lower()[:40] or 'neutral',
            motion.strip().lower()[:80] or 'idle',
            min(max(float(intensity), 0.0), 1.0),
        )


@dataclass(frozen=True)
class Keyframe:
    t_ms: int
    angle: float


@dataclass(frozen=True)
class ServoTrack:
    servo: str
    keyframes: tuple[Keyframe, ...]


@dataclass(frozen=True)
class Gesture:
    name: str
    description: str
    duration_ms: int
    tracks: tuple[ServoTrack, ...]
    max_speed_deg_per_sec: float = 90.0


@dataclass(frozen=True)
class MotionFrame:
    t_ms: int
    angles: dict[str, float]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_servo_config_path() -> Path:
    return project_root() / 'configs' / 'servos.seven_servo_tripod.yaml'


def default_gestures_dir() -> Path:
    return project_root() / 'gestures'


def load_yaml(path: str | Path) -> dict:
    with Path(path).open('r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f'Expected YAML mapping at {path}')
    return data


def load_robot_config(path: str | Path) -> RobotConfig:
    data = load_yaml(path)
    servos: dict[str, ServoCalibration] = {}
    for item in data.get('servos', []):
        servo = ServoCalibration(**item)
        servos[servo.name] = servo
    if not servos:
        raise ValueError('Servo config must include at least one servo')
    return RobotConfig(str(data.get('name', 'xenobuddy')), int(data.get('pwm_frequency', 50)), servos)


def load_gesture_file(path: str | Path) -> Gesture:
    data = load_yaml(path)
    tracks: list[ServoTrack] = []
    for servo_name, keyframes in (data.get('servos') or {}).items():
        parsed = tuple(sorted((Keyframe(int(f['t']), float(f['angle'])) for f in keyframes), key=lambda f: f.t_ms))
        if parsed:
            tracks.append(ServoTrack(str(servo_name), parsed))
    if not tracks:
        raise ValueError(f'Gesture {path} has no servo tracks')
    safety = data.get('safety') or {}
    return Gesture(
        str(data.get('name') or Path(path).stem),
        str(data.get('description', '')),
        int(data.get('duration_ms', 1000)),
        tuple(tracks),
        float(safety.get('max_speed_deg_per_sec', 90.0)),
    )


class GestureLibrary:
    def __init__(self, gestures: dict[str, Gesture]) -> None:
        self._gestures = gestures

    @classmethod
    def from_dir(cls, directory: str | Path) -> 'GestureLibrary':
        gestures = {g.name: g for g in (load_gesture_file(p) for p in sorted(Path(directory).glob('*.yaml')))}
        if 'idle' not in gestures:
            raise ValueError('Gesture library must include idle')
        return cls(gestures)

    def names(self) -> set[str]:
        return set(self._gestures)

    def has(self, name: str) -> bool:
        return name in self._gestures

    def get(self, name: str) -> Gesture:
        return self._gestures[name]


class OfflineIntentRouter:
    def __init__(self, gestures: GestureLibrary) -> None:
        self.gestures = gestures
        self.rules = [
            (('fist bump', 'bump', 'high five'), BehaviourPlan.safe('Friendly contact protocol initiated.', 'happy', 'fist_bump', 0.75)),
            (('wave', 'hello', 'hi ', 'greet'), BehaviourPlan.safe('Hello, human collaborator. I acknowledge your presence with enthusiasm.', 'friendly', 'wave', 0.7)),
            (('celebrate', 'success', 'great job', 'awesome'), BehaviourPlan.safe('Celebration subroutine complete. Morale has increased by measurable units.', 'excited', 'celebrate', 0.9)),
            (('confused', 'puzzled', 'strange', 'what'), BehaviourPlan.safe('Curious. My reasoning lattice requires additional evidence.', 'curious', 'confused', 0.55)),
            (('photosynthesis', 'explain', 'science'), BehaviourPlan.safe('Plants convert light, water and carbon dioxide into chemical energy. Elegant, efficient, and suspiciously green.', 'teacher', 'explain', 0.5)),
        ]

    def plan(self, text: str) -> BehaviourPlan:
        lowered = f' {text.lower()} '
        for phrases, plan in self.rules:
            if any(p in lowered for p in phrases):
                return plan if self.gestures.has(plan.motion) else BehaviourPlan.safe(plan.reply, plan.emotion, 'idle', plan.intensity)
        return BehaviourPlan.safe('I heard you. I will remain calmly attentive until a clearer action is requested.', 'neutral', 'idle', 0.35)


def parse_behaviour_json(raw: str, allowed_motions: set[str]) -> BehaviourPlan:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError('LLM response was not valid JSON') from exc
    if not isinstance(payload, dict):
        raise ValueError('LLM response must be an object')
    motion = str(payload.get('motion', 'idle')).strip().lower()
    if motion not in allowed_motions:
        motion = 'idle'
    return BehaviourPlan.safe(
        str(payload.get('reply', '')),
        str(payload.get('emotion', 'neutral')),
        motion,
        float(payload.get('intensity', 1.0)),
    )


def interpolate(track: ServoTrack, t_ms: int) -> float:
    frames = track.keyframes
    if t_ms <= frames[0].t_ms:
        return frames[0].angle
    if t_ms >= frames[-1].t_ms:
        return frames[-1].angle
    for left, right in zip(frames, frames[1:]):
        if left.t_ms <= t_ms <= right.t_ms:
            span = right.t_ms - left.t_ms
            alpha = 0 if span <= 0 else (t_ms - left.t_ms) / span
            return left.angle + alpha * (right.angle - left.angle)
    return frames[-1].angle


def render_timeline(gesture: Gesture, calibrations: dict[str, ServoCalibration], *, intensity: float = 1.0, step_ms: int = 100) -> list[MotionFrame]:
    if step_ms <= 0:
        raise ValueError('step_ms must be positive')
    intensity = min(max(float(intensity), 0.0), 1.0)
    times = sorted(set(list(range(0, gesture.duration_ms + step_ms, step_ms)) + [gesture.duration_ms]))
    frames: list[MotionFrame] = []
    for t_ms in times:
        angles: dict[str, float] = {}
        for track in gesture.tracks:
            if track.servo not in calibrations:
                raise ValueError(f'Gesture references unknown servo: {track.servo}')
            cal = calibrations[track.servo]
            raw = interpolate(track, t_ms)
            scaled = cal.home_angle + (raw - cal.home_angle) * intensity
            angles[track.servo] = round(cal.clamp(scaled), 3)
        frames.append(MotionFrame(t_ms, angles))
    validate_speed(frames, calibrations, gesture.max_speed_deg_per_sec)
    return frames


def validate_speed(frames: list[MotionFrame], calibrations: dict[str, ServoCalibration], gesture_limit: float) -> None:
    previous = None
    for frame in frames:
        if previous is None:
            previous = frame
            continue
        dt = (frame.t_ms - previous.t_ms) / 1000.0
        if dt <= 0:
            previous = frame
            continue
        for servo, angle in frame.angles.items():
            if servo not in previous.angles:
                continue
            allowed = min(float(gesture_limit), calibrations[servo].max_speed_deg_per_sec)
            speed = abs(angle - previous.angles[servo]) / dt
            if speed > allowed + 1e-6:
                raise ValueError(f'Gesture exceeds speed limit on {servo}: {speed:.1f} deg/s > {allowed:.1f} deg/s')
        previous = frame


class ServoBus(Protocol):
    name: str
    config: RobotConfig
    def execute(self, frames: list[MotionFrame], *, dry_run: bool = False) -> None: ...


class SimulationServoBus:
    name = 'sim'
    def __init__(self, config: RobotConfig) -> None:
        self.config = config
    def execute(self, frames: list[MotionFrame], *, dry_run: bool = False) -> None:
        for frame in frames:
            print(f'[sim t={frame.t_ms:04d}ms] {frame.angles}')


class PCA9685ServoBus:
    name = 'pca9685'
    def __init__(self, config: RobotConfig) -> None:
        self.config = config
        try:
            import board  # type: ignore
            import busio  # type: ignore
            from adafruit_motor import servo as motor_servo  # type: ignore
            from adafruit_pca9685 import PCA9685  # type: ignore
        except ImportError as exc:
            raise RuntimeError('PCA9685 mode requires Raspberry Pi hardware libraries. Install with: pip install -e .[hardware]') from exc
        i2c = busio.I2C(board.SCL, board.SDA)
        self._pca = PCA9685(i2c)
        self._pca.frequency = config.pwm_frequency
        self._servos = {
            name: motor_servo.Servo(self._pca.channels[cal.channel], min_pulse=cal.min_pulse, max_pulse=cal.max_pulse)
            for name, cal in config.servos.items()
        }
    def execute(self, frames: list[MotionFrame], *, dry_run: bool = False) -> None:
        if dry_run:
            return SimulationServoBus(self.config).execute(frames, dry_run=True)
        previous_t = 0
        for frame in frames:
            time.sleep(max(frame.t_ms - previous_t, 0) / 1000.0)
            for servo_name, angle in frame.angles.items():
                self._servos[servo_name].angle = angle
            previous_t = frame.t_ms


def create_servo_bus(name: str, config: RobotConfig) -> ServoBus:
    if name == 'sim':
        return SimulationServoBus(config)
    if name == 'pca9685':
        return PCA9685ServoBus(config)
    raise ValueError(f'Unknown servo bus: {name}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='XenoBuddy-Pi.AI command line')
    parser.add_argument('--servo-config', type=Path, default=default_servo_config_path())
    parser.add_argument('--gestures-dir', type=Path, default=default_gestures_dir())
    parser.add_argument('--bus', choices=['sim', 'pca9685'], default='sim')
    parser.add_argument('--step-ms', type=int, default=100)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list-gestures').set_defaults(func=cmd_list_gestures)
    say = sub.add_parser('say')
    say.add_argument('text')
    say.add_argument('--dry-run', action='store_true')
    say.set_defaults(func=cmd_say)
    preview = sub.add_parser('preview')
    preview.add_argument('motion_file', type=Path)
    preview.add_argument('--intensity', type=float, default=1.0)
    preview.set_defaults(func=cmd_preview)
    return parser


def cmd_list_gestures(args: argparse.Namespace) -> int:
    library = GestureLibrary.from_dir(args.gestures_dir)
    for name in sorted(library.names()):
        print(f'{name}\t{library.get(name).description}')
    return 0


def cmd_say(args: argparse.Namespace) -> int:
    config = load_robot_config(args.servo_config)
    library = GestureLibrary.from_dir(args.gestures_dir)
    plan = OfflineIntentRouter(library).plan(args.text)
    frames = render_timeline(library.get(plan.motion), config.servos, intensity=plan.intensity, step_ms=args.step_ms)
    print(json.dumps(plan.to_dict(), indent=2))
    create_servo_bus(args.bus, config).execute(frames, dry_run=args.dry_run)
    print(f'XenoBuddy: {plan.reply}')
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    config = load_robot_config(args.servo_config)
    gesture = load_gesture_file(args.motion_file)
    for frame in render_timeline(gesture, config.servos, intensity=args.intensity, step_ms=args.step_ms):
        print(json.dumps({'t': frame.t_ms, 'angles': frame.angles}, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
