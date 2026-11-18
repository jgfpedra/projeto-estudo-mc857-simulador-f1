# PREREG PASS-DIAG-2 — viabilidade de fechamento e divergência pré-engajamento

**Estado:** pré-freeze; aguardando o commit do dono. Nenhum número novo de trajetória, tentativa ou gap foi aberto.  
**Escopo:** report-only; zero corridas/smokes; zero mudança de produção; suíte não reexecutada; sem promoção.  
**Retomada:** handoff `01a1748e-dd04-7902-8f8a-fb3b49324b4f`, reivindicado nesta sessão.  
**Base:** PASS-DIAG-1F, commit `40cd5bc16799afb05546011d6eeb82c17b99dd9a`; script v1.4 SHA-256 `85812034fabbb1c6a7c2d2b6f9758bbb77e3d370a5eefcd5f7f64ce5c870af9f`. O instrumento PASS-DIAG-2 é v1.5. A única mudança funcional é acrescentar Q1/Q2 e seus casos sintéticos; `run_analysis` e as saídas da 1F permanecem intactos.

## Perguntas e entradas congeladas

- **Q1:** R1 OFF e R2 ON já divergem em trajetória antes de 60 s? Em caso afirmativo, registrar o primeiro tick, campo e piloto, além do primeiro ponto por piloto. Se não houver diferença nos campos de trajetória, distinguir campos não-trajectory divergentes de pré-60 idêntico. Isso localiza divergência; não demonstra causalidade.
- **Q2:** durante cada tentativa R2, o gap assinado do alvo ao ego fecha? Ajustar uma reta no intervalo amostrado, calcular a taxa de fechamento e projetar dez segundos. Medir também, por piloto de R1, o tempo em fila próxima com pace equilibrado.

Os sete pinos são Tier B (hash de disco pré-fixado nos ciclos anteriores); os hashes abaixo são revalidados na abertura, antes da análise. Geometria permanece Tier A, validada por disco e blob do commit de proveniência `8136d54ec45f9f49b38a5893a812928474109535`.

