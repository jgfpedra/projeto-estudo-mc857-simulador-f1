"""Checkpoint for API races. Redis must be trusted: payloads use Python pickle.

The physics solver's internal contact cache is not exported; resumption restores
body poses and velocities but is not bit-identical, especially during impacts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import pickle
import zlib

import pybullet as pb

from .simulation import SimulationEngine
from .rule_based_race_controller import RuleBasedRaceController

VERSION = 2
ENGINE_FIELDS = (
    'user_driver_id', 'states', 'last_inputs', 'last_input_ts', 'sim_ts',
    'current_lap', 'race_started', 'race_finished', 'prev_waypoint_idx',
    'max_wp_visited', 'lap_start_ts', 'cum_dist_m', 'last_pos',
    'race_progress_m', '_tyre_fit_progress_m', 'race_s_m', 'race_lateral_m',
    '_race_last_s', 'last_tyre_warn_pct', '_no_lap_drivers', 'last_weather_kind',
    'collision_tracker', '_pit_requests', '_pit_commands', '_pit_cancel_commands',
    '_pit_skip_auto_once', '_manual_pit_active', '_accepting_pit_commands',
    'finished_drivers', '_weather_evaluated_lap',
)


def _signature(payload):
    secret = os.environ.get('F1_CHECKPOINT_SECRET')
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest() if secret else ''


def capture(engine, publisher):
    cid = engine.physics._client_id
    if cid is None:
        raise RuntimeError('Física não inicializada')
    bodies = {}
    for driver_id, handle in engine.handles.items():
        body = handle.chassis_id
        bodies[driver_id] = {
            'pose': pb.getBasePositionAndOrientation(body, physicsClientId=cid),
            'velocity': pb.getBaseVelocity(body, physicsClientId=cid),
            'joints': [pb.getJointState(body, i, physicsClientId=cid)[:2]
                       for i in range(pb.getNumJoints(body, physicsClientId=cid))],
            'mass': handle.mass_kg,
        }
    controller = next(iter(engine.controllers.values()))
    if not isinstance(controller, RuleBasedRaceController) or any(c is not controller for c in engine.controllers.values()):
        raise ValueError('Checkpoint só aceita controlador por regras compartilhado')
    with engine._pit_command_lock:
        data = {
            'version': VERSION, 'config': engine.config, 'track': engine.track,
            'drivers': engine.drivers, 'weather_model': engine.weather_model,
            'engine': {name: getattr(engine, name) for name in ENGINE_FIELDS},
            'pit_progress': engine.pit_controller.progress,
            'controller': {'hints': controller._hints, 'styles': controller._styles,
                           'authority': controller.last_authority, 'gridlock': controller._gridlock},
            'bodies': bodies,
            'publisher': {'snapshot': publisher.snapshot, 'timing': publisher.timing,
                          'collisions': publisher.collisions},
        }
        payload = zlib.compress(pickle.dumps(data, protocol=5), level=1)
        return _signature(payload) + '.' + base64.b64encode(payload).decode('ascii')


def restore(encoded, publisher):
    signature, payload = encoded.split('.', 1)
    compressed = base64.b64decode(payload, validate=True)
    if not hmac.compare_digest(signature, _signature(compressed)):
        raise ValueError('Assinatura do checkpoint inválida')
    data = pickle.loads(zlib.decompress(compressed))
    if data.get('version') != VERSION:
        raise ValueError('Versão de checkpoint incompatível')
    engine = SimulationEngine(data['config'], data['track'], data['drivers'],
                              publisher=publisher, weather_model=data['weather_model'])
    engine.setup()
    try:
        for name, value in data['engine'].items():
            setattr(engine, name, value)
        engine.pit_controller.progress = data['pit_progress']
        controller = RuleBasedRaceController(engine.track, seed=engine.config.random_seed)
        controller._hints = data['controller']['hints']
        controller._styles = data['controller']['styles']
        controller.last_authority = data['controller']['authority']
        controller._gridlock = data['controller']['gridlock']
        for driver in engine.drivers:
            engine.set_controller(driver.driver_id, controller)
        cid = engine.physics._client_id
        for driver_id, body in data['bodies'].items():
            handle = engine.handles[driver_id]
            handle.mass_kg = body['mass']
            pb.changeDynamics(handle.chassis_id, -1, mass=body['mass'], physicsClientId=cid)
            pb.resetBasePositionAndOrientation(handle.chassis_id, *body['pose'], physicsClientId=cid)
            pb.resetBaseVelocity(handle.chassis_id, *body['velocity'], physicsClientId=cid)
            for index, (position, velocity) in enumerate(body['joints']):
                pb.resetJointState(handle.chassis_id, index, position, velocity, physicsClientId=cid)
        publisher.snapshot = data['publisher']['snapshot']
        publisher.timing = data['publisher']['timing']
        publisher.collisions = data['publisher']['collisions']
        publisher.engine = engine
        engine.physics.contact_collector = []
        engine.physics.contact_collector_include_penetration = True
        return engine
    except Exception:
        engine.teardown()
        raise
