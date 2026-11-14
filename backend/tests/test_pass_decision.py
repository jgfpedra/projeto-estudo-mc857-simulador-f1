"""PASS-1: predicado, lado, abortos e passividade do caminho default-OFF."""
import math
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)


def _make_controller(pass_decision=True, leader_yield=False):
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.reference_controller import ReferenceController
    from backend.model_train.velocity_profile import VelocityProfile

    class Physics:
        def __init__(self):
            self.state = dict(x=200.0, y=0.0, speed_mps=30.0,
                              heading_rad=math.pi / 2, yaw_rate=0.0,
                              g_lat=0.0, g_long=0.0)

        def get_state(self, _handle):
            return self.state

    class Engine:
        def __init__(self):
            self.handles = {'EGO': object()}
            self.physics = Physics()

    class Host:
        _project_on_path = F1MultiContextEnv._project_on_path
        _point_at = F1MultiContextEnv._point_at
        _kappa_signed = F1MultiContextEnv._kappa_signed
        _heading_at = F1MultiContextEnv._heading_at
        steer_limit_rad = staticmethod(F1MultiContextEnv.steer_limit_rad)

    env = Host()
    pts = np.array([(200.0 * math.cos(2 * math.pi * i / 72),
                     200.0 * math.sin(2 * math.pi * i / 72))
                    for i in range(72)], dtype=np.float64)
    B = np.roll(pts, -1, axis=0)
    AB = B - pts
    lengths = np.hypot(AB[:, 0], AB[:, 1])
    env._wps_arr = pts
    env._seg_AB = AB
    env._seg_len = lengths
    env._seg_cum = np.concatenate([[0.0], np.cumsum(lengths)])[:-1]
    env._seg_heading = np.arctan2(AB[:, 1], AB[:, 0])
    env._track_len_s = float(lengths.sum())
    env._half_width = 6.0
    env.driver_id = 'EGO'
    env.engine = Engine()
    vp = VelocityProfile(pts, grip_mult=0.788, sf=0.80,
                         ds_target=4.0, smooth_window_m=20.0)
    return ReferenceController(env, velocity_profile=vp,
                               pass_decision=pass_decision,
                               leader_yield=leader_yield)


def _context(gap=20.0, ego_speed=21.0, other_speed=20.0, now=63.0,
             allowed=True, contact_pairs=(), ego_cum=1000.0,
             target_cum=None, sample=True, target_lat=0.0):
    target_cum = 1000.0 + gap if target_cum is None else target_cum
    return dict(
        t_s=now, sample_5hz=sample, allowed=allowed,
        cars=[dict(driver_id='TGT', s=100.0 + gap, lat=target_lat,
                   speed=other_speed, cum_dist=target_cum)],
        ego_cum_dist=ego_cum, track_len_s=1000.0, half_width=6.0,
        contact_pairs=set(contact_pairs),
    )


def _runtime_state_sha(ctrl):
    """Hash only mutable control state; the ON/OFF config bit is excluded."""
    fields = (
        '_lat_offset', 'last_follow_mode', '_last_pursuit', '_pass_state',
        'last_pass_state', '_pass_target', '_pass_cooldown', '_pass_closing',
        '_pass_decision_state', '_pass_decision_stats',
    )
    state = {name: getattr(ctrl, name) for name in fields}
    payload = json.dumps(state, sort_keys=True, separators=(',', ':'),
                         default=list).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