| Entrada | SHA-256 |
|---|---|
| `experiments/pass-1/1_R1_OFF.csv` | `5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa` |
| `experiments/pass-1/1_R1_OFF.log` | `f23a79771bd9f05d8e709f9bf67a93be8a93bf2e8129403db03972b0c0c23273` |
| `experiments/pass-1/2_R2_ON.csv` | `7d2c49b9b873fc4fc4888b1413cd47ae3b9dde040a4e1af111ac246c90e0a27c` |
| `experiments/pass-1/2_R2_ON.log` | `213fb953c98e59a51e2178a9f05171560dd63ed15f675fcf6c2a86b33c783f1b` |
| `experiments/pass-1/4_AUDIT_PASS_1.json` | `347216e6cf65f109ec82d927762bab5ffefea85c4913fca024891bf05e1a134b` |
| `experiments/pass-1/5_EXECUCAO_PASS_1.md` | `e4f6ac05383d481c862cf679edac171547ccbde81c44557ecd2072f295281a67` |
| `model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |

O contexto publicado que motivou este ciclo permanece: 5 tentativas, zero consumos; 17 inversões líquidas globais sem inversão do par-alvo durante tentativa; custo de pace das janelas −0,089 s; R1/R2 já divergiam antes de 60 s, segundo a interpretação pendente do dossiê 1F. Nenhum detalhe adicional de tentativa ou amostra está autorizado antes do freeze.

## FASE 0 — censos mascarados congelados

Os censos só registram forma/schema e hashes. O censo de formas processa R1 e R2; o de resíduos repete a regra congelada na 1E; o de schema do audit repete a forma congelada na 1F. As saídas de censo abaixo são arquivos imutáveis do freeze. Na abertura, reexecutar cada bloco, comparar byte a byte com o artefato correspondente e conferir SHA-256. Divergência = PARE.

### 0.1 Formas de linha dos logs

Comando da raiz do repositório:

```sh
python3 - <<'PY' > backend/experiments/pass-1/autopsia/0_CENSO_FORMAS_PASS_DIAG_2.txt
import ast, hashlib, json, re
from pathlib import Path
root=Path('backend')
manifest=json.loads((root/'experiments/pass-1/autopsia/1_MANIFEST_PASS_DIAG_1F.json').read_text(encoding='utf-8'))
pins=manifest['source_pins']
summary_keys={'opportunities','engaged','aborted_gap','aborted_timeout','aborted_contact','aborted_rejoin','aborted_target','consumed','attempts','active_attempt'}
attempt_keys={'target_id','start_s','end_s','outcome'}
rows=['PASS-DIAG-2 — censo mascarado de formas de linha','Valores de log, pilotos, horários, outcomes e quantidades de tentativas omitidos.']
for label, rel in [('R1','experiments/pass-1/1_R1_OFF.log'),('R2','experiments/pass-1/2_R2_ON.log')]:
    path=root/rel
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pins.get(rel): raise SystemExit('LINE-FORM CENSUS PARE: source pin mismatch')
    shapes=[]
    for line in path.read_text(encoding='utf-8',errors='strict').splitlines():
        if line.startswith('[pass-decision] '):
            match=re.fullmatch(r'\[pass-decision\]\s+[^:]+:\s*(\{.*\})\s*',line)
            if not match: raise SystemExit('LINE-FORM CENSUS PARE: pass-decision line shape')
            try: summary=ast.literal_eval(match.group(1))
            except Exception: raise SystemExit('LINE-FORM CENSUS PARE: summary syntax')
            if not isinstance(summary,dict) or set(summary)!=summary_keys or not isinstance(summary['attempts'],list): raise SystemExit('LINE-FORM CENSUS PARE: summary schema')
            for attempt in summary['attempts']:
                if not isinstance(attempt,dict) or set(attempt)!=attempt_keys: raise SystemExit('LINE-FORM CENSUS PARE: attempt schema')
            shapes.append('pass-decision-summary|summary-keys='+','.join(sorted(summary_keys))+'|attempt-keys='+','.join(sorted(attempt_keys)))
        elif re.match(r'^\[[^\]]+\]',line): shapes.append('bracketed-line')
        elif line.strip(): shapes.append('plain-line')
        else: shapes.append('blank-line')
    rows.append(f'{label} line-form fingerprint SHA-256: {hashlib.sha256(chr(10).join(shapes).encode()).hexdigest()}')
    rows.append(f'{label} pinned source SHA-256 verified: PASS')
rows.append('Dictionary shape was checked without publishing values or record counts.')
print('\n'.join(rows)+'\n',end='')
PY
```

Artefato e SHA-256: `0_CENSO_FORMAS_PASS_DIAG_2.txt` — `aaafcb056735d0cfa5c90eb7aabb10b31163ca60c2c7de3315f4332c5d120261`.

### 0.2 Grade lógica de 0,1 s

Usar a fórmula e a saída mascarada já congeladas na PASS-DIAG-1E, sem exibir horários: para cada `start_s`/`end_s`, exigir `abs(t*10-round(t*10)) <= 1e-3`; bucket `round((t*10) % 2, 6)` em `{0,1,2}`; preservar apenas hash agregado e contagens dos buckets. Comando da raiz, repetido na abertura:

```sh
python3 - <<'PY' > /tmp/pass_diag_2_residue.txt
import ast, hashlib, json, math, re
from pathlib import Path
root=Path('backend')
manifest=json.loads((root/'experiments/pass-1/autopsia/1_MANIFEST_PASS_DIAG_1F.json').read_text(encoding='utf-8'))
source=Path('backend/experiments/pass-1/2_R2_ON.log')
expected=manifest['source_pins']['experiments/pass-1/2_R2_ON.log']
if hashlib.sha256(source.read_bytes()).hexdigest()!=expected: raise SystemExit('RESIDUE CENSUS PARE: source pin mismatch')
lines=[line for line in source.read_text(encoding='utf-8').splitlines() if line.startswith('[pass-decision] ')]
attempts=[]
for line in lines:
    match=re.fullmatch(r'\[pass-decision\]\s+[^:]+:\s*(\{.*\})\s*',line)
    if not match: raise SystemExit('RESIDUE CENSUS PARE: line shape')
    try: summary=ast.literal_eval(match.group(1))
    except Exception: raise SystemExit('RESIDUE CENSUS PARE: summary syntax')
    if not isinstance(summary,dict) or not isinstance(summary.get('attempts'),list): raise SystemExit('RESIDUE CENSUS PARE: attempts schema')
    attempts.extend(summary['attempts'])
