"""PISTAS_EXPAND_1 (prereg 8afec70 §5) — testes estruturais DATA-DRIVEN.

O manifest é a verdade do ciclo (PATCH_A FIXAÇÃO 1: congelamento seletivo
→ os testes verificam MANIFEST × ARQUIVOS × LOADER, não quantas pistas
terminaram em cada status):

  OK           → mirror {key}_v2.json no path frozen (carrega case-exata)
  COMPARADO    → candidato (b) em experiments/candidatos/ (v1 intacto)
  AGUARDA_DONO → candidato (c) aprovado nos gates, FORA do frozen
  FAILED       → gates reprovaram: SEM mirror (resultado honesto)
  NAO_EXECUTADO→ stretch sem teto: SEM artefato

Anti-H-1 estrutural: a chave case-exata documentada no manifest é a que o
loader resolve (track_resolution.py:212-216 — key VERBATIM, prioridade
{key}_v2). Anti-substituição: nenhum {key}_v2.json no path frozen fora
das linhas OK."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
EXP = BACKEND / "experiments" / "pistas-expand-1"
MANIFEST = EXP / "manifest_pistas_expand_1.csv"
FROZEN = BACKEND / "model_train" / "tracks_frozen"

# v2 pré-existentes ao ciclo (canônicos + variante SF) — autorizados
V2_PRE_EXISTENTES = {"interlagos", "Monaco", "Spa", "interlagos_sf729"}


def _rows():
    assert MANIFEST.exists(), f"manifest ausente: {MANIFEST}"
    with open(MANIFEST) as f:
        return list(csv.DictReader(f))


def _embedded_sha(data: dict) -> str:
    """sha256 EXATAMENTE como o loader verifica (track_resolution.py:227)."""
    raw = json.dumps({k: v for k, v in data.items() if k != "sha256"},
                     sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _candidate_file(row):
    key = row["chave_case_exata"]
    if row["status"] == "COMPARADO":
        return EXP / "candidatos" / f"{key}_candidato_openf1.json"
    if row["status"] == "AGUARDA_DONO":
        return EXP / "candidatos" / f"{key}_v2_candidato.json"
    return None


def _artefatos():
    """(row, arquivo) de TODO artefato produzido no ciclo (OK + candidatos)."""
    out = []
    for r in _rows():
        if r["status"] == "OK":
            out.append((r, FROZEN / f"{r['chave_case_exata']}_v2.json"))
        elif r["status"] in ("COMPARADO", "AGUARDA_DONO"):
            out.append((r, _candidate_file(r)))
    return out


class TestPE1Carrega:
    def test_t_pe1_carrega(self):
        """§5.1: cada mirror NOVO (status OK) carrega via load_track_frozen
        com a case EXATA documentada (anti-H-1); wp == manifest. Estrutural:
        nenhum {key}_v2.json no path frozen sem linha OK correspondente."""
        from backend.domain.track_resolution import load_track_frozen
        ok = [r for r in _rows() if r["status"] == "OK"]
        for r in ok:
            t = load_track_frozen(r["chave_case_exata"], strict=True)
            assert len(t.waypoints) == int(r["wp"]), \
                f"{r['pista']}: wp {len(t.waypoints)} != manifest {r['wp']}"
        # anti-substituição: todo _v2.json no frozen é pre-existente OU OK
        atuais = {p.stem[:-3] for p in FROZEN.glob("*_v2.json")}
        autorizadas = V2_PRE_EXISTENTES | {r["chave_case_exata"] for r in ok}
        assert atuais <= autorizadas, \
            f"v2 NÃO-autorizado no path frozen: {atuais - autorizadas}"


class TestPE1Identidade:
    def test_t_pe1_identidade(self):
        """§5.2: track_identity de cada OK: fonte=openf1 e |ΔL| < 1% do
        oficial da tabela §1 (L_oficial_m do manifest)."""
        from backend.domain.track_resolution import (load_track_frozen,
                                                     track_identity)
        for r in [x for x in _rows() if x["status"] == "OK"]:
            t = load_track_frozen(r["chave_case_exata"], strict=True)
            ident = track_identity(t, requested=r["chave_case_exata"],
                                   fonte="openf1")
            assert ident["fonte"] == "openf1", ident
            dpct = (abs(ident["length_m"] - float(r["L_oficial_m"]))
                    / float(r["L_oficial_m"]))
            assert dpct < 0.01, f"{r['pista']}: Δ {dpct:.3%} >= 1%"


class TestPE1Manifest:
    def test_t_pe1_manifest(self):
        """§5.3: manifest ↔ arquivos: todo candidato JSON tem linha; todo OK
        tem mirror no frozen; sha256 RECALCULADO == manifest == embutido
        (determinístico entre execuções); FAILED/NAO_EXECUTADO sem v2 no
        frozen e sem sha (resultado honesto)."""
        rows = _rows()
        by_key = {r["chave_case_exata"]: r for r in rows}
        assert len(by_key) == len(rows), "chave duplicada no manifest"
        # candidato SEM linha = órfão (proibido)
        cand_dir = EXP / "candidatos"
        if cand_dir.exists():
            for f in sorted(cand_dir.glob("*.json")):
                esperados = ({f"{k}_candidato_openf1" for k in by_key}
                             | {f"{k}_v2_candidato" for k in by_key})
                assert f.stem in esperados, f"candidato sem linha no manifest: {f.name}"
        for r in rows:
            key = r["chave_case_exata"]
            v2 = FROZEN / f"{key}_v2.json"
            if r["status"] == "OK":
                assert v2.exists(), f"OK sem mirror: {v2}"
                data = json.loads(v2.read_text())
                sha = _embedded_sha(data)
                assert sha == data["sha256"] == r["sha256"], \
                    f"{key}: sha {sha} != manifest {r['sha256']}"
            elif r["status"] in ("COMPARADO", "AGUARDA_DONO"):
                cf = _candidate_file(r)
                assert cf is not None and cf.exists(), \
                    f"{key}: status {r['status']} sem candidato"
                data = json.loads(cf.read_text())
                sha = _embedded_sha(data)
                assert sha == data["sha256"] == r["sha256"], \
                    f"{key}: sha candidato {sha} != manifest {r['sha256']}"
                assert not v2.exists(), \
                    f"{key}: candidato PROIBIDO no path frozen (substituição)"
            else:  # FAILED / NAO_EXECUTADO
                assert not v2.exists(), f"{key}: {r['status']} mas v2 no frozen"
                assert not r["sha256"], f"{key}: {r['status']} não deve ter sha"


class TestPE1Schema:
    def test_t_pe1_schema(self):
        """§5.4: TODO artefato produzido (OK + candidatos): contorno fecha
        (primeiro≈último wp ≤ 20 m), espaçamento médio 10 m ± margem,
        n_wp plausível [L/12, L/8]."""
        artefatos = _artefatos()
        assert artefatos, "nenhum artefato produzido no ciclo"
        for r, f in artefatos:
            assert f is not None and f.exists(), f"{r['pista']}: {f}"
            data = json.loads(f.read_text())
            wps = np.asarray(data["waypoints"], dtype=np.float64)
            closed = np.vstack([wps, wps[:1]])
            dd = np.hypot(*np.diff(closed, axis=0).T)
            L = float(dd.sum())
            gap = float(np.hypot(*(wps[0] - wps[-1])))
            assert gap <= 20.0, f"{r['pista']}: fechamento {gap:.1f} m > 20"
            assert 8.5 <= float(dd.mean()) <= 11.5, \
                f"{r['pista']}: espaçamento médio {dd.mean():.2f} m"
            assert L / 12.0 <= len(wps) <= L / 8.0, \
                f"{r['pista']}: n_wp {len(wps)} fora de [{L/12:.0f},{L/8:.0f}]"
