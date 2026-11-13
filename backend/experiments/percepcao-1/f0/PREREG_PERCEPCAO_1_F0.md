# PREREG_PERCEPCAO_1_F0 — Fase 0 da percepção de tráfego

**Data:** 2026-11-06 · **Branch:** `feat/sanidade-produto` · **Estado:**
aguardando Freeze do Dono. Esta preregistração é documental: zero treino e
zero corrida são permitidos antes do Freeze.

## 1. Pins de layout e entrada

| caminho | layout | entrada do ator | linhas herdadas do v10 |
|---|---:|---:|---:|
| percepção | 31d | 45d | 17 |
| fallback | 34d | 48d | 20 |

O layout é uma sequência ordenada, com nomes, unidades, escala, origem e
semântica publicados no artefato de fingerprint. Shape incompatível é erro
explícito; não há truncamento, padding ou fallback silencioso.

`W=5` ticks é a janela canônica (0,5 s a 10 Hz). Se a continuidade da janela
não puder ser comprovada, o instrumento usa `W=10` ticks e rotula o caso como
fallback. Os resultados W=5 e W=10 são reportados separadamente.

## 2. Fingerprint e variedades

O fingerprint do layout é o SHA-256 do JSON canônico UTF-8, com chaves
ordenadas, sem espaços supérfluos, números estáveis e listas na ordem
semântica. Cada arquivo de avaliação registra o JSON, o SHA-256 e a versão do
instrumento.

Para a variedade base `V`, somente cinco realizações são válidas:
`K=5`, `k=0,1,2,3,4`. A derivação é:

```text
seed_k = int.from_bytes(
    sha256((V + ":k=" + str(k)).encode("utf-8")).digest()[:8],
    "big",
)
```

O valor inteiro, a string `V:k=<k>` e o hash do layout devem aparecer no log e
no relatório. Não se aceita seed manual que não reconcilie com a derivação.

## 3. Pistas e splits

| conjunto | pistas | pares |
|---|---|---:|
| decisão/treino | 14 pistas de decisão + Zandvoort | 70 (`14×5`) |
| TESTE reportado | Monaco, Suzuka, Spa | 15 (`3×5`) |
| reserva congelada | `LasVegas_v2` | 0 |

`LasVegas_v2` fica congelada como reserva e não pode ser lida para calibrar,
treinar ou ajustar gates nesta fase. Os conjuntos de teste não podem orientar
qualquer decisão de desenvolvimento.

## 4. Pré-condição do professor (Task 3)

Após o Freeze, executar exatamente duas corridas solo de 600 s em Interlagos:
uma com o professor e uma com o v10 cego, sob o mesmo protocolo de observação.
Classificar as saídas por curva e calcular:

```text
taxa_total_v10 = total de saídas por curva / oportunidades válidas do v10
sobreposição = saídas do professor que coincidem com uma saída do v10
              / total de saídas do v10
```

**PARE:** se a sobreposição das saídas por curva for `>= 50%` da taxa total do
v10 cego, a pré-condição do professor falha e nenhum treino ou gate de
percepção pode começar. O relatório deve mostrar numeradores, denominadores,
curva, pista, realização e janela; denominador zero é `N/A`, nunca zero.

## 5. Gate analítico e secundários da Fase 1

O primário é a taxa de saídas por curva, calculada por oportunidade válida e
agregada sem ocultar a dispersão entre as cinco realizações:

```text
taxa(curva, braço) = saídas_classificadas(curva) / oportunidades(curva)
```

Passa quando a taxa agregada do candidato não excede a baseline e a mediana
por realização não piora. Secundários obrigatórios: contatos totais, contatos
até 60 s, linhas/tempo fora, laps_total, hesitações ou paradas ≥3 s,
excursões, reentradas em até 5 s, deadlocks, integridade de shape, fingerprint,
seed e dupla leitura determinística.

## 6. Orçamento fechado da Fase 0

- **Zero treino.**
- **2 corridas solo diagnósticas de 600 s** em Interlagos (professor e v10
  cego), somente após o Freeze e sob a regra de PARE acima.
- **85 pares de avaliação da baseline v10**, distribuídos conforme o instrumento
  congelado entre os conjuntos de decisão/validação e TESTE reportado. Cada par
  é uma comparação determinística e deve preservar a separação dos splits.

Toda saída deve ser nova, possuir log e sidecar quando aplicável, registrar
exit code, fingerprint, seed e janela, e ser lida duas vezes com `cmp=0`.
Qualquer divergência interrompe a Fase 0.

## 7. Governança

Este documento deve permanecer staged e sem commit até o Freeze do Dono.
Nenhuma simulação, treino, alteração de código de produção, re-pin de pista,
consumo de `LasVegas_v2`, pool 76..79 ou shard `test/` é permitido antes do
Freeze. O executor reporta PARE em qualquer violação e não cria uma
substituição silenciosa.
