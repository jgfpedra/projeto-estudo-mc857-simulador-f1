"""LARGADA-1 0-b — DOC-INTEGRITY dos arquivos de estado.

O mishap de header aconteceu 2× na história do projeto (um header de seção
sobrescrito por um edit deixa o corpo antigo ÓRFÃO embaixo de conteúdo novo).
Contratos testados (fail rápido na próxima edição mal-aplicada):
- PROJECT_STATE.md: header "> Última atualização: **...**" presente e fecha
  '**'; cada linha da cadeia "(anterior:" é COMPLETA (conteúdo + ponteiro
  "Ver ..." + fecha parêntese) — truncada/sobrescrita = FAIL; o bloco do
  topo (antes da 1ª seção "## ") só contém títulos/citações — linha comum
  no topo = corpo órfão.
- MEMORY.md (raiz): existe, aponta para o PROJECT_STATE.md, e toda linha
  de conteúdo termina com "." (linha truncada = edição mal-aplicada).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PS = ROOT / "backend" / "PROJECT_STATE.md"
MEM = ROOT / "MEMORY.md"


def test_state_files_doc_integrity():
    # --- PROJECT_STATE.md ---
    lines = PS.read_text().splitlines()
    assert lines[0].startswith("# PROJECT_STATE.md"), "título ausente"
    upd = [l for l in lines if l.startswith("> Última atualização:")]
    assert upd, "header 'Última atualização' ausente"
    assert upd[0].rstrip().endswith("**"), "update header não fecha com '**'"
    ant = [l for l in lines if l.startswith("> (anterior:")]
    assert ant, "cadeia '(anterior:)' ausente"
    for l in ant:
        assert re.search(r"Ver .+\)\*{0,2}$", l.rstrip()), \
            f"cadeia '(anterior:)' incompleta/órfã: {l[:80]}..."
    first_section = next(i for i, l in enumerate(lines) if l.startswith("## "))
    for l in lines[:first_section]:
        if l.strip():
            assert l.startswith("#") or l.startswith(">"), \
                f"corpo órfão no bloco do topo (sem header próprio): {l[:80]}"
    # --- MEMORY.md ---
    mtext = MEM.read_text()
    assert "PROJECT_STATE.md" in mtext, "MEMORY.md sem ponteiro para o estado vivo"
    for l in mtext.splitlines():
        s = l.rstrip()
        if s and not s.startswith("#"):
            assert s.endswith("."), f"linha de MEMORY.md truncada: {s[:80]}"
