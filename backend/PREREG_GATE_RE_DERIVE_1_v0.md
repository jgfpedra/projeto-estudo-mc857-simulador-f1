PREREG GATE-RE-DERIVE-1 — rascunho v0 (redator externo: Luna; salvo verbatim pelo orquestrador para uso como base da revisão)
Status: rascunho para revisão; não canônico e não autorizado para execução.
Objetivo: definir antecipadamente um micro-ciclo exploratório para derivar e avaliar regras de plausibilidade do comprimento de geometrias geradas pelo pipeline OpenF1 v4.
Condição para congelamento: todos os FALTA_DADO(repo) que afetem elegibilidade, parâmetros ou reprodutibilidade devem ser resolvidos e revisados antes de qualquer execução. Nenhum resultado deste ciclo poderá ser usado para alterar retrospectivamente gates ou promover pistas.

S0. Escopo e não objetivos
Este ciclo compara as medições históricas elegíveis do pipeline v4 e avalia se delas pode ser derivado um gate de comprimento reproduzível. O resultado esperado é um limiar global proposto, acompanhado de um diagnóstico sobre sua estabilidade e seus limites.

Este ciclo não promove nem reclassifica pistas, não altera o loader, não escreve em paths frozen, não inclui pistas em pools de treino ou avaliação e não executa simulações. Resultados anteriores permanecem rotulados conforme os gates vigentes quando foram obtidos.

O ciclo termina com um limiar proposto para avaliação futura ou, se os critérios pré-registrados não forem satisfeitos, com a conclusão de que o comprimento deve permanecer report-only.

S1. Alvo geométrico explícito
O pipeline v4, conforme o contexto disponível, extrai uma trajetória observada que representa uma racing line, a qual pode cortar curvas e ser sistematicamente mais curta que o comprimento oficial do circuito.

Neste ciclo, a finalidade do comprimento oficial é funcionar como referência de plausibilidade para essa geometria. A concordância com esse comprimento não demonstra que a linha extraída represente a linha central da pista, suas bordas, sua largura ou a geometria adequada para uso como pista de treino ou avaliação.

A finalidade downstream exata dos mirrors no projeto é FALTA_DADO(repo). Este prereg não concede autorização para usar os resultados como certificação de geometria de simulação.

S2. Inventário do pool v4
Antes da calibração, deve ser declarado o inventário completo das pistas elegíveis, incluindo dados obtidos pelo mesmo pipeline v4 em ciclos anteriores. Não se pode adicionar ou excluir uma pista após a leitura de seus deltas.

O ciclo anterior é descrito como contendo sete resultados FAILED, um mirror LasVegas congelado e uma candidata Suzuka comparada. Isso sugere nove pistas naquele lote, mas não confirma que sejam o universo elegível de dados v4.

Pista / chave exata
Fonte e método
Comprimento oficial e proveniência
Comprimento v4
Delta assinado
Status anterior
Elegível para calibração?
Histórico de uso
Lista completa e valores por pista: FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)	FALTA_DADO(repo)

Não v1, mirrors canônicos nem geometrias de fonte ou método diferentes serão usados para derivar o viés de comprimento v4. Os nomes, a proveniência e os valores do inventário precisam ser conferidos antes do congelamento deste prereg.

S3. Camada 1 — validações rígidas de geometria
As regras desta camada são gates binários e independentes do delta de comprimento. Uma pista que falhar em qualquer gate estrutural não segue para a calibração estatística.

O espaçamento nominal de reamostragem do pipeline v4 é Δ* = FALTA_DADO(repo). Os parâmetros numéricos abaixo são PROPOSTOS e precisam ser conferidos contra a implementação e o inventário local antes do congelamento do prereg. Não podem ser ajustados depois de observados os resultados deste ciclo.

Gate
Regra proposta de decisão
Tolerância proposta e derivação
Unidade	A conversão de coordenadas deve corresponder exatamente à unidade e ao fator declarados pela fonte e pelo pipeline. Coordenadas ou fator ausentes, inconsistentes ou não documentados causam falha.	PROPOSTO: após conversão para metros, a razão entre a diagonal do bounding box e o comprimento oficial deve estar entre 0,05 e 0,50. O limite superior decorre da plausibilidade de um percurso fechado; o inferior é um piso provisório de plausibilidade e requer conferência local. A transformação e os dados necessários são FALTA_DADO(repo).
Continuidade	Todas as coordenadas devem ser finitas; não pode haver pontos repetidos consecutivos nem segmentos inválidos.	PROPOSTO: cada segmento, incluindo o segmento de fechamento, deve ter comprimento entre 0,5 × Δ* e 1,5 × Δ*.
Fechamento	A distância entre o último ponto e o primeiro deve respeitar a tolerância de continuidade.	PROPOSTO: distância de fechamento ≤ 1,5 × Δ*.
Espaçamento	Todo o percurso reamostrado deve respeitar a faixa uniforme pré-definida; não se excluem pontos para melhorar o resultado.	PROPOSTO: cada espaçamento consecutivo, incluindo fechamento, deve estar em [0,5 × Δ*, 1,5 × Δ*]. O valor de Δ* é FALTA_DADO(repo).
Topologia	O resultado deve ser um único ciclo fechado, sem ramificações nem auto-interseções entre segmentos não adjacentes. Interseções em vértices compartilhados por segmentos adjacentes são permitidas.	Aplicação por teste determinístico de interseção de segmentos. PROPOSTO: tolerância numérica de interseção ≤ 0,01 × Δ*; requer conferência da representação numérica e implementação.
Saltos na amostra ordenada	A ordenação temporal deve ser estritamente crescente. Uma amostra sem coordenada ou timestamp necessário, ou com deslocamento fisicamente implausível, falha; não se consulta a rede para completar dados.	PROPOSTO: sinalizar quando a velocidade entre duas amostras exceder 120 m/s. O valor é um limite provisório amplo, não um fato validado; deve ser conferido antes do congelamento. Cadência, ordenação e presença de timestamps são FALTA_DADO(repo).

