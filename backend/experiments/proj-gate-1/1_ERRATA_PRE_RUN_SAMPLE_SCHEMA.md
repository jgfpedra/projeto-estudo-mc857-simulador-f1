# Errata pré-R1 — amostragem e completude de PROJ-GATE-1

Antes da implementação e de qualquer corrida, a leitura do CSV R4 confirmou
que `--ticks 6000` produz amostras de diagnóstico em ticks pares: `0,2,...,5998`.
São 3000 amostras por carro, 10 carros e 30.000 linhas, cobrindo 600 s em
passos de 0,2 s. O preregistro e o audit v1.0 foram ajustados para comparar a
completude com essa saída observada de R4.

O orçamento de cada corrida continua em 6000 ticks lógicos. Nenhum resultado,
limiar numérico, pista, seed ou configuração foi alterado. Nenhuma corrida,
smoke, análise de classes ou suíte foi executada nesta errata.

Este complemento foi congelado antes do commit de implementação e de R1.
