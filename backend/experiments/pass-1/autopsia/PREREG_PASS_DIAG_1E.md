# PREREG PASS-DIAG-1E — v1.3 com tick lógico de 0,1 s

**Estado:** pré-freeze, aguardando commit do dono. Nenhuma métrica da autópsia foi aberta.  
**Escopo:** report-only; zero simulações/smokes, nenhuma mudança de produção e sem promoção.  
**Retomada:** PARE de grade na PASS-DIAG-1D; handoff `01a17064-5e1d-7aa3-9224-1d7438406250`.  
**Base:** PASS-DIAG-1D, commit `6989bf831e8ba41c10acdbc2f444ebfba92f5958`, prereg SHA-256 `170a35d4f9b750a91f164fd5a759052249a77e5bd98ea83e7095c25a4188a936`; PASS-DIAG-1B, SHA-256 `d668bfb781467afbcf0d696fee38f6cfedb3bb3e0cd9f8741f28d38cbfb62093`. Todas as definições de Q0, (a)–(f), pace empírico R1, reentrada, contatos, inversões e gates permanecem exatamente as congeladas nesses preregs, salvo o mapeamento de amostra abaixo.

## Exposição autorizada

Acumula-se a exposição da PASS-DIAG-1B/1D: 17 inversões líquidas pós-largada; mediana R2 137,01 s contra limite 136,71 s; contatos de primeira volta R1 4.140 e R2 171; pós-rejoin R1 17 e R2 29; suíte 20F/375P/3S; zero amostras DECISION_ACTIVE em carve-outs; cinco tentativas e zero consumidas segundo os metadados publicados.

O censo de resíduos congelado como FASE 0 usa somente os campos `start_s` e `end_s` do log R2. O dono declarou que as cinco tentativas pertencem à grade lógica de 0,1 s e que os resíduos observados são aproximadamente `{0,1,2}`, com o bucket 2 associado a ruído de tick ímpar. Não são exibidos horários absolutos, pilotos, alvos, outcomes, nem associações entre tentativas. A extensão ratificada calcula, para cada limite temporal, `residue = round((t_segundos * 10) % 2, 6)` e agrega os buckets 0/1/2; o artefato também guarda somente um SHA agregado dos textos de horário, nunca os textos.

Artefato FASE 0: `experiments/pass-1/autopsia/0_CENSO_RESIDUOS_PASS_DIAG_1E.txt`, SHA-256 `5ba2037387e10ff70287f561e1422bc580529208456fbfd108fb7a09ca796b77`.

### Comando congelado para reexecutar o censo mascarado

Executar da raiz do repositório após verificar os blobs do freeze. O comando só escreve no arquivo temporário um hash agregado dos horários e contagens dos buckets; imprime apenas PASS/FAIL. Ele não mostra horários, pilotos, alvos ou outcomes.

```sh
python3 - <<'PY' > /tmp/pass_diag_1e_census.txt
import ast, hashlib, math, re
from pathlib import Path
source=Path('backend/experiments/pass-1/2_R2_ON.log')
lines=[line for line in source.read_text(encoding='utf-8').splitlines() if line.startswith('[pass-decision] ')]
attempts=[]
for line in lines:
    match=re.fullmatch(r'\[pass-decision\]\s+[^:]+:\s*(\{.*\})\s*',line)
    if not match: raise SystemExit('CENSUS PARE: line shape')
    try: summary=ast.literal_eval(match.group(1))
    except Exception: raise SystemExit('CENSUS PARE: summary literal')
    if not isinstance(summary,dict) or not isinstance(summary.get('attempts'),list): raise SystemExit('CENSUS PARE: attempts schema')
    attempts.extend(summary['attempts'])
if len(attempts)!=5: raise SystemExit('CENSUS PARE: attempt count')
raw_times=[]
buckets={0:0,1:0,2:0}
for attempt in attempts:
    if not isinstance(attempt,dict): raise SystemExit('CENSUS PARE: attempt item schema')
    for key in ('start_s','end_s'):
        raw=attempt.get(key)
        try: seconds=float(raw)
        except Exception: raise SystemExit('CENSUS PARE: time schema')
        if not math.isfinite(seconds): raise SystemExit('CENSUS PARE: non-finite time')
        logical=seconds*10.0
        if abs(logical-round(logical))>1e-3: raise SystemExit('CENSUS PARE: logical-grid residual exceeds tolerance')
        residue=round((seconds*10.0)%2,6)
        bucket=0 if abs(residue-0.0)<=1e-3 else 1 if abs(residue-1.0)<=1e-3 else 2 if abs(residue-2.0)<=1e-3 else None
        if bucket is None: raise SystemExit('CENSUS PARE: residue bucket outside declared set')
        buckets[bucket]+=1
        raw_times.append(str(raw))
if sum(buckets.values())!=10: raise SystemExit('CENSUS PARE: boundary count')
raw_digest=hashlib.sha256('\n'.join(raw_times).encode()).hexdigest()
text=(
    'PASS-DIAG-1E — censo mascarado de resíduos\n'
    'Fonte: log R2 pinado; campos start_s/end_s somente.\n'
    'Fórmula: residue = round((t_segundos * 10) % 2, 6).\n'
    'Sanidade da grade lógica: PASS (|t*10 - round(t*10)| <= 1e-3).\n'
    f'Hash agregado dos horários (ordem do log; valores omitidos): {raw_digest}\n'
    f'Buckets agregados (sem piloto, alvo, outcome ou associação): 0={buckets[0]}, 1={buckets[1]}, 2={buckets[2]}.\n'
    'Horários absolutos omitidos.\n'
)
print(text,end='')
PY
cmp -s /tmp/pass_diag_1e_census.txt backend/experiments/pass-1/autopsia/0_CENSO_RESIDUOS_PASS_DIAG_1E.txt || { echo 'CENSUS PARE'; exit 1; }
echo 'CENSUS CHECK PASS'
```