if len(attempts)!=5: raise SystemExit('RESIDUE CENSUS PARE: attempt count')
raw_times=[]
buckets={0:0,1:0,2:0}
for attempt in attempts:
    if not isinstance(attempt,dict): raise SystemExit('RESIDUE CENSUS PARE: attempt item schema')
    for key in ('start_s','end_s'):
        raw=attempt.get(key)
        try: seconds=float(raw)
        except Exception: raise SystemExit('RESIDUE CENSUS PARE: time schema')
        if not math.isfinite(seconds): raise SystemExit('RESIDUE CENSUS PARE: non-finite time')
        logical=seconds*10.0
        if abs(logical-round(logical))>1e-3: raise SystemExit('RESIDUE CENSUS PARE: logical-grid residual')
        residue=round((seconds*10.0)%2,6)
        bucket=0 if abs(residue)<=1e-3 else 1 if abs(residue-1.0)<=1e-3 else 2 if abs(residue-2.0)<=1e-3 else None
        if bucket is None: raise SystemExit('RESIDUE CENSUS PARE: bucket outside frozen set')
        buckets[bucket]+=1
        raw_times.append(str(raw))
if sum(buckets.values())!=10: raise SystemExit('RESIDUE CENSUS PARE: boundary count')
raw_digest=hashlib.sha256('\n'.join(raw_times).encode()).hexdigest()
text=('PASS-DIAG-1E — censo mascarado de resíduos\n'
      'Fonte: log R2 pinado; campos start_s/end_s somente.\n'
      'Fórmula: residue = round((t_segundos * 10) % 2, 6).\n'
      'Sanidade da grade lógica: PASS (|t*10 - round(t*10)| <= 1e-3).\n'
      f'Hash agregado dos horários (ordem do log; valores omitidos): {raw_digest}\n'
      f'Buckets agregados (sem piloto, alvo, outcome ou associação): 0={buckets[0]}, 1={buckets[1]}, 2={buckets[2]}.\n'
      'Horários absolutos omitidos.\n')
print(text,end='')
PY
cmp -s /tmp/pass_diag_2_residue.txt backend/experiments/pass-1/autopsia/0_CENSO_RESIDUOS_PASS_DIAG_2.txt || { echo 'RESIDUE CENSUS PARE'; exit 1; }
echo 'RESIDUE CENSUS CHECK PASS'
```

Artefato e SHA-256: `0_CENSO_RESIDUOS_PASS_DIAG_2.txt` — `5ba2037387e10ff70287f561e1422bc580529208456fbfd108fb7a09ca796b77`.

### 0.3 Schema do audit

Comando da raiz, repetido na abertura. Só estrutura, chaves e tipos são escritos; nenhum valor é impresso.

```sh
python3 - <<'PY' > /tmp/pass_diag_2_audit_schema.txt
import hashlib, json
from pathlib import Path
root=Path('backend')
manifest=json.loads((root/'experiments/pass-1/autopsia/1_MANIFEST_PASS_DIAG_1F.json').read_text(encoding='utf-8'))
path=root/'experiments/pass-1/4_AUDIT_PASS_1.json'
expected=manifest['source_pins']['experiments/pass-1/4_AUDIT_PASS_1.json']
if hashlib.sha256(path.read_bytes()).hexdigest()!=expected: raise SystemExit('AUDIT SCHEMA CENSUS PARE: source pin mismatch')
data=json.loads(path.read_text(encoding='utf-8'))
if not isinstance(data,dict): raise SystemExit('AUDIT SCHEMA CENSUS PARE: top-level shape')
container=data.get('pass_decision_attempts')
if not isinstance(container,dict) or set(container)!={'R2'}: raise SystemExit('AUDIT SCHEMA CENSUS PARE: run shape')
records=container['R2']
if not isinstance(records,list) or len(records)!=5: raise SystemExit('AUDIT SCHEMA CENSUS PARE: R2 list shape')
required={'driver_id','target_id','start_s','end_s','outcome'}
if any(not isinstance(row,dict) or set(row)!=required for row in records): raise SystemExit('AUDIT SCHEMA CENSUS PARE: record-key shape')
def kind(value):
    if isinstance(value,str): return 'string'
    if isinstance(value,bool): return 'boolean'
    if isinstance(value,(int,float)): return 'number'
    if value is None: return 'null'
    return type(value).__name__