A lista concreta de checks que a implementação atual consegue executar e os dados necessários para cada um são FALTA_DADO(repo). Se uma regra não puder ser aplicada mecanicamente com os dados disponíveis, o resultado será FALTA_DADO(repo) e o gate não poderá ser declarado aprovado.

S4. Camada 2 — calibração do viés de comprimento
A calibração usa somente pistas declaradas elegíveis no S2 e extraídas pelo mesmo pipeline OpenF1 v4. Cada pista é uma unidade independente de validação. Não se dividem pontos ou voltas da mesma pista entre calibração e validação.

Para cada pista elegível i, define-se o delta assinado:

δᵢ = 100 × (Lᵢ,v4 − Lᵢ,oficial) / Lᵢ,oficial

Comprimentos oficiais devem vir de uma proveniência e revisão consistentes, registradas no inventário. Essa proveniência é FALTA_DADO(repo).

Escolha pré-registrada: usar um único limiar global neste micro-ciclo. Não serão ajustados limiares por classe. A amostra disponível é pequena e subdividi-la em classes elevaria a variância e permitiria adaptar os limites aos resultados observados. Classes, se já constarem no inventário, poderão ser reportadas descritivamente, sem participar do limiar.

LOO por pista: para cada pista j, ajusta-se a regra usando as demais pistas elegíveis. No conjunto de ajuste, calcula-se o viés como mediana dos deltas e a dispersão robusta como 1,4826 × MAD, em que MAD é a mediana dos desvios absolutos à mediana. A pista excluída passa no fold se seu delta estiver no intervalo [mediana − 3 × dispersão robusta, mediana + 3 × dispersão robusta].

Os valores 3 e o mínimo de cinco pistas de ajuste por fold são PROPOSTOS para este rascunho e devem ser aceitos ou substituídos antes do congelamento. Não poderão ser recalibrados após os folds. Se qualquer fold tiver menos de cinco pistas de ajuste, dispersão nula, dados incompletos ou resultado não calculável, o limiar desse fold é inválido e a limitação é reportada.

Não se escolhe entre limiar global e por classe depois de observar o LOO. Se a estrutura do inventário tornar a escolha global inviável, este ciclo termina como report-only; criar uma regra por classe exigirá outro prereg.

S5. Camada 3 — holdout
Antes de expor os deltas candidatos ao processo de calibração, deve-se verificar se existe ao menos uma pista v4 elegível, com stream completo já em cache, que não tenha sido usada para derivar o gate e cujo resultado não tenha sido usado para escolher sua regra.

A existência e a elegibilidade desse holdout são FALTA_DADO(repo). Sua seleção deve ser registrada no inventário e ocorrer antes de revelar seu delta. O holdout não participa do ajuste nem da escolha do limiar e é avaliado uma única vez pela regra congelada.

Se não houver holdout elegível, não se busca um stream pela rede. O prereg registra ausência de validação independente; o LOO permanece diagnóstico exploratório e não valida generalização.

S6. Árvore de decisão completa
Ramo 1 — limiar válido no escopo pré-registrado. Este ramo só se aplica se:

o inventário completo estiver fechado e os gates estruturais forem calculáveis;
todos os folds LOO forem válidos e passarem o critério pré-registrado;
houver holdout independente elegível e ele passar pelo intervalo pré-registrado;
nenhum parâmetro tiver sido alterado após a leitura dos resultados.
O limiar poderá ser documentado como proposta para avaliação de futuras pistas v4 dentro do escopo amostrado. O PARE registrará a fórmula, os dados usados, os folds, o resultado do holdout e as limitações. Isso não promove pistas, não altera o loader nem muda o status dos resultados anteriores.