A divergência no arquivo mascarado, hash, schema, quantidade congelada ou resíduos fora da sanidade/taxonomia é PARE. Os pinos de R1/R2 continuam sendo os da PASS-DIAG-1B; na abertura, re-hash dos sete arquivos antes de qualquer leitura analítica.

## Mapeamento de tentativa para amostras CSV — única mudança semântica

1. Para segundos, `tick_lógico(t) = round(t * 10)`. Exigir `abs(t * 10 - tick_lógico) <= 1e-3`; acima disso, PARE. Um campo de tick explícito no audit é validado como tick lógico inteiro, com a mesma tolerância numérica.
2. Para cada intervalo, usar a série de amostras 5 Hz do par ego/alvo: início é o primeiro sample com `tick_csv >= tick_lógico(start)`; fim é o último sample com `tick_csv <= tick_lógico(end)`. A lista de progresso é inclusiva entre essas linhas. A consistência log/audit compara os ticks lógicos originais, não os ticks amostrados.
3. Se o índice da linha inicial for maior ou igual ao índice da linha final, a tentativa fica `NÃO ESTIMÁVEL`: publicar a contagem; métricas que exigem progresso/curvatura/pace ficam nulas; não inferir troca ou consumo pelo intervalo sem amostras suficientes. Manter separados o outcome registrado no log e a classificação de trajetória.
4. Para intervalos estimáveis, manter Q0 e (a)–(f) exatamente como congelados. Atributos temporais de atividade usam o intervalo lógico; métricas de progresso usam as linhas CSV mapeadas. O custo agregado de pace é a soma somente das tentativas estimáveis, com a contagem estimável/não estimável explícita; se nenhuma for estimável, o agregado fica nulo.

## Instrumento e selftest

`scripts/pass_1_diag.py` v1.3 é a versão 1.2 com diff restrito ao bump/docstring, ao mapeamento lógico→amostras e propagação de `NÃO ESTIMÁVEL`, e ao selftest. O selftest não abre CSV/log/audit real. Casos obrigatórios: `start_s=332,7` produz tick lógico ímpar 3327 e mapeia, em ticks sintéticos `[3326,3328,3330,3332]`, para início 3328/fim 3330; janela que mapeia para a mesma linha fica não estimável; `332,755` PARE por ruído acima de 1e-3; parser e cross-check log/audit sintéticos; cross-check dos pinos com a tabela congelada da 1B.

Log do selftest: `experiments/pass-1/autopsia/0_selftest_v13.log`; SHA-256 `438b592a035d794192bb4caa31d535afb99d447bba2e7f31f8a322eadb07ea82`. O selftest passou sem abrir dados reais de corrida.

## Freeze e execução

Arquivos do freeze: este prereg, `scripts/pass_1_diag.py` v1.3, `0_CENSO_RESIDUOS_PASS_DIAG_1E.txt`, `0_selftest_v13.log` e `1_MANIFEST_PASS_DIAG_1E.json`. O manifest fixa os hashes de cada arquivo e os sete pinos de fonte herdados da 1B. Dono commita os cinco blobs; Luna verifica `git show <commit>:<path>` byte-idêntico ao disco; em seguida reexecuta o censo mascarado e compara arquivo/hash, revalida os sete pinos e só então executa a análise offline, Q0 primeiro.

As seis saídas de análise continuam as da 1D: `1_Q0_TENTATIVAS.csv`, `2_Q0_INVERSOES.csv`, `3_PACE_CURVATURA.csv`, `4_REENTRADA_CONTATOS.csv`, `5_PRIMEIRA_VOLTA.csv`, `6_RESUMO.json`. Todos devem estar ausentes antes do run; nenhuma saída pode ser sobrescrita.

**PARE obrigatório:** qualquer blob diferente do disco; censo mascarado/hash diferente; ruído lógico maior que 1e-3; resíduos fora de 0/1/2; divergência em qualquer pino; schema ou consistência log/audit divergente; diff v1.2→v1.3 fora dos blocos autorizados; selftest falho; saída pré-existente/parcial; edição pós-números; corrida/smoke; mudança de produção; FAIL novo na suíte referenciada.
