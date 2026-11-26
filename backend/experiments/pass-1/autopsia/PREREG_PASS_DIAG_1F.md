# PREREG PASS-DIAG-1F — v1.4: join audit↔log conforme schema real

**Estado:** pré-freeze, aguardando commit do dono. Nenhuma métrica nova de tentativa foi aberta.  
**Escopo:** report-only; zero simulações/smokes, nenhuma mudança de produção e sem promoção.  
**Retomada:** PARE de schema da PASS-DIAG-1E; handoff `01a17084-26f3-70f1-abd4-b68dc9912452`.  
**Base congelada:** PASS-DIAG-1E commit `9a7852cb8111d354a1206b7c5992540824896467`; script v1.3 SHA-256 `90f44bac473878449eb16cf33cbc86998f9a5135e4181daabecf86d4ccd1c623`. O audit R1 permanece Tier B com SHA-256 `347216e6cf65f109ec82d927762bab5ffefea85c4913fca024891bf05e1a134b`; não é repinado nem regenerado.

## Declaração de exposição acumulada

Mantêm-se as exposições declaradas na PASS-DIAG-1B/1D/1E: 17 inversões líquidas pós-largada; mediana R2 137,01 s contra limite 136,71 s; contatos de primeira volta R1 4.140 e R2 171; pós-rejoin R1 17 e R2 29; cinco tentativas e zero consumidas; suíte 20F/375P/3S; zero amostras DECISION_ACTIVE em carve-outs. A PASS-DIAG-1E parou no schema antes de gerar qualquer saída de análise.

Exposição adicional ratificada pelo dono: `pass_decision_attempts` no audit é um dict `{"R2": [5 registros]}`. Os campos são `driver_id`, `target_id`, `start_s`, `end_s`, `outcome`; não existe `driver`. Os dois registros expostos são LEC/PIA 332,6→340,6 `abort_timeout` e RUS/GAS 78,4→86,5 `abort_timeout`. Permanecem SELADOS o terceiro registro de RUS, os registros completos de PER, demais valores, taxas, atribuições Q0, (e) e (f).

## Emenda congelada: gate de consistência v2

1. O driver de cada tentativa vem exclusivamente do prefixo da linha `[pass-decision] <DRV>:` no log. O audit não fornece a autoridade do driver.
2. `pass_decision_attempts` precisa ter shape dict com a única run key `R2`, cujo valor é uma lista de cinco registros com as chaves exatas `driver_id`, `target_id`, `start_s`, `end_s`, `outcome`.
3. Para cada tentativa do log deve existir exatamente um registro do audit R2 em que `driver_id == drv`, `target_id == target`, `abs(start_s_audit - start_s_log) <= 1e-6`, `abs(end_s_audit - end_s_log) <= 1e-6` e `outcome_audit == outcome_log` (igualdade literal). O pareamento tem de ser bijetivo 5↔5, sem duplicidades nem sobras.
4. O log permanece fonte dos horários e dos campos da tentativa; valores do audit são somente contra-cheque e não substituem o log. Os horários usados nas métricas continuam seguindo o mapeamento lógico v1.3: `round(t_s * 10)`, tolerância de grade `1e-3`, primeiro sample CSV `tick >= início`, último `tick <= fim`; janela que mapeia à mesma linha é `NÃO ESTIMÁVEL`.
5. Qualquer shape diferente, não-bijeção ou discordância de driver/alvo/tempo/outcome é PARE/finding mecânico.

Todas as demais definições de Q0, (a)–(f), pace empírico R1, curvatura, reentrada, contatos, inversões, primeira volta, fallback `NÃO ESTIMÁVEL` e gates permanecem exatamente como frozen na PASS-DIAG-1B/1D/1E. Q0 continua primeiro: classificar as cinco tentativas (cinco registros; zero consumidos), conferir o join log↔audit e atribuir as 17 inversões por janela, piloto e lag; só depois abrir e reportar (a)–(f).

## FASE 0 — censo de schema, sem valores

O censo mostra apenas chaves, estrutura, quantidade de registros e tipos JSON. Não imprime nem grava identificadores, timestamps, outcomes ou outros valores. Fonte audit hash-pinned, sem alterar ou regenerar o audit.

Artefato: `experiments/pass-1/autopsia/0_CENSO_SCHEMA_AUDIT_PASS_DIAG_1F.txt`; SHA-256 `c9532d4d146104947f3e3cbdeb40aff8377c4ebcc89594d772928bfdc46aa731`.

### Comando congelado para repetir o censo mascarado

Executar da raiz do repositório após verificar o commit e os pinos. O comando só grava a estrutura mascarada em `/tmp` e imprime PASS/FAIL.