class TestPassDecisionPredicate:
    def test_threshold_edges_and_fifteen_samples(self):
        ctrl = _make_controller()
        # 14.999 m fails; exactly 15 m and exactly 1 m/s qualify.
        result = None
        for i in range(15):
            ctx = _context(gap=14.999, now=61.0 + i * 0.2)
            result = ctrl._pass_decision_layer(100.0, 21.0, 0.0, 40.0, ctx)
        assert result[2] == 'FOLLOW'
        assert ctrl._pass_decision_state['candidate_samples'] == 0

        for i in range(14):
            result = ctrl._pass_decision_layer(
                100.0, 21.0, 0.0, 40.0,
                _context(gap=15.0, now=65.0 + i * 0.2))
        assert result[2] == 'FOLLOW'
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=15.0, now=67.8))
        assert result == (True, result[1], 'DECISION_ACTIVE')
        assert ctrl._pass_decision_stats['engaged'] == 1

    def test_immediate_follow_target_uses_existing_same_line_filter(self):
        ctrl = _make_controller()
        ctx = _context(gap=20.0)
        ctx['cars'] = [
            dict(driver_id='LATERAL', s=110.0, lat=3.0, speed=20.0,
                 cum_dist=1010.0),
            dict(driver_id='FOLLOW', s=120.0, lat=0.0, speed=20.0,
                 cum_dist=1020.0),
        ]
        for i in range(15):
            ctx['t_s'] = 61.0 + i * 0.2
            result = ctrl._pass_decision_layer(
                100.0, 21.0, 0.0, 40.0, ctx)
        assert result[2] == 'DECISION_ACTIVE'
        assert ctrl._pass_decision_state['target_id'] == 'FOLLOW'

        close_front = _make_controller()
        ctx['cars'] = [
            dict(driver_id='NEAR', s=110.0, lat=0.0, speed=20.0,
                 cum_dist=1010.0),
            dict(driver_id='FAR', s=120.0, lat=0.0, speed=20.0,
                 cum_dist=1020.0),
        ]
        for i in range(15):
            ctx['t_s'] = 65.0 + i * 0.2
            result = close_front._pass_decision_layer(
                100.0, 21.0, 0.0, 40.0, ctx)
        assert result[2] == 'FOLLOW'

    def test_speed_difference_below_one_does_not_qualify(self):
        ctrl = _make_controller()
        for i in range(20):
            result = ctrl._pass_decision_layer(
                100.0, 20.999, 0.0, 40.0,
                _context(gap=20.0, ego_speed=20.999, other_speed=20.0,
                         now=61.0 + i * 0.2))
        assert result[2] == 'FOLLOW'
        assert ctrl._pass_decision_stats['engaged'] == 0


class TestPassDecisionClearanceAndAbort:
    def test_selects_side_with_greater_lateral_clearance(self):
        ctrl = _make_controller()
        cars = [
            dict(driver_id='TGT', s=120.0, lat=0.0, speed=20.0,
                 cum_dist=1020.0),
            dict(driver_id='LEFT', s=105.0, lat=2.5, speed=20.0,
                 cum_dist=1005.0),
        ]
        side, target_lat = ctrl._pass_decision_choose_side(
            100.0, 0.0, cars, 6.0, 1000.0)
        assert side == -1.0
        assert target_lat == pytest.approx(-2.5)

    def _active(self, ctrl, started=60.0):
        ctrl._pass_decision_state.update(
            active=True, target_id='TGT', started_s=started, start_lat=0.0,
            side=1.0, target_lat=2.5, lateral_progress_m=0.0)

    def test_gap_abort_without_lateral_progress(self):
        ctrl = _make_controller()
        self._active(ctrl)
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=7.9, now=61.0, target_cum=1007.9))
        assert result == (False, None, 'DECISION_ABORT_GAP')
        assert ctrl._pass_decision_stats['aborted_gap'] == 1
        assert ctrl._pass_decision_stats['attempts'][-1]['outcome'] == 'abort_gap'

    def test_timeout_abort_after_eight_seconds(self):
        ctrl = _make_controller()
        self._active(ctrl)
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=20.0, now=68.01, target_cum=1020.0))
        assert result == (False, None, 'DECISION_ABORT_TIMEOUT')
        assert ctrl._pass_decision_stats['aborted_timeout'] == 1

    def test_solver_contact_abort_is_pair_specific(self):
        ctrl = _make_controller()
        self._active(ctrl)
        unrelated = {('EGO', 'OTHER')}
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=20.0, now=61.0, contact_pairs=unrelated))
        assert result[2] == 'DECISION_ACTIVE'
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=20.0, now=61.1,
                     contact_pairs={('EGO', 'TGT')}))
        assert result == (False, None, 'DECISION_ABORT_CONTACT')
        assert ctrl._pass_decision_stats['aborted_contact'] == 1
        assert ctrl._pass_decision_stats['attempts'][-1]['target_id'] == 'TGT'

    def test_rejoin_carveout_aborts_an_active_attempt(self):
        ctrl = _make_controller()
        self._active(ctrl)
        result = ctrl._pass_decision_layer(
            100.0, 21.0, 0.0, 40.0,
            _context(gap=20.0, now=61.0, allowed=False))
        assert result == (False, None, 'DECISION_ABORT_REJOIN')
        assert ctrl._pass_decision_stats['aborted_rejoin'] == 1


