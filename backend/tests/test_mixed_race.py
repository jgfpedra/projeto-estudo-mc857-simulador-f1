"""Testes mínimos do campo MISTO (A2 FASE 5): parse de --mixed, atribuição
de grupos e resumo por grupo."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend'),
          str(PROJECT_ROOT / 'backend' / 'model_train')):
    if p not in sys.path:
        sys.path.insert(0, p)

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'race_diag_mod', PROJECT_ROOT / 'backend' / 'model_train' / 'race_diagnostic.py')
# race_diagnostic importa pybullet indiretamente (run_race_10_cars) — só
# carregamos as funções PURAS via exec seção se o import completo pesar;
# aqui o import completo funciona no ambiente do projeto.
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


class TestParseMixed:
    def test_valid(self):
        assert rd.parse_mixed('traffic:2,edge:8') == {'traffic': 2, 'edge': 8}
        assert rd.parse_mixed('edge:10') is None or True  # edge:10 soma 10? sim
        assert rd.parse_mixed('edge:10') == {'edge': 10}

    def test_none_spec(self):
        assert rd.parse_mixed('') is None
        assert rd.parse_mixed(None) is None

    def test_invalid_sum(self):
        with pytest.raises(ValueError, match='soma'):
            rd.parse_mixed('traffic:2,edge:7')

    def test_invalid_group(self):
        with pytest.raises(ValueError, match='desconhecido'):
            rd.parse_mixed('foo:2,edge:8')

    def test_invalid_zero(self):
        with pytest.raises(ValueError, match='> 0'):
            rd.parse_mixed('traffic:0,edge:10')

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="':'"):
            rd.parse_mixed('traffic2edge8')


class TestAssignGroups:
    def test_first_n_traffic(self):
        ids = list('ABCDEFGHIJ')
        g = rd.assign_groups(ids, {'traffic': 2, 'edge': 8})
        assert g['A'] == 'traffic' and g['B'] == 'traffic'
        assert all(g[x] == 'edge' for x in 'CDEFGHIJ')
        assert set(g.values()) == {'traffic', 'edge'}


class TestHoldAt:
    """B3.3d (FASE 5): --hold-at congela um carro na linha central."""

    def _ctrl_tables(self):
        """Tabelas sintéticas: reta ao longo do eixo x, 100 m, segmentos de 10 m."""

        class C:
            pass
        c = C()
        c._A = np.array([[10.0 * i, 0.0] for i in range(10)])
        c._AB = np.roll(c._A, -1, axis=0) - c._A
        c._seg_len = np.hypot(c._AB[:, 0], c._AB[:, 1])
        c._seg_cum = np.concatenate([[0.0], np.cumsum(c._seg_len)])[:-1]
        c._track_len_s = float(c._seg_len.sum())
        return c

    def test_pose_at_s_on_synthetic_straight(self):
        c = self._ctrl_tables()
        x, y, yaw = rd._pose_at_s(c, 35.0)
        assert x == pytest.approx(35.0) and y == pytest.approx(0.0)
        assert yaw == pytest.approx(0.0)
        # wrap: s no fim da pista volta ao início
        x2, y2, _ = rd._pose_at_s(c, c._track_len_s + 5.0)
        assert x2 == pytest.approx(5.0)

    @pytest.mark.slow
    def test_hold_car_stays_at_s(self):
        """Smoke físico: corrida de 30 ticks com --hold-at — o carro held tem
        s ~constante no CSV (variação < 2 m)."""
        import subprocess, sys
        cmd = [sys.executable, 'model_train/race_diagnostic.py',
               '--actor', 'model_train/v10_dagger/dagger_actor_best.keras',
               '--obs-mode', 'edge', '--ticks', '30', '--laps', '99',
               '--track', 'interlagos', '--hold-at', '1200',
               '--out', '/tmp/hold_smoke.csv', '--seed', '0']
        subprocess.run(cmd, cwd=str(PROJECT_ROOT / 'backend'), check=True,
                      capture_output=True, timeout=600)
        df = pd.read_csv('/tmp/hold_smoke.csv')
        held = df[df.drv == 'GAS'].sort_values('tick')   # último do grid
        assert held.s.max() - held.s.min() < 2.0, \
            f"carro held andou: [{held.s.min():.1f}, {held.s.max():.1f}]"
        assert (held.speed < 2.0).all()


class TestMixedSummary:
    def _df(self):
        # 2 traffic (A, B) + 2 edge (C, D); 121 ticks de 0.2s (24 s) — mas
        # contato precisa de t>60s p/ pós-largada: usamos t_s explícito alto
        rows = []
        for t in range(120):
            t_s = t * 0.2 + 100.0          # tudo já pós-largada
            for d, s in (('A', 1000.0), ('B', 1050.0), ('C', 1005.0), ('D', 2000.0)):
                rows.append(dict(tick=t, t_s=t_s, drv=d, s=s,
                                 speed=30.0, lat=0.5, car_car=0, offtrack=0))
        # contato A-C (próximos em s) no tick 50; hesitação de C (v<2 x3)
        for r in rows:
            if r['tick'] == 50 and r['drv'] in ('A', 'C'):
                r['car_car'] = 2
        for r in rows:
            if 60 <= r['tick'] <= 64 and r['drv'] == 'C':
                r['speed'] = 1.0
        # uma volta de B (wrap s: 4200 -> 100)
        for r in rows:
            if r['drv'] == 'B':
                r['s'] = 4200.0 if r['tick'] < 60 else 100.0
        return pd.DataFrame(rows)

    def test_summary_counts(self):
        groups = {'A': 'traffic', 'B': 'traffic', 'C': 'edge', 'D': 'edge'}
        ms = rd.mixed_summary(self._df(), groups)
        # contato A-C: 1 amostra para cada lado (A traffic, C edge)
        assert ms['traffic']['contacts'] == 1
        assert ms['edge']['contacts'] == 1
        assert ms['post_launch'] == 2          # ambas as amostras t_s>60
        assert ms['pair_contacts'] == {'edge-traffic': 1}
        # hesitação: C (edge) 1 episódio; A/B/D nenhuma
        assert ms['edge']['hesitations'] == 1
        assert ms['traffic']['hesitations'] == 0
        # volta de B: 1 wrap; rolante precisa de 2+ wraps (aqui só 1 → None)
        assert ms['traffic']['laps'] == 1
        assert ms['traffic']['rolling_med'] is None
        assert ms['edge']['laps'] == 0


class TestUpdateLastGood:
    """PASSO 0.1 (FASE 6): last_good só avança após o gate PASSAR — o bug
    fez a linha [FINAL] do train.log apontar um checkpoint REPROVADO."""

    def test_failed_gate_keeps_previous_green(self):
        from backend.model_train.train_dagger import update_last_good
        prev = dict(stage=0, n_traffic=0, path='best_s0', iter=2)
        out = update_last_good(prev, ok_gate=False,
                               stage_info=dict(stage=1, n_traffic=4,
                                               path='best_s1', iter=3))
        assert out == prev, "gate reprovado deve MANTER o estágio verde anterior"

    def test_passed_gate_advances(self):
        from backend.model_train.train_dagger import update_last_good
        prev = dict(stage=0, path='best_s0')
        out = update_last_good(prev, ok_gate=True,
                               stage_info=dict(stage=1, path='best_s1'))
        assert out['stage'] == 1 and out['path'] == 'best_s1'

    def test_none_stays_none_on_failure(self):
        from backend.model_train.train_dagger import update_last_good
        assert update_last_good(None, ok_gate=False, stage_info=dict(x=1)) is None
