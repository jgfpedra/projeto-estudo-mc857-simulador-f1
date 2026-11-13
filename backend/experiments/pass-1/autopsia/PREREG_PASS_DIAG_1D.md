# PREREG PASS-DIAG-1D — parser v1.2 para o formato real do log

**Estado:** pré-freeze; nenhum detalhe de tentativa, tempo, alvo ou métrica nova foi lido.  
**Escopo:** report-only; zero sims/smokes, nenhuma mudança de produção e sem promoção.  
**Retomada:** novo ciclo autorizado após o PARE de schema da PASS-DIAG-1C.  
**Base normativa:** PASS-DIAG-1B, SHA-256 `d668bfb781467afbcf0d696fee38f6cfedb3bb3e0cd9f8741f28d38cbfb62093`; todas as definições Q0, (a)–(f), perfil empírico R1, curvatura, reentrada, contatos, inversões, primeira volta, folga, saídas e gates permanecem idênticos, salvo as emendas explícitas abaixo.

## Exposição autorizada antes do freeze

Acumula-se integralmente a declaração da PASS-DIAG-1B e somente estes dados publicados: 17 inversões líquidas pós-largada; mediana R2 137,01 s contra limite 136,71 s; contatos de primeira volta R1 4.140 e R2 171; contatos pós-rejoin R1 17 e R2 29; suíte 20F/375P/3S; zero amostras DECISION_ACTIVE em carve-outs; cinco registros em `pass_decision_attempts`; zero consumidos.

O censo de formas autorizado pelo dono declara: uma linha `[pass-decision] <DRV>: {dict}` por piloto; chaves do resumo `opportunities`, `engaged`, `aborted_gap`, `aborted_timeout`, `aborted_contact`, `aborted_rejoin`, `aborted_target`, `consumed`, `attempts`, `active_attempt`; cada item de `attempts` tem `target_id`, `start_s`, `end_s`, `outcome`. O censo de forma não autoriza valores. Continuam SELADOS: valores de RUS/PER; tempos e alvos das tentativas; taxas de progresso; atribuições Q0; resultados de (e) e (f).

Valores adicionais já declarados pelo dono e, portanto, permitidos antes do freeze: distribuição das tentativas RUS 3 (GAS, GAS, HAM), LEC 1 (PIA), PER 1 (GAS), demais 0; outcomes presentes `abort_timeout` e `abort_contact`, nenhum `consumed`; amostras cruas vistas VER/NOR/HAM/GAS/ALO/PIA zeradas; LEC `opportunities=1`, `engaged=1`, `abort_timeout=1`, `consumed=0`. Nenhum outro valor é autorizado.

O artefato mascarado do censo é `experiments/pass-1/autopsia/0_CENSO_FORMAS_PASS_DIAG_1D.txt`, SHA-256 `83cdb13f01eb6bdc0ac4712abe5663aae8fade577855baad8b1f0dde204ae8b2`. Ele redige pilotos e contagens e substitui todos os valores do dicionário por nomes de campo. A abertura após freeze deve repetir exatamente o comando abaixo, comparar byte a byte com esse artefato e conferir o mesmo SHA antes de abrir qualquer valor; qualquer mudança de forma ou divergência é PARE.

Comando congelado (executar da raiz do repositório):

```sh
set -o pipefail
grep -E '^\[pass-decision\] ' backend/experiments/pass-1/2_R2_ON.log | python3 -c 'import ast,re,sys; required={"opportunities","engaged","aborted_gap","aborted_timeout","aborted_contact","aborted_rejoin","aborted_target","consumed","attempts","active_attempt"}; attempt_keys={"target_id","start_s","end_s","outcome"}; n=0
for raw in sys.stdin:
 m=re.fullmatch(r"\[pass-decision\]\s+[^:]+:\s*(\{.*\})\s*",raw.rstrip("\n"))
 if not m: raise SystemExit("CENSUS FAIL: line shape")
 try: obj=ast.literal_eval(m.group(1))
 except Exception: raise SystemExit("CENSUS FAIL: literal dict")
 if not isinstance(obj,dict) or set(obj)!=required or not isinstance(obj["attempts"],list): raise SystemExit("CENSUS FAIL: summary schema")
 for attempt in obj["attempts"]:
  if not isinstance(attempt,dict) or set(attempt)!=attempt_keys: raise SystemExit("CENSUS FAIL: attempt schema")
 n+=1
 print("[pass-decision] <DRV>: dict_keys=["+",".join(sorted(obj))+"], attempts_item_keys=["+",".join(sorted(attempt_keys))+"]")
if n==0: raise SystemExit("CENSUS FAIL: no records")' | sort | uniq -c | sed -E 's/^[[:space:]]*[0-9]+/<COUNT>/'
```

O comando não imprime nomes de pilotos, valores, tentativas, outcomes, horários ou contagens: valida o literal/schema, emite apenas campos, agrupa formas iguais e mascara o contador. A forma aceita é exatamente a declarada acima; qualquer formato adicional ou diferente é PARE.