class TestPassDecisionCarveoutsAndParity:
    def test_launch_and_rejoin_carveouts_reset_the_streak(self):
        ctrl = _make_controller()
        for i in range(15):
            result = ctrl._pass_decision_layer(
                100.0, 21.0, 0.0, 40.0,
                _context(now=59.8, allowed=True))
        assert result[2] == 'FOLLOW'
        assert ctrl._pass_decision_state['candidate_samples'] == 0
        for i in range(15):
            result = ctrl._pass_decision_layer(
                100.0, 21.0, 0.0, 40.0,
                _context(now=70.0 + i * 0.2, allowed=False))
        assert result[2] == 'FOLLOW'
        assert ctrl._pass_decision_stats['engaged'] == 0

    def test_flag_off_keeps_legacy_action_and_default(self):
        legacy = _make_controller(pass_decision=False)
        off = _make_controller(pass_decision=False)
        assert legacy.PASS_DECISION_ENABLED is False
        traffic = [(105.0, 0.0, 20.0)]
        a = legacy.action(traffic)
        b = off.action(traffic)
        np.testing.assert_array_equal(a, b)
        assert legacy.last_pass_state == off.last_pass_state
        assert legacy._lat_offset == off._lat_offset

    def test_flag_on_transitions_only_after_explicit_sustained_engage(self):
        ctrl = _make_controller(pass_decision=True)
        ctrl._pass_layer = lambda *_args: (_ for _ in ()).throw(
            AssertionError('máquina legada chamada após o engajamento'))
        _, s, _, _ = ctrl.env._project_on_path(200.0, 0.0)
        ctx = _context(gap=20.0, now=63.0)
        ctx['cars'][0]['s'] = s + 20.0
        ctx['track_len_s'] = ctrl.env._track_len_s
        ctx['decision_engage_target'] = 'TGT'
        result = ctrl.action([(s + 20.0, 0.0, 20.0)],
                             pass_decision_context=ctx)
        assert result.shape == (2,)
        assert ctrl.last_pass_state == 'DECISION_ACTIVE'

    def test_runner_window_engages_on_same_tick(self):
        ctrl = _make_controller(pass_decision=True)
        _, ego_s, _, _ = ctrl.env._project_on_path(200.0, 0.0)
        target_s = (ego_s + 20.0) % ctrl.env._track_len_s
        context = _context(gap=20.0, now=63.0, sample=True)
        context.update(
            cars=[dict(driver_id='TGT', s=target_s, lat=0.0, speed=20.0)],
            s_ego=ego_s, track_len_s=ctrl.env._track_len_s,
            decision_engage_target='TGT')

        ctrl.action([(target_s, 0.0, 20.0)],
                    pass_decision_context=context)

        assert ctrl._pass_decision_state['active'] is True
        assert ctrl.last_pass_state == 'DECISION_ACTIVE'

        divergent = _make_controller(pass_decision=True)
        divergent_context = dict(context)
        divergent_context['cars'] = [
            dict(driver_id='OTHER', s=target_s, lat=0.0, speed=20.0)]
        divergent.action([(target_s, 0.0, 20.0)],
                         pass_decision_context=divergent_context)
        assert divergent._pass_decision_state['active'] is True
        assert divergent._pass_decision_state['target_id'] == 'TGT'

    def test_n_blocked_ticks_have_identical_off_on_runtime_state(self):
        off = _make_controller(pass_decision=False)
        on = _make_controller(pass_decision=True)
        off_legacy = off._pass_layer
        on_legacy = on._pass_layer
        off_calls, on_calls = [], []
        off._pass_layer = lambda *args: (off_calls.append(args),
                                         off_legacy(*args))[1]
        on._pass_layer = lambda *args: (on_calls.append(args),
                                        on_legacy(*args))[1]
        on._pass_decision_layer = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError('decisão nova executada antes do primeiro engage'))
        traffic = [(220.0, 0.0, 20.0)]
        for tick in range(25):
            ctx = _context(now=55.0 + tick * 0.1, allowed=True,
                           sample=(tick % 2 == 0))
            assert on.pass_decision_sustained_target(
                [dict(t_s=ctx['t_s'], s_ego=100.0, lat_ego=0.0,
                      v_ego=21.0, cars=ctx['cars'], track_len_s=1000.0)] * 15,
                allowed=True) is None
            off_action = off.action(traffic)
            on_action = on.action(traffic, pass_decision_context=ctx)
            np.testing.assert_array_equal(off_action, on_action)
            assert off_calls[-1] == on_calls[-1]
            assert _runtime_state_sha(off) == _runtime_state_sha(on)

    def test_sustained_predicate_is_pure_and_requires_same_target(self):
        ctrl = _make_controller(pass_decision=True)
        _, ego_s, _, _ = ctrl.env._project_on_path(200.0, 0.0)
        target_s = (ego_s + 20.0) % ctrl.env._track_len_s
        from backend.model_train.reference_controller import signed_dist_s
        assert signed_dist_s(target_s, ego_s, ctrl.env._track_len_s) == pytest.approx(20.0)

        samples = []
        for i in range(15):
            samples.append(dict(
                t_s=61.0 + i * 0.2, s_ego=ego_s, lat_ego=0.0,
                v_ego=21.0, track_len_s=ctrl.env._track_len_s,
                cars=[dict(driver_id='TGT', s=target_s, lat=0.0, speed=20.0)]))
        before = _runtime_state_sha(ctrl)
        assert ctrl.pass_decision_sustained_target(samples, allowed=True) == 'TGT'
        assert ctrl.pass_decision_sustained_target(samples, allowed=False) is None
        samples[-1]['cars'][0]['driver_id'] = 'OTHER'
        assert ctrl.pass_decision_sustained_target(samples, allowed=True) is None
        assert _runtime_state_sha(ctrl) == before


