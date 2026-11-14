# PLANO_PERCEPCAO_1 — percepção de tráfego para o ator v14

**Versão:** 1.0 · **Estado:** preregistração de abertura; aguardando Freeze do Dono ·
**Data:** 2026-11-06 (America/Sao_Paulo) · **Branch:** `feat/sanidade-produto`.

Este plano abre o Programa PERCEPÇÃO-1. O objetivo é medir, em etapas separadas
e reproduzíveis, se a percepção explícita de tráfego melhora a decisão do ator
sem alterar a física, a geometria congelada, os mecanismos homologados do
REALISMO-1 ou os pools já selados. Nenhuma tarefa deste documento autoriza
simulação, treino ou alteração de código: cada tarefa só começa após o
prereg correspondente, o Freeze do Dono e o orçamento explícito.

## 1. Escopo e estado inicial

O ator de referência usa observação edge de 34 dimensões e o caminho de
fallback usa 31 dimensões. O ator de percepção usa 45 dimensões de entrada e o
fallback correspondente usa 48 dimensões. As linhas herdadas do v10 são 17
para o caminho de percepção e 20 para o fallback. As dimensões são pins de
layout, não uma autorização para alterar o modelo nesta abertura.

O protocolo preserva os defaults de produção do REALISMO-1:
`--rejoin-handoff align --rejoin-ramp --gov vplan` no perfil composite. O
programa PERCEPÇÃO-1 não promove, desliga ou retreina qualquer mecanismo de
controle fora de seu próprio prereg.

## 2. Quatro ajustes ratificados

1. **Layout e fallback separados.** O layout de percepção (31d) e o fallback
   (34d) são pinados independentemente; as entradas do ator (45d/48d) e as
   linhas herdadas do v10 (17/20) não podem ser inferidas por padding silencioso.
2. **Janela curta com fallback explícito.** `W=5` ticks (0,5 s a 10 Hz) é o
   padrão; se a janela não puder ser formada, o protocolo usa `W=10` ticks e
   registra a razão, sem misturar as duas populações na mesma análise.
3. **Identidade e variedade são criptográficas.** Cada layout é serializado em
   JSON canônico e identificado por SHA-256; cada variedade deriva suas
   sementes por SHA-256 com `K=5`, `k=0..4`. Nomes de arquivo ou ordem de
   diretório não são identidade.
4. **Pré-condição do professor antes do treino.** A Task 3 só pode avançar
   após duas corridas solo de 600 s em Interlagos. Sobreposição de saídas por
   curva igual ou superior a 50% da taxa total do v10 cego encerra a linha de
   professor com PARE; não há treino de recuperação dentro da mesma tarefa.

## 3. Tabela de observações e contratos de dimensão

| Caminho | Layout | Entrada do ator | Linhas herdadas do v10 | Uso |
|---|---:|---:|---:|---|
| Percepção | 31d | 45d | 17 | ator com tráfego explícito |
| Fallback | 34d | 48d | 20 | compatibilidade sem percepção |

O cabeçalho, a ordem, a escala e a semântica de cada componente devem ser
publicados no prereg da tarefa que os usa. Qualquer divergência de shape,
ordem ou escala é erro explícito e PARE; não é permitido truncar, preencher
com zeros ou aceitar uma entrada incompatível como sucesso.

## 4. Tarefas do programa

1. **Abrir o plano mestre:** registrar escopo, invariantes, pools, splits e
   governança deste documento.
2. **Preregistrar F0:** congelar layouts, janela, fingerprint, sementes, pistas,
   orçamento e critérios da baseline v10.
3. **Auditar o professor:** executar somente após Freeze as duas corridas solo
   de 600 s em Interlagos e aplicar a regra de PARE da pré-condição.
4. **Congelar o instrumento:** validar shape, escalas, JSON canônico, SHA-256 e
   derivação de sementes, sem treino.
5. **Extrair a baseline v10:** medir os 85 pares de avaliação definidos no F0,
   com dupla leitura determinística e sem ajuste de limiar.
6. **Fechar a Fase 0:** publicar tabela por pista, variedade, janela e
   integridade; qualquer discrepância interrompe o programa.
7. **Preregistrar a Fase 1:** fixar a fórmula analítica do gate, secundários,
   agregação e critérios de não-regressão.
8. **Medir a Fase 1 solo:** comparar professor e v10 sem tráfego e sem
   alteração de mecanismo; documentar o limite de atribuição.
9. **Preregistrar a Fase 2:** fixar a composição de tráfego, vizinhos visíveis,
   curriculum e separação treino/validação/teste.
10. **Construir o conjunto supervisionado:** gerar exemplos somente com o
    professor aprovado, preservando fingerprint e sementes.
11. **Treinar o candidato:** executar o treino autorizado com checkpoint,
    orçamento e seed derivados; nenhum retreino oportunista é permitido.
