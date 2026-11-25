# Linha local de Interlagos

`interlagos_rule_line.json` contém deslocamentos da linha suavizada do
controller em dois trechos da geometria congelada. O arquivo só é aplicado
quando o SHA-256 dos waypoints e a largura de 12 m coincidem. Os waypoints da
pista, a projeção e a detecção de saída continuam usando a geometria original.

Os deslocamentos foram calculados offline nas janelas de 1800–2050 m e
2200–2420 m. Em cada uma, minimizou-se a soma dos quadrados da curvatura,
acrescida de `0,0001 * soma(diff(offset, 2)^2)` e `0,0000001 * soma(offset^2)`.
O deslocamento normal foi limitado a 3,5 m em relação à linha já suavizada,
com dois pontos fixos em cada extremidade. O L-BFGS-B atingiu o limite de
avaliações, portanto o arquivo é um candidato calibrado, sem garantia de
ótimo. O controller aplica metade dos deslocamentos para preservar mais
espaço de manobra e mantém o planejamento de velocidade pela geometria
anterior, pois a nova linha isoladamente não garante frenagem suficiente.

As medições da alteração são para a pista congelada e dependem da física e do
controller atuais. A velocidade da F1 real ainda não é reproduzida nesses
trechos. Em um ensaio de 180 s com dez carros, pista seca e seed 42, as saídas
diminuíram nas duas janelas, mas aumentaram no restante da volta (21 para 24
eventos no total). A interação com tráfego ainda precisa de calibração.

## Ritmo de volta

Na geometria e largura verificadas, o controller usa fator lateral 0,65 e
permite pedir até 10 m/s² de aceleração. Em outras pistas permanecem os valores
conservadores 0,58 e 6 m/s²: aumentar o fator para Mônaco elevou o tempo e as
saídas, enquanto aumentar apenas a aceleração também elevou excursões. O motor
limita a força aplicada pela potência e pela aderência traseira.

Uma volta seca solo de VER com seed 42 caiu de 126,1 s para 112,7 s; o desvio
lateral máximo do centro do carro foi 4,32 m, dentro dos 6 m de meia largura.
Com fator lateral 0,58 e aceleração 10 m/s², seis combinações solo de piloto e
seed ficaram entre 116,2 e 118,1 s, sem o centro passar de 5 m. No grid seco de
dez carros, seed 42, o líder caiu de 126,3 s para 112,7 s; o total de amostras
com o centro a mais de 6 m caiu de 1373 para 1140 até o líder completar a volta,
mas as excursões se redistribuíram entre pilotos. É uma medição inicial, não
uma validação estatística de corrida.

A referência abaixo de 80 s ainda não foi atingida. Elevar o teto do hairpin de
7,2 para 9 m/s com o fator 0,65 levou a saídas e tornou a volta mais lenta
(113,5 s); no perfil atual a mínima em s≈2300 continua perto de 14 km/h. O
trajeto e o modelo de scrub dos pneus ainda limitam a velocidade nessa curva.

## Retorno à pista após saída

A superfície continua reduzindo o grip de 1,0 para 0,35 nos 3 m após a borda.
Essa perda é severa, mas agora o controller aplica um piso de superfície 0,50
somente enquanto o piloto está fora do asfalto e em modo de retorno; o grip do
pneu e do clima continuam ativos. O modo mantém o alvo na linha central,
ignora desvios de tráfego e só termina quando o carro está a até 4,5 m do centro
e com erro de orientação menor que 35°. O esterço máximo no retorno é 0,45 rad.

A velocidade de retorno varia com a posição: 6 m/s quando o carro está mais de
4 m além da borda, 5 m/s na grama próxima e 4 m/s já no asfalto enquanto ainda
está desalinhado. Isso evita que um carro atravessado continue acelerando pela
pista e saia pelo lado oposto.

Em uma reprodução seca headless com o carro do Alonso, seed 42 e início de
costas para a pista, a 8 m do centro, ele tocou o asfalto em 3,3 s e estabilizou
em 22,0 s sem se afastar além dos 8 m iniciais. Começando 20 m fora, tocou o
asfalto em 7,7 s e estabilizou em 13,9 s sem ultrapassar essa distância. São
cenários sintéticos em uma reta, não uma reprodução da saída observada na volta.

Com o retorno atualizado, a volta limpa seca de VER/seed 42 permanece em
112,7 s, com afastamento máximo de 4,32 m. No grid seco de dez carros até o
líder completar a volta, o total de amostras além de 6 m foi 141; Alonso chegou
a 6,60 m nesse ensaio. Um ajuste de fator lateral 0,70 e aceleração 10 m/s²
baixou o tempo para 110,5 s, mas elevou essas amostras a 426 e levou outros
pilotos a mais de 12 m do centro. O perfil adotado permanece em 0,65 e 10 m/s²
para preservar margem contra saídas. Todas essas comparações usam uma seed.

## Disputa e classificação

No runner de dez carros, o perfil `apex-rules` sorteia uma seed e a ordem do
grid por padrão. A seed aparece na inicialização: `--seed 42` repete a corrida
e `--variance off` conserva a ordem fixa do grid. Os demais perfis mantêm suas
opções padrão de variância e seed.

Cada piloto tem reação de largada e ritmo variáveis, derivados da seed. O ritmo
muda gradualmente e erros ocasionais são pequenas reduções de acelerador. Em
retas, o piloto tenta antecipar a passagem quando está se aproximando, verifica
as faixas disponíveis e mantém a manobra até o adversário ficar para trás.

O runner conta voltas e ordena a classificação pelo progresso projetado na
pista, incluindo a posição inicial do grid. A distância percorrida continua
disponível para telemetria; o modo legado de contagem de voltas é preservado
nos demais ambientes por padrão.

O vácuo simplificado alcança 8–60 m, com pico em 12 m e redução máxima de 8%
do arrasto para carros rápidos e alinhados em uma reta. Numa comparação seca
de três voltas, seed 1 e grid variado, Verstappen venceu largando em segundo.
O vácuo ampliado deixou 22 pares de carros trocando de ordem em pista, contra
18 com o alcance anterior; a diferença para o segundo foi 228 m contra 299 m.
As amostras agregadas fora dos 6 m de meia largura caíram de 495 para 142.
São resultados de uma corrida por configuração; outras seeds deram resultados
mistos e a vantagem do líder ainda pode ficar grande.
