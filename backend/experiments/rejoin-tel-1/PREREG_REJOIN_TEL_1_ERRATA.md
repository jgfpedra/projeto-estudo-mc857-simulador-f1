# Errata pré-resultados — regra de encaminhamento REJOIN-TEL-1

**Data:** 2026-10-24 (America/Sao_Paulo)  
**Aplica-se a:** `PREREG_REJOIN_TEL_1.md` (commit `cc879b0`).  
**Momento:** antes do commit da implementação, da suíte e do replay; nenhum
resultado novo foi aberto.

O prereg congela o limiar angular de 20° e a análise de associação, mas não
define a regra mecânica que converte esses dois resultados em recomendação.
Para evitar escolha pós-resultado, usar uma assinatura combinada e
descritiva:

- **Recomendar RECUP-2 opt-in** somente se mais de 50% das reentradas
  observáveis e identificáveis tiverem `abs(heading_err_deg)>20°` **e** a
  correlação Pearson entre erro angular assinado e segunda saída em até 10 s
  for positiva. Exige pelo menos duas observações com variação suficiente para
  a correlação; caso contrário ela é não identificável.
- **Arquivar/adiar a hipótese angular** se a assinatura combinada não ocorrer
  ou não for identificável. Isso não declara ausência de defeito e não impede
  outras causas.

A regra não muda schema, métricas, orçamento, PARE ou permissões. Qualquer
encaminhamento permanece recomendação ao dono; nenhuma correção ou promoção
neste ciclo.