## Pinos e dupla proveniência

Os sete pinos de dados permanecem exatamente os da tabela `Fontes e pinos pré-freeze` da PASS-DIAG-1B; R1/R2 CSVs, logs, audit e execução são Tier B com SHA-256 em disco; geometria é Tier A no commit `8136d54ec45f9f49b38a5893a812928474109535`. O script v1.2 deriva os pinos da tabela congelada da PASS-DIAG-1B e o selftest compara todas as entradas. Na abertura: re-hash dos sete pinos; divergência = PARE. Não imprimir conteúdo de log/audit na checagem de hash/schema.

## Emendas v1.2 congeladas

1. `scripts/pass_1_diag.py` versão 1.2 substitui somente o leitor per-tick por parser do formato censado: identifica piloto no prefixo, remove o prefixo, usa `ast.literal_eval`, valida os nomes de campos do resumo e dos itens e extrai os intervalos da lista `attempts`. Tempos em segundos devem cair na grade congelada de 0,2 s e são convertidos aos ticks do CSV. Outcomes aceitos: `abort_gap`, `abort_timeout`, `abort_contact`, `consumed`, `aborted_rejoin`, `aborted_target` (com aliases de pontuação/capitalização declarados no parser). Os dois últimos são classificados como `ABORT-CARVEOUT-REJOIN` e `ABORT-CARVEOUT-TARGET`, permanecem separados da taxonomia principal e alimentam o gate g5. O selftest continua derivando os pinos exclusivamente da tabela imutável da PASS-DIAG-1B.
2. Novo gate independente: a lista de tentativas do log deve corresponder exatamente à lista R2 de `pass_decision_attempts` do audit JSON, usando piloto, alvo, início/fim na grade de 5 Hz e outcome normalizado. Divergência, campo ausente/ambíguo, outcome desconhecido, intervalo duplicado ou forma fora do censo = PARE. O script imprime apenas PASS/FAIL e nomes de campos na validação, nunca valores crus.
3. Selftest sintético, sem abrir CSV/log/audit real: linha literal do formato censado, extração dos itens, outcomes regulares e de carve-out, comparação com uma lista audit sintética independente, e cross-check de todos os pinos da tabela da PASS-DIAG-1B.

## Q0 e análise

Q0 é a primeira tabela do relatório: classificar as cinco tentativas (incluindo `TROCA-SEM-CONSUMO`); atribuir as 17 inversões a janelas, pilotos e lags; emitir o veredito mecânico entre bookkeeping, perturbação de fila ou inconclusivo. Em seguida, executar sem alteração as definições de PASS-DIAG-1B para (a) outcomes, (b) custo de pace contra o perfil empírico R1 ratificado, (c) curvatura e faixas congeladas, (d) anatomia pós-rejoin/contatos proxy, (e) linha temporal da primeira volta e (f) duração, gap e progresso lateral/quase-consumo. Manter explícita a limitação de que `car_car` não identifica o outro piloto.

Saídas novas, sem sobrescrever arquivos: mesmas seis tabelas/artefatos definidos na PASS-DIAG-1B em `experiments/pass-1/autopsia/`. Q0 precede (a)–(f). O dossiê final recomenda um único fator para PASS-2 — correção do contador se houver evidência de bookkeeping, ou um knob de engajamento/aborto se houver perturbação real; gates recalibrados permanecem: g4 primeira volta ≤ R1 (a melhoria 4.140→171 é efeito publicado), pace ≤ R1+2%, pós-rejoin ≤ R1 se coberto pelo mesmo fator; mecanismo adicional de pós-rejoin fica arquivado como item próprio. Veredito ao dono: PASS-2 (R1 OFF reutilizado se o caminho OFF não mudar, um ON + R3 condicional) ou arquivar. Sem promoção.

## Freeze e PARE

Arquivos de freeze: este prereg, `scripts/pass_1_diag.py` v1.2, `0_CENSO_FORMAS_PASS_DIAG_1D.txt`, `0_selftest_v12.log` e `1_MANIFEST_PASS_DIAG_1D.json`. O manifest é gerado dos próprios arquivos e do prereg congelado; registrar SHA-256 de cada um. Dono commita e informa o commit. Só após conferir `git show <commit>:<path>` byte-idêntico ao disco, reexecutar e comparar o censo e confirmar os hashes de fonte, pode-se abrir valores e executar a autópsia. O prereg/script/manifest não podem ser editados depois dos números.

PARE obrigatório: qualquer hash divergente; blob diferente do disco; censo/hash divergente; qualquer valor não declarado lido pré-freeze; formato de linha não previsto pelo censo; comparação log/audit divergente; diff v1.1→v1.2 fora de parser/integração de carve-out, import `ast`, bump docstring/versão e selftest; selftest sem o cross-check de pinos; arquivo parcial/overwrite; qualquer corrida/smoke; mudança de produção ou edição pós-números.