```sh
python3 - <<'PY' > /tmp/pass_diag_1f_schema.txt
import hashlib, json
from pathlib import Path
path=Path('backend/experiments/pass-1/4_AUDIT_PASS_1.json')
expected='347216e6cf65f109ec82d927762bab5ffefea85c4913fca024891bf05e1a134b'
if hashlib.sha256(path.read_bytes()).hexdigest()!=expected: raise SystemExit('SCHEMA CENSUS PARE: audit hash mismatch')
data=json.loads(path.read_text(encoding='utf-8'))
if not isinstance(data,dict): raise SystemExit('SCHEMA CENSUS PARE: top-level shape')
container=data.get('pass_decision_attempts')
if not isinstance(container,dict) or set(container)!={'R2'}: raise SystemExit('SCHEMA CENSUS PARE: run mapping shape')
records=container['R2']
if not isinstance(records,list) or len(records)!=5: raise SystemExit('SCHEMA CENSUS PARE: R2 list shape')
required={'driver_id','target_id','start_s','end_s','outcome'}
if any(not isinstance(row,dict) or set(row)!=required for row in records): raise SystemExit('SCHEMA CENSUS PARE: record-key shape')
def kind(value):
    if isinstance(value,str): return 'string'
    if isinstance(value,bool): return 'boolean'
    if isinstance(value,(int,float)): return 'number'
    if value is None: return 'null'
    return type(value).__name__
types={key:sorted({kind(row[key]) for row in records}) for key in sorted(required)}
if any(len(v)!=1 for v in types.values()): raise SystemExit('SCHEMA CENSUS PARE: field-type shape')
rows=[
 'PASS-DIAG-1F — censo de schema do audit (sem valores)',
 'Fonte: 4_AUDIT_PASS_1.json; SHA-256 Tier B pinado conferido.',
 'Chaves de topo: '+','.join(sorted(data))+'.',
 'pass_decision_attempts: object com run key R2.',
 f'R2: array; registros={len(records)}.',
 'Chaves exatas por registro: '+','.join(sorted(required))+'.',
 'Tipos por campo: '+','.join(f'{k}={types[k][0]}' for k in sorted(required))+'.',
 'Valores, identificadores, horários e outcomes omitidos.',
]
print('\n'.join(rows)+'\n',end='')
PY
cmp -s /tmp/pass_diag_1f_schema.txt backend/experiments/pass-1/autopsia/0_CENSO_SCHEMA_AUDIT_PASS_DIAG_1F.txt || { echo 'SCHEMA CENSUS PARE'; exit 1; }
echo 'SCHEMA CENSUS CHECK PASS'
```

Na abertura, re-hash dos sete arquivos de entrada contra a manifest/prereg PASS-DIAG-1B e do audit contra seu pino Tier B. Qualquer divergência é PARE.

## FASE 1 — freeze do instrumento

`scripts/pass_1_diag.py` v1.4 = v1.3 com diff restrito a: (a) carregamento/validação do dict por run e join do audit por `driver_id` segundo o gate v2; (b) bump de versão/docstring; (c) selftest sintético com shape real `{"R2": [...]}` e `driver_id`, mantendo casos de grade lógica, janela não estimável, horário fora de grade e cross-check de pinos. Selftest não abre CSV, log ou audit real.

Script v1.4 SHA-256 `85812034fabbb1c6a7c2d2b6f9758bbb77e3d370a5eefcd5f7f64ce5c870af9f`. Log do selftest `experiments/pass-1/autopsia/0_selftest_v14.log`, SHA-256 `cddb0d9573f956e7b2639d8ec2fda982dc0f98b57e913a4edf46a40209a9eee4`; resultado PASS.

Freeze files: este prereg, `scripts/pass_1_diag.py`, `0_CENSO_SCHEMA_AUDIT_PASS_DIAG_1F.txt`, `0_selftest_v14.log` e `1_MANIFEST_PASS_DIAG_1F.json`. O manifest registra hashes dos outros quatro, os sete pinos herdados e a ausência das seis saídas antes da abertura. Dono commita exatamente os cinco arquivos; Luna confere `git show <commit>:<path>` byte a byte contra o disco. Só então reexecutar o censo mascarado e validar os pinos; após PASS, executar Q0 primeiro e depois (a)–(f).

## Saídas herdadas e PARE

As seis saídas são as da PASS-DIAG-1E: `1_Q0_TENTATIVAS.csv`, `2_Q0_INVERSOES.csv`, `3_PACE_CURVATURA.csv`, `4_REENTRADA_CONTATOS.csv`, `5_PRIMEIRA_VOLTA.csv`, `6_RESUMO.json`; devem estar ausentes no freeze e nunca podem ser sobrescritas. O dossiê textual do refinamento volta ao dono com um único fator para PASS-2, pace ≤ R1+2%, g4 recalibrado para primeira volta ≤ R1 e pós-rejoin ≤ R1 se o fator cobrir.

**PARE obrigatório:** join não-bijetivo ou divergente; schema/censo diferente; blob diferente do disco; pino divergente; qualquer número novo antes do freeze verificado; edição pós-números; saída pré-existente/parcial; corrida/smoke; mudança de produção; FAIL novo na suíte referenciada. Sem promoção.