types={key:sorted({kind(row[key]) for row in records}) for key in sorted(required)}
if any(len(values)!=1 for values in types.values()): raise SystemExit('AUDIT SCHEMA CENSUS PARE: field-type shape')
rows=['PASS-DIAG-1F — censo de schema do audit (sem valores)',
      'Fonte: 4_AUDIT_PASS_1.json; SHA-256 Tier B pinado conferido.',
      'Chaves de topo: '+','.join(sorted(data))+'.',
      'pass_decision_attempts: object com run key R2.',
      f'R2: array; registros={len(records)}.',
      'Chaves exatas por registro: '+','.join(sorted(required))+'.',
      'Tipos por campo: '+','.join(f'{key}={types[key][0]}' for key in sorted(required))+'.',
      'Valores, identificadores, horários e outcomes omitidos.']
print('\n'.join(rows)+'\n',end='')
PY
cmp -s /tmp/pass_diag_2_audit_schema.txt backend/experiments/pass-1/autopsia/0_CENSO_SCHEMA_AUDIT_PASS_DIAG_2.txt || { echo 'AUDIT SCHEMA CENSUS PARE'; exit 1; }
echo 'AUDIT SCHEMA CENSUS CHECK PASS'
```

Artefato e SHA-256: `0_CENSO_SCHEMA_AUDIT_PASS_DIAG_2.txt` — `c9532d4d146104947f3e3cbdeb40aff8377c4ebcc89594d772928bfdc46aa731`.

## Definições congeladas

### Q1 — divergência pré-60 s

1. Ler R1/R2 após confirmar todos os hashes. Alinhar por `(drv,tick)` em amostras com `t_s < 60`; os conjuntos de chaves devem ser idênticos. Comparar, nesta ordem, `s`, `body_x`/`body_y` (fallback conjunto `x`/`y`), `cum_dist`, `speed`, `lat`. Colunas ausentes, valores não finitos, chaves duplicadas ou desalinhadas = PARE.
2. Valores numéricos divergem se `abs(R1−R2) > 1e-9`. A divergência global é a primeira ordenada por tick, ordem de campo acima e piloto; registrar também a primeira por piloto. O output guarda tick, tempo, piloto, campo, valores R1/R2 e diferença absoluta.
3. Se não houver diferença nos seis campos de trajetória, comparar os demais campos comuns, excluindo as chaves de alinhamento `tick`, `t_s`, `drv`: numéricos com tolerância `1e-9`, textos após trim literal. Classificação: `TRAJECTORY_DIVERGENCE`, `NONTRAJECTORY_ONLY` (diferença só fora do conjunto de trajetória, incluindo telemetria/controle) ou `IDENTICAL_PRE60`. Essa categoria descreve colunas; não atribui causa. O primeiro campo fora da trajetória é reportado separadamente.

### Q2 — cinemática de gap das tentativas

1. Usar as tentativas R2 extraídas pelo parser 1F; o join log↔audit deve continuar bijetivo 5↔5 por piloto/alvo/tick lógico/outcome conforme 1F. A fonte dos horários e outcomes segue sendo o log. Para cada piloto e alvo, aplicar o mesmo mapeamento 1F: `tick_lógico=round(t_s*10)`, tolerância `1e-3`, início no primeiro sample CSV com `tick >= start_tick`, fim no último com `tick <= end_tick`, ambas as pontas inclusivas. Janela sem dois índices distintos ou com menos de 3 amostras fica `NÃO_ESTIMÁVEL`.
2. Em cada amostra mapeada, `g = wrap(s_target−s_ego,L)` no intervalo `[-L/2,L/2)`, positivo quando o alvo está à frente. Desenrolar a sequência adicionando a cada passo a diferença assinada mais curta, para remover a descontinuidade de volta sem trocar o sentido do gap.
3. Ajustar OLS `g(t)=a+b*t` contra `t_s` real. Reportar `g_start`, `g_end`, `b` (m/s), taxa de fechamento `−b`, erro-padrão de `b` e extremos do intervalo amostrado. Projeção congelada: `g_end + b*10`. Banda aproximada de 95% baseada na incerteza da inclinação: projeção `± 1,96 × 10 × SE(b)`; registrar a aproximação, sem tratá-la como previsão causal.
4. A projeção indica consumo plausível se o limite superior for `<= −10 m`; indica não plausível em 10 s se o limite inferior for `> −10 m`; caso contrário, `INCERTO`. Gap abaixo de `−10 m` corresponde ao ego 10 m à frente do alvo. Se a janela tiver menos de 3 amostras, `Sxx=0` ou falhar o mapeamento, declarar não estimável. Agregar mediana/média da taxa de fechamento e contagens por classe de projeção, sem misturar janelas não estimáveis.

### Escala do atrator — R1

Em cada tick R1 e para cada ego, localizar o carro imediatamente à frente: menor gap positivo de `wrap(s_outro−s_ego,L)`; empate por identificador lexical. O tick é `FOLLOW_EQUILIBRADO` se esse gap for `<60 m` e `abs(speed_ego−speed_ahead) <0,2 m/s`. Duração por piloto = amostras qualificadas × `0,2 s` (5 Hz); reportar tempo total observado e fração da corrida. A regra é geométrica e não depende de uma interpretação de `p_state`.

## Instrumento e selftest

`backend/scripts/pass_1_diag.py` v1.5 é a v1.4 acrescida somente dos blocos Q1 e Q2, bump de versão/docstring e casos sintéticos do selftest. O selftest preserva os checks v1.4 de pinos, schema/join e grade; acrescenta divergência de trajetória, diferença apenas fora da trajetória, tolerância `1e-9`, mapeamento de janela de gap, regressão com gap fechando, gap estacionário, projeção de 10 s, janela curta/não estimável, desenrolamento e follow. Não abre CSV, log ou audit de corrida.

Log do selftest: `0_selftest_v15.log`, SHA-256 `1760ea59a068dafbf5cc22e95d15c4d11aefd1f61779cf1b462180c6cfbf855d`; resultado PASS.

## Freeze, abertura e outputs

Arquivos a congelar em um commit do dono: este prereg; `backend/scripts/pass_1_diag.py`; os três censos acima; `0_selftest_v15.log`; `1_MANIFEST_PASS_DIAG_2.json`. O manifest deve registrar hashes de disco do prereg, script, censos e selftest; os sete pinos herdados; base commit/script; e ausência dos quatro outputs novos. Luna compara `git show <commit>:<path>` byte a byte com disco para os sete arquivos.

Somente após o commit verificado: (1) reexecutar os três censos e comparar bytes e hashes; (2) revalidar os sete pinos Tier B e a geometria Tier A; (3) conferir novamente que os quatro outputs abaixo não existem; (4) abrir a análise. Execução frozen, da raiz:

```sh
python3 -c 'import runpy,sys; ns=runpy.run_path("backend/scripts/pass_1_diag.py",run_name="pass_diag_2_frozen"); ns["run_pass_diag_2"](sys.argv[1])' <COMMIT_DO_FREEZE>
```

Essa chamada executa apenas Q1/Q2 e deixa o `main`/runner 1F sem alteração. Outputs fresh, sem sobrescrita:

- `1_Q1_PRE60_DIVERGENCIA.csv`
- `2_Q2_GAPS_TENTATIVAS.csv`
- `3_Q2_FOLLOW_R1.csv`
- `4_RESUMO_PASS_DIAG_2.json`

O dossiê de veredito é escrito somente após a análise e volta ao dono. Nenhum `PROJECT_STATE`, `AUDITORIA_RL.md` ou worklog é atualizado nesta fase pré-freeze.

**PARE obrigatório:** qualquer hash divergente; censo diferente; schema/alinhamento inválido; join log↔audit não bijetivo; output pré-existente; qualquer número novo antes do commit verificado; diff v1.4→v1.5 fora dos blocos declarados; edição do script/prereg após os números; corrida/smoke; mudança de produção; FAIL novo.
