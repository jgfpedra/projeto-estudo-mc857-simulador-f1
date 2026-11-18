"""ANTI-D3-1 — probe pós-veredito READ-ONLY (marcado; zero runs; veredito FAIL já emitido).

Perguntas ao dado JÁ commitado (nenhuma corrida nova):
  Q-A: o progress-guard ENGAJOU nas hesitações? (trigger = 5 ticks
       consecutivos com Δcum<0,5m e g>0,01; fade visível = colapso do
       g_gate do CSV, que carrega o g EFETIVO pós-fade)
  Q-B: durações guard-ON vs guard-OFF (f4v15) e resgate (episódio termina
       com g_gate colapsado)

Limitação do proxy (documentada): o CSV NÃO exporta as obs 34-46 (d_min),
então o gate NOMINAL não é recomputável; o contador usa g_gate>0,01 como
proxy do branch nominal>0,01 — EXATO até o 1º fade completo (quando
g_gate→0 o proxy reseta; disparos sustentados são sub-contados). O
GUARD-OFF (f4v15) tem g_gate == nominal em todo tick → proxy exato; os
disparos dele são CONTRAFACTUAIS mecânicos (replay das constantes).
Proxy adicional (v2, pós-1º-run): o contador do proxy pula o tick 0 (o
guard conta o 1º predict com delta=0 pela inicialização last_cum=None) —
disparos de LARGADA são invisíveis a ele; e com fade ativo g_gate→0 cega
o proxy. Por isso a §Divergência usa as DUAS corridas: prefixo idêntico
⇒ g_gate OFF == nominal ON; o tick da 1ª diferença = 1º disparo (fade
0,2 ⇒ razão ON/OFF = 0,8); razões 0,64/0,40/0,20 nos ticks seguintes =
rampa do fade.

  .venv/bin/python scripts/experiments/anti_d3/anti_d3_probe.py \
      experiments/anti-d3-1/2_allcomposite.csv \
      experiments/f4v15-wiring/2_allcomposite.csv
"""

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)

import sys

import numpy as np
import pandas as pd


def per_driver_arrays(df):
    out = {}
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        out[drv] = dict(drv=drv, t=g.t_s.values, v=g.speed.values,
                        s=g.s.values, cum=g.cum_dist.values,
                        off=g.offtrack.values, gg=g.g_gate.values,
                        cc=g.car_car.values)
    return out


def episodes(arr):
    """Critério do veredito (verbatim): on-track v<0,5; janela 0,3-3s; t>20s."""
    eps, v, tt, off = [], arr['v'], arr['t'], arr['off']
    i, n = 0, len(v)
    while i < n:
        if v[i] < 0.5 and tt[i] > 20 and off[i] == 0:
            j = i
            while j < n and v[j] < 0.5 and off[j] == 0:
                j += 1
            d = (tt[min(j, n - 1)] - tt[i]) if j > i else 0
            if 0.3 <= d <= 3.0:
                eps.append((i, j, d))
            i = max(j, i + 1)
        else:
            i += 1
    return eps


def trigger_ticks(arr):
    """Proxy do contador no_prog: tick onde 5 consecutivos Δcum<0,5m com
    g_gate>0,01 completam a janela (espelha run_race_10_cars.py:778-795)."""
    cum, gg = arr['cum'], arr['gg']
    fires, c = [], 0
    for i in range(1, len(cum)):
        if cum[i] - cum[i - 1] < 0.5 and gg[i] > 0.01:
            c += 1
            if c == 5:
                fires.append(i)
        else:
            c = 0
    return fires


def summarize(path, label, counterfactual):
    df = pd.read_csv(path, comment='#')
    arrs = per_driver_arrays(df)
    n_ep, durs, rows = 0, [], []
    n_fire, n_fire_in_ep = 0, 0
    cc_total = int(df.car_car.sum())
    cc_near_fire = 0
    for arr in arrs.values():
        eps = episodes(arr)
        fires = trigger_ticks(arr)
        n_fire += len(fires)
        near = set()
        for f in fires:
            for k in range(f, min(len(arr['cc']), f + 10)):  # ≤2s pós-disparo
                near.add(k)
        cc_near_fire += int(sum(arr['cc'][k] for k in near))
        n_ep += len(eps)
        for num, (i0, i1, d) in enumerate(eps, 1):
            durs.append(d)
            win = [f for f in fires if i0 - 15 <= f < i1]
            n_fire_in_ep += len(win)
            f0 = win[0] if win else None
            gg = arr['gg']
            g0, gend = float(gg[i0]), float(gg[min(i1, len(gg) - 1)])
            gmin = float(gg[i0:i1].min()) if i1 > i0 else g0
            collapsed = gend < 0.5 * max(g0, 0.01)
            if f0 is not None:
                trig = "t_ep%+.1fs" % (arr['t'][f0] - arr['t'][i0])
            else:
                trig = "nunca"
            rows.append(
                "  #%2d %s t=%7.1fs dur=%4.1fs s=%6.0fm g0=%4.2f "
                "g_end=%4.2f g_min=%4.2f trig=%-12s fim=%s"
                % (num, arr['drv'], arr['t'][i0], d, arr['s'][i0], g0,
                   gend, gmin, trig, "COLAPSADO" if collapsed else "platô"))
    durs = np.array(durs)
    tag = " (contrafactual mecânico)" if counterfactual else ""
    print(label, path)
    print("  hesitações: %d | duração med %.2fs min %.2f máx %.2f"
          % (n_ep, np.median(durs), durs.min(), durs.max()))
    for r in rows:
        print(r)
    print("  disparos de trigger na corrida%s: %d "
          "(dentro/adjacentes a hesitações: %d)"
          % (tag, n_fire, n_fire_in_ep))
    print("  cc total %d | cc em ≤2s pós-disparo: %d (%.1f%%)\n"
          % (cc_total, cc_near_fire, 100.0 * cc_near_fire / max(cc_total, 1)))