class TestLeaderYieldSynthetic:
    def test_leader_yield_engages_passes_and_returns(self):
        leader = _make_controller(pass_decision=False, leader_yield=True)
        _, leader_s, _, _ = leader.env._project_on_path(200.0, 0.0)
        follower_s = (leader_s - 10.0) % leader.env._track_len_s
        cars = [dict(driver_id='FOLLOW', s=follower_s, lat=0.0,
                     speed=30.0, cum_dist=990.0)]
        context = dict(
            t_s=61.0, leader_yield_allowed=True,
            leader_yield_engage_follower='FOLLOW',
            leader_yield_cars=cars, leader_yield_contact_pairs=set(),
            leader_yield_ego_cum=1000.0, leader_yield_follower_cum=990.0,
            track_len_s=leader.env._track_len_s, half_width=6.0)
        leader.action([(follower_s, 0.0, 25.0)],
                      pass_decision_context=context)
        assert leader._leader_yield_state['active'] is True
        assert abs(leader._leader_yield_state['target_lat']) >= 3.5

        context['leader_yield_engage_follower'] = None
        context['leader_yield_follower_cum'] = 1010.0
        leader.action([(follower_s, 0.0, 25.0)],
                      pass_decision_context=context)
        assert leader._leader_yield_state['active'] is False
        assert leader._leader_yield_stats['consumed'] == 1

    def test_parity_audit_synthetic_selftest_does_not_open_race_csvs(self):
        import importlib.util

        path = PROJECT_ROOT / 'backend' / 'scripts' / 'experiments' / 'passing' / 'pass_parity_1_audit.py'
        spec = importlib.util.spec_from_file_location(
            'pass_parity_1_audit', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._selftest()

    def test_only_professor_mixed_arm_gets_follow_group(self):
        from backend.model_train.race_diagnostic import parse_mixed, assign_groups
        groups = parse_mixed('professor:2,edge:8', n_total=10)
        assignment = assign_groups(list('ABCDEFGHIJ'), groups)
        assert [d for d in 'ABCDEFGHIJ' if assignment[d] == 'professor'] == ['A', 'B']
        assert all(assignment[d] == 'edge' for d in 'CDEFGHIJ')