Ramo 2 — nenhum limiar válido. Se qualquer condição acima falhar, não se escolhe um novo número, não se muda o método e não se reprocessam pistas para alcançar aprovação. O comprimento permanece como descritor report-only para este ciclo. O PARE registra a causa, os dados ausentes e o próximo dado necessário. Qualquer novo método exige outro prereg.

S7. Regras da casa aplicáveis
Prereg próprio antes de qualquer patch, script ou chamada de rede.
Este ciclo não deve consumir chamadas OpenF1; se um stream estiver ausente do cache ou incompleto, falhar com FALTA_DADO(repo).
Nenhuma promoção ou reclassificação de pista.
Nenhuma escrita em paths frozen canônicos.
Nenhuma simulação.
Cache-first obrigatório; nenhum fallback para rede.
O teto de 25 chamadas OpenF1 é declarado para contexto, mas não autoriza chamadas neste ciclo.
Não alterar pools de treino ou avaliação.
Preservar resultados anteriores sem post-hoc re-pin.
S8. Formato do PARE esperado
O PARE final deve conter:

o inventário completo, sua elegibilidade e a proveniência dos comprimentos;
o resultado individual dos gates estruturais, sem exceções manuais;
os parâmetros e fórmulas pré-registrados, incluindo valores propostos que tenham sido congelados;
os folds LOO, o holdout independente ou sua ausência, e a decisão mecânica da árvore do S6;
os limiares propostos, se válidos, ou a justificativa report-only;
as limitações e os dados ausentes.
Usar obrigatoriamente a expressão "diagnóstico exploratório". O PARE deve dizer explicitamente o que o gate não prova: generalização para outras pistas, adequação da racing line como linha central da pista, qualidade das bordas ou largura, segurança do piloto, desempenho do modelo e adequação ao treino ou à avaliação.

A suíte deve ser descrita como "349 testes, com 20 falhas bit a bit estáveis ('regressão estável conhecida') e 3 skips". Não rotular como "suíte verde" ou "validação completa".

S9. Limitações a divulgar
Amostra pequena de pistas implica alta variância e baixo poder para distinguir comportamentos por classe.
LOO por pista é diagnóstico exploratório; não substitui uma validação externa independente.
Um único holdout, mesmo que passe, não demonstra generalização ampla.
O viés de comprimento se refere à relação entre o comprimento medido pela racing line v4 e o comprimento oficial, dentro da proveniência registrada.
A aprovação estrutural e a plausibilidade do comprimento não certificam a geometria como centro de pista ou como artefato adequado ao simulador.
A ausência de dados elegíveis, cache completo, timestamps ou proveniência impede declarar aprovação; não será contornada por rede ou julgamento manual.
S10. Auto-checagem
Requisito
Cobertura neste rascunho
Três camadas separadas	S3 gates estruturais; S4 calibração só v4; S5 holdout separado.
Adendo 1 — inventário completo antes da calibração	S2; inventário e histórico de elegibilidade ainda FALTA_DADO(repo).
Adendo 2 — LOO exploratório e limitações	S4 e S9.
Adendo 3 — escolha global × classe pré-registrada	S4; limiar global proposto; sem ajuste por classe.
Adendo 4 — classes definidas antes dos deltas	S4; classes não participam do limiar e não serão criadas post hoc; taxonomia existente, se houver, é FALTA_DADO(repo).
Adendo 5 — alvo geométrico explícito	S1; uso downstream exato dos mirrors continua FALTA_DADO(repo).
Adendo 6 — regras e tolerâncias reproduzíveis	S3; parâmetros numéricos estão marcados como propostas pendentes de conferência.
Adendo 7 — separação calibração, treino e avaliação	S0 e S7 proíbem uso em pools neste ciclo; inventário de uso histórico por pista é FALTA_DADO(repo).
Árvore com dois ramos definidos antes dos dados	S6.
Regras de rede, promoção e paths frozen	S7.
Rotulagem correta da suíte	S8.

Lista consolidada de FALTA_DADO(repo):

inventário completo de pistas elegíveis v4, incluindo ciclos anteriores;
chave exata, fonte, método e revisão do pipeline para cada pista;
comprimento oficial, sua proveniência e revisão;
comprimento medido, delta assinado e status anterior por pista;
histórico de uso de cada pista para calibração, treino, avaliação ou escolha de método;
existência de holdout independente elegível e stream integral em cache;
fator de conversão de unidade e metadados necessários para verificá-lo;
espaçamento nominal Δ* da reamostragem v4;
ordenação, timestamps, cadência e completude dos streams para o gate de saltos;
taxonomia de classes existente, caso se deseje reportá-las descritivamente;
compatibilidade dos limites propostos com a implementação e com o inventário antes do congelamento do prereg.
Ressalvas do redator: sem resolver os dados acima, este texto permanece um rascunho e a execução não deve começar. A presença de dados históricos já vistos pode impedir que qualquer pista do inventário seja um holdout verdadeiramente independente; nesse caso, o resultado correto é LOO exploratório e gate report-only, conforme S5 e S6.

Memória consultada: não.