def divergence(on_path, off_path):
    """§Divergência: ground truth do 1º disparo do guard (padrão leak-check).
    Prefixo idêntico ⇒ g_gate OFF == nominal ON; 1ª diferença = 1º disparo
    (fade 0,2 → razão 0,8; depois 0,64/0,40/0,20). Divergências seguintes
    por driver = contaminação (o mundo já mudou), NÃO disparos próprios."""
    on = pd.read_csv(on_path, comment='#')
    off = pd.read_csv(off_path, comment='#')
    m = on.merge(off, on=['drv', 'tick'], suffixes=('_on', '_off'))
    m['dg'] = (m.g_gate_on - m.g_gate_off).abs()
    print("§Divergência ON vs OFF (g_gate; OFF == nominal no prefixo):")
    d = m[m.dg > 1e-6]
    if d.empty:
        print("  BIT-IDÊNTICAS — o guard nunca agiu (impossível se divergem)")
        return
    r0 = d.sort_values('tick').iloc[0]
    drv, tk = r0.drv, int(r0.tick)
    print("  1ª divergência: %s tick %d (t=%.1fs) ON=%.3f OFF=%.3f razão=%.2f"
          % (drv, tk, r0.t_s_on, r0.g_gate_on, r0.g_gate_off,
             r0.g_gate_on / max(r0.g_gate_off, 1e-9)))
    w = m[(m.drv == drv) & (m.tick >= tk - 10) & (m.tick <= tk + 8)]
    w = w.sort_values('tick')
    prev = None
    print("  janela do 1º disparo (%s): tick | Δcum(ON) | g_on | g_off | v_on | v_off"
          % drv)
    for _, r in w.iterrows():
        cum = r.cum_dist_on
        dlt = 0.0 if prev is None else cum - prev
        prev = cum
        print("    t=%5d t_s=%6.1fs Δcum=%5.2f g_on=%5.2f g_off=%5.2f "
              "v_on=%5.2f v_off=%5.2f"
              % (r.tick, r.t_s_on, dlt, r.g_gate_on, r.g_gate_off,
                 r.speed_on, r.speed_off))
    firsts = d.groupby('drv').tick.min().sort_values()
    parts = []
    for dv, tk0 in firsts.items():
        r = d[d.drv == dv].sort_values('tick').iloc[0]
        if r.g_gate_off > 0.01:
            tag = "razão=%.2f" % (r.g_gate_on / r.g_gate_off)
        else:
            tag = "g_nominal=0"
        parts.append("%s@t%d(%s)" % (dv, int(tk0), tag))
    print("  1ª divergência por driver (razão 0,80/0,60 no tick = disparo "
          "PRÓPRIO com fade 0,2/0,4; razão ≠ = contaminação): " + ", ".join(parts))
    print("  g_gate<0,01 em %% dos ticks: ON %.1f%% vs OFF %.1f%% "
          "(excesso ON ≈ fades ativos; OFF nunca teve fade)"
          % (100 * (m.g_gate_on < 0.01).mean(),
             100 * (m.g_gate_off < 0.01).mean()))
    print("  janela de largada (linhas 0,2s; g_nominal/velocidade; * = divergência):")
    for dv in firsts.index:
        w0 = m[(m.drv == dv) & (m.tick <= 12)].sort_values('tick')
        fd = int(firsts[dv])
        seq = " ".join(("*" if int(r.tick) == fd else "")
                       + "%.2f/%.0f" % (r.g_gate_off, r.speed_off)
                       for _, r in w0.iterrows())
        print("    %-4s %s" % (dv, seq))


def main(argv):
    print("=== ANTI-D3-1 probe pós-veredito (READ-ONLY; proxy documentado) ===\n")
    summarize(argv[0], "GUARD-ON :", counterfactual=False)
    summarize(argv[1], "GUARD-OFF:", counterfactual=True)
    divergence(argv[0], argv[1])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