12. **Avaliar o candidato:** rodar os pares pré-registrados em treino e
    validação; o conjunto de teste permanece intocado.
13. **Preregistrar a Fase 3:** fixar o protocolo de corrida, N, pistas, duração,
    métricas, integridade e comparação contra a baseline.
14. **Avaliar a Fase 3:** usar apenas as pistas e variedades liberadas; medir
    contatos, ritmo, saídas, deadlocks e estabilidade de observação.
15. **Fechar a decisão:** aplicar gates, alertas de regressão e árvore de
    PARE/FAIL/PASS, sem promover configuração que não esteja homologada.
16. **Encerrar o programa:** publicar relatório final, hashes, artefatos,
    ledgers sincronizados e decisão do Dono; manter reservas e testes selados.

## 5. Divisão de pistas e orçamento

As pistas de decisão são 14 pistas de treino mais Zandvoort como validação,
totalizando 70 pares (`14 × K=5`). As pistas reportadas como TESTE são Monaco,
Suzuka e Spa, totalizando 15 pares (`3 × K=5`). `LasVegas_v2` permanece como
reserva congelada e não pode ser consumida sem novo prereg.

A Fase 0 não tem treino. Seu orçamento é de duas corridas solo diagnósticas de
600 s em Interlagos (professor e v10 cego) e 85 pares de avaliação da baseline
v10. As corridas diagnósticas são pré-condição e não podem ser reaproveitadas
como evidência de treino ou teste.

## 6. Janela, fingerprint e sementes

`W=5` ticks equivale a 0,5 s a 10 Hz. Se houver menos de cinco ticks válidos,
ou se a janela perder a continuidade exigida pelo instrumento, o caso é
recalculado com `W=10` ticks e marcado como fallback. A análise principal
reporta separadamente as duas classes.

O fingerprint é o SHA-256 do JSON canônico do layout: UTF-8, chaves ordenadas,
sem espaços supérfluos, números serializados de forma estável e listas na
ordem semântica declarada. A string canônica e o hash devem acompanhar cada
artefato.

Para uma variedade base `V`, a semente da realização `k` é:

```text
seed_k = int.from_bytes(
    sha256((V + ":k=" + str(k)).encode("utf-8")).digest()[:8],
    "big",
)
```

Somente `k=0,1,2,3,4` é válido. A semente efetiva, a string de derivação e o
hash do layout são disclosure obrigatório.

## 7. Fórmula analítica do gate e secundários da Fase 1

O gate primário usa a taxa de saídas por curva:

```text
taxa(curva, braço) = saídas classificadas na curva / oportunidades válidas
```

O resultado da Fase 1 é aprovado somente se a taxa agregada do candidato não
exceder a baseline nas curvas elegíveis e se a mediana das taxas por realização
não piorar. Cada curva informa numerador, denominador, janela usada e pista.
Nenhum denominador zero é convertido em zero: é `N/A` e provoca revisão.

Secundários obrigatórios: contatos totais e t≤60 s, linhas fora, tempo fora,
laps_total, hesitações/paradas ≥3 s, excursões, reentradas até 5 s, deadlocks,
shape/fingerprint e integridade de seed. Secundário que falhar não é escondido
por média agregada; deve ser exposto por pista e variedade.

## 8. Governança, integridade e PARE

- Prereg deve estar staged antes de qualquer execução.
- Todo comando deve começar em `backend/` e declarar o interpretador
  `.venv/bin/python`; não usar rede nem fallback silencioso.
- Zero simulação, zero treino e zero alteração de produção nesta abertura.
- Pools 76..79 e shards `test/` permanecem intocados; nenhum artefato pode ser
  sobrescrito. Saídas devem ser novas e inexistentes antes da execução.
- Cada corrida ou avaliação tem exit code, linhas, sidecar, log, fingerprint,
  seed e dupla leitura determinística (`cmp=0`) quando aplicável.
- PARE imediato para shape incompatível, fingerprint divergente, seed não
  derivada, saída pré-existente, fallback não declarado, professor acima do
  limiar de 50% ou qualquer alteração fora do prereg.
- O Dono decide Freeze, re-pin, promoção e encerramento. O executor não faz
  commit, não altera defaults e não libera reservas por inferência.

## 9. Artefatos e encerramento

Artefatos ficam sob `backend/experiments/percepcao-1/<fase>/`. Cada fechamento
contém a matriz por realização, hashes SHA-256, comandos completos, status de
integridade, resultados primários/secundários e o veredito mecânico. Os três
ledgers recebem uma linha idêntica somente após a execução autorizada.

Este plano é documento de abertura. A próxima ação autorizada é a revisão do
Dono e o Freeze correspondente; até lá, todas as tarefas 3–16 estão bloqueadas.
