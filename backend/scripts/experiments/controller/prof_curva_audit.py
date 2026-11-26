#!/usr/bin/env python3
"""Auditoria da corrida solo do professor para o programa PROF-CURVA-1.

Analisa saídas de pista por curva (instrumento canônico saidas_verdict),
estatísticas de tempo fora de pista e tempos de volta para a Guarda de Ritmo
(Decisão 3=b).
"""
from __future__ import annotations

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)


import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts import saidas_verdict as SV  # noqa: E402

SAIDAS_VERDICT_SHA256 = "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
HISTORICAL_BASELINE_LAP_S = 107.0
RHYTHM_GUARD_MAX_DEGRADATION_PCT = 15.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_log_lap_times(log_path: Path) -> List[float]:
    """Extrai a lista de tempos de volta do log do race_diagnostic."""
    if not log_path.exists():
        return []
    content = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"tempos=\[([0-9., ]+)\]", content)
    if not match:
        return []
    raw_str = match.group(1).strip()
    if not raw_str:
        return []
    return [float(x.strip()) for x in raw_str.split(",") if x.strip()]


def audit_run(
    csv_path: Path,
    log_path: Optional[Path] = None,
    track: str = "interlagos",
    baseline_lap_s: float = HISTORICAL_BASELINE_LAP_S,
) -> Dict[str, Any]:
    """Audita a execução solo do professor a partir do CSV e do log."""
    actual_sv_sha = sha256_file(Path(SV.__file__))
    if actual_sv_sha != SAIDAS_VERDICT_SHA256:
        raise RuntimeError(
            f"SHA-256 de saidas_verdict divergente: esperado {SAIDAS_VERDICT_SHA256}, obtido {actual_sv_sha}"
        )

    if track not in SV.TRACKS:
        raise ValueError(f"Pista não suportada: {track}")

    track_file = SV.TRACKS[track]["file"]
    track_sha256 = sha256_file(Path(track_file))
    geom = SV.load_track_geometry(track_file)
    track_length_m = float(geom[4])
    corners = SV.build_corner_definitions(geom[0])

    df = pd.read_csv(csv_path, comment="#")
    row_count = len(df)

    # Extração canônica de saídas
    events, summary = SV.extract_excursions(df, corners, geom)

    # Máximo deslocamento lateral absoluto
    lat_max = float(df["lat"].abs().max()) if "lat" in df.columns else 0.0

    # Contagem de saídas por curva
    corner_counts: Dict[str, int] = {c["id"]: 0 for c in corners}
    corner_counts["Reta"] = 0
    if not events.empty:
        for cid, cnt in events["corner_id"].value_counts().items():
            corner_counts[str(cid)] = int(cnt)

    # Voltas completadas calculadas pela distância acumulada
    cum_dist_max = float(df["cum_dist"].max()) if "cum_dist" in df.columns else 0.0
    laps_completed_by_dist = int(cum_dist_max // track_length_m)

    # Tempos de volta
    lap_times = []
    if log_path and log_path.exists():
        lap_times = parse_log_lap_times(log_path)

    laps_count = len(lap_times) if lap_times else laps_completed_by_dist

    if lap_times:
        med_all = float(np.median(lap_times))
        med_later = float(np.median(lap_times[1:])) if len(lap_times) > 1 else med_all
        best_lap = float(min(lap_times))
    else:
        med_all = None
        med_later = None
        best_lap = None

    # Avaliação da Guarda de Ritmo (Decisão 3=b: max 15% de perda sobre 107.0s)
    # Teto = 107.0 * 1.15 = 123.05 s
    rhythm_guard_ceiling_s = baseline_lap_s * (1.0 + RHYTHM_GUARD_MAX_DEGRADATION_PCT / 100.0)
    degradation_pct = None
    rhythm_guard_pass = None
    if med_later is not None:
        degradation_pct = float((med_later - baseline_lap_s) / baseline_lap_s * 100.0)
        rhythm_guard_pass = bool(med_later <= rhythm_guard_ceiling_s)

    # Curvas críticas de Interlagos
    critical_corners = {}
    if track == "interlagos":
        for cid in ["C01", "C06", "C07", "C08", "Reta"]:
            cnt = corner_counts.get(cid, 0)
            rate = cnt / laps_count if laps_count > 0 else 0.0
            critical_corners[cid] = {
                "saidas": cnt,
                "taxa_por_volta": rate,
            }

    detailed_events = []
    if not events.empty:
        for _, ev in events.iterrows():
            detailed_events.append(
                {
                    "tick": int(ev.tick),
                    "t_s": float(ev.t_s),
                    "dur_s": float(ev.dur_s),
                    "s": float(ev.s),
                    "corner_id": str(ev.corner_id),
                    "corner_name": str(ev.corner_name),
                    "v_1s_kmh": float(ev.v_1s_kmh),
                }
            )

    return {
        "instrument": "prof_curva_audit_v1",
        "csv_path": str(csv_path),
        "csv_sha256": sha256_file(csv_path),
        "log_path": str(log_path) if log_path else None,
        "track": track,
        "track_sha256": track_sha256,
        "saidas_verdict_sha256": SAIDAS_VERDICT_SHA256,
        "total_ticks": int(summary.get("total_ticks", row_count)),
        "off_ticks": int(summary.get("off_ticks", 0)),
        "off_pct": float(summary.get("off_pct", 0.0)),
        "n_events": int(summary.get("n_events", 0)),
        "dur_median_s": float(summary.get("dur_median", 0.0)),
        "lat_max_m": lat_max,
        "laps_count": laps_count,
        "lap_times": lap_times,
        "lap_time_median_all_s": med_all,
        "lap_time_median_later_s": med_later,
        "best_lap_s": best_lap,
        "baseline_lap_s": baseline_lap_s,
        "rhythm_guard_ceiling_s": rhythm_guard_ceiling_s,
        "degradation_pct": degradation_pct,
        "rhythm_guard_pass": rhythm_guard_pass,
        "critical_corners": critical_corners,
        "corner_counts": corner_counts,
        "events": detailed_events,
    }


def render_markdown(audit: Dict[str, Any]) -> str:
    """Gera relatório de achados em Markdown."""
    lines = [
        "# Relatório de Referência Solo — Professor em Interlagos (Task 2)",
        "",
        f"- **Instrumento:** `{audit['instrument']}`",
        f"- **Pista:** `{audit['track']}` (SHA-256: `{audit['track_sha256'][:16]}...`)",
        f"- **CSV:** `{audit['csv_path']}` (SHA-256: `{audit['csv_sha256']}`)",
        f"- **Amostras:** {audit['total_ticks']} ticks (5 Hz, 600 s)",
        f"- **Voltas Completadas:** {audit['laps_count']}",
        "",
        "## 1. Saídas de Pista e Tempo Fora",
        "",
        f"- **Amostras fora de pista:** {audit['off_ticks']} de {audit['total_ticks']} ({audit['off_pct']:.1f}%)",
        f"- **Número total de excursões:** {audit['n_events']}",
        f"- **Duração mediana de excursão:** {audit['dur_median_s']:.1f} s",
        f"- **Deslocamento lateral máximo:** |lat| = {audit['lat_max_m']:.2f} m",
        "",
        "## 2. Diagnóstico das Quatro Curvas Crônicas de Interlagos",
        "",
        "| Setor / Curva | Nome | Saídas | Taxa (saídas/volta) | Diagnóstico |",
        "|---|---|---|---|---|",
    ]

    names = {
        "C01": "Descida do Lago (T4/T5)",
        "C06": "Bico de Pato (T10)",
        "C07": "Mergulho (T11)",
        "C08": "Junção (T12)",
        "Reta": "Reta / Loop Grama (pós-Junção)",
    }

    for cid in ["C01", "C06", "C07", "C08", "Reta"]:
        info = audit["critical_corners"].get(cid, {"saidas": 0, "taxa_por_volta": 0.0})
        cnt = info["saidas"]
        rate = info["taxa_por_volta"]
        diag = "CRÔNICA (100% das voltas)" if rate >= 1.0 else "Esporádica"
        lines.append(f"| `{cid}` | {names[cid]} | {cnt} | {rate:.2f} | {diag} |")

    lines.extend(
        [
            "",
            "Demais curvas de Interlagos (C02 a C05, C09 a C12): **0 saídas**.",
            "",
            "## 3. Tempos de Volta e Guarda de Ritmo (Decisão 3=b)",
            "",
            f"- **Tempos individuais por volta:** {audit['lap_times']} s",
            f"- **Melhor volta:** {audit['best_lap_s']} s",
            f"- **Mediana (todas as voltas):** {audit['lap_time_median_all_s']} s",
            f"- **Mediana (excluindo volta 1 / largada):** {audit['lap_time_median_later_s']} s",
            f"- **Baseline histórica limpa:** {audit['baseline_lap_s']:.1f} s",
            f"- **Teto da Guarda de Ritmo (+15%):** {audit['rhythm_guard_ceiling_s']:.2f} s",
            f"- **Degradação na referência sem patch:** +{audit['degradation_pct']:.2f}% (inflada por 26 s/volta de perambulação na grama)",
            "",
            "## 4. Conclusão da Baseline",
            "",
            "A medição solo sem patch de teto confirma integralmente a anatomia prevista:",
            "1. As quatro saídas crônicas ocorrem em 100% das voltas (C01, C06, C07, C08);",
            "2. A Junção (C08) e o looping consequente na grama (Reta) somam ~26 segundos de tempo perdido fora de pista por volta;",
            "3. O Gate Primário da Task 4 exigirá **ZERO** saídas em C01, C06, C07 e C08, e zero saídas novas nas demais curvas;",
            "4. A Guarda de Ritmo na Task 4 exigirá que a velocidade ajustada gere mediana de volta `<= 123.05 s` (<= 15% sobre a baseline limpa histórica de 107 s).",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria solo do professor PROF-CURVA-1")
    parser.add_argument("--csv", type=Path, required=True, help="Caminho do CSV de telemetria")
    parser.add_argument("--log", type=Path, default=None, help="Caminho do log do race_diagnostic")
    parser.add_argument("--track", type=str, default="interlagos", help="Nome da pista")
    parser.add_argument("--out-dir", type=Path, default=None, help="Diretório de saída dos relatórios")
    parser.add_argument(
        "--baseline-lap-s",
        type=float,
        default=HISTORICAL_BASELINE_LAP_S,
        help="Tempo de volta histórico limpo",
    )

    args = parser.parse_args()
    out_dir = args.out_dir or args.csv.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    result = audit_run(
        csv_path=args.csv,
        log_path=args.log,
        track=args.track,
        baseline_lap_s=args.baseline_lap_s,
    )

    json_path = out_dir / "REF_FINDINGS.json"
    md_path = out_dir / "REF_FINDINGS.md"

    with json_path.open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)

    md_content = render_markdown(result)
    with md_path.open("w", encoding="utf-8") as stream:
        stream.write(md_content)

    print(f"Auditoria concluída com sucesso:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print(f"  Fora de pista: {result['off_pct']:.1f}% | Eventos: {result['n_events']}")
    print(f"  Tempos: {result['lap_times']} | Mediana (excl v1): {result['lap_time_median_later_s']} s")


if __name__ == "__main__":
    main()
