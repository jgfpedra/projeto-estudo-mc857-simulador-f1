# PREREG YIELD-1B — consolidação do freeze

## Estado e exposição

YIELD-1 foi interrompido antes da corrida por edição pós-números: a suíte
pré-ajuste registrou 20 falhas conhecidas, 380 passes e 3 skips
(`0_full_suite.log`, SHA-256
`dd1a2edf407a493222bb94d480a17928cf46d33928a70fb5215b4f8fa86ee8f4`).
Não existe saída de R2-Y. O freeze desta revisão reúne os fixes PASS-PARITY v2/v3,
a implementação YIELD-1, o wiring standalone de `--leader-yield` e a emenda do
gatilho abaixo. Os registros de fechamento pendentes permanecem fora do commit.

## Gatilho congelado

O líder pode ceder somente a partir de `t >= 60 s`, quando há um seguidor atrás
com `signed_dist_s` em `[-20, -5] m`, `|Δlat| < 2,6 m`, o líder é o carro mais
próximo à frente do seguidor na mesma linha e o seguidor permanece em FOLLOW/cap.
Velocidade estritamente maior do seguidor não é requisito: igualdade é esperada
sob o `v_plan` compartilhado. A condição precisa aparecer em 15 amostras 5 Hz
consecutivas para o mesmo par.

O lado de fuga reutiliza `_pass_decision_choose_side`; o alvo lateral sai pelo
menos 3,5 m do seguidor, com limites da pista. O yield é consumido quando o
seguidor fica 10 m à frente, aborta por contato, carve-out ou timeout de 8 s,
e mantém um único estado ativo por líder.

## Gates e orçamento

Executar uma única suíte serial após o commit do dono e uma única R2-Y com a
configuração canônica mais `--leader-yield`. O gate exige zero FAILED novo,
pré-gate sintético aprovado, consumo por par, não-piora contra R1, transferência
sem carve-out e paridade byte a byte com R1 até o primeiro gatilho `t* >= 60 s`.
Qualquer falha de gate arquiva o mecanismo com o payload e encerra a sublinha de
passagem.
