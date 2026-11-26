# Geometrias históricas aproximadas

`f1results_tracks.json` é um banco derivado da release `v2.10.1+20260921` do [F1 Results Database](https://github.com/mclarenmp4-22/f1resultsdatabase), banco distribuído sob a [ODbL 1.0](ODbL-1.0.txt). Os SVGs de origem foram traçados de mapas do [StatsF1](https://www.statsf1.com/). Os IDs e localizações de `f1db_circuit_locations.json` vêm do [F1DB](https://github.com/f1db/f1db), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). A licença MIT do código do projeto não substitui as licenças dos dados.

A cópia compacta contém **106 geometrias em 57 circuitos e 700 combinações circuito/temporada** identificadas sem ambiguidade. Não inclui o banco original de aproximadamente 325 MB nem exige acesso à rede em execução. O SHA-256 do SQLite de origem e dos dois arquivos F1DB usados no cruzamento está no próprio JSON; cada entrada referencia o GP e o layout da fonte.

Os waypoints são **aproximações**, reconstruídas dos contornos desenhados. A largada e o sentido usam os marcadores identificados pela fonte; não foram medidos ou verificados independentemente. Não há informação de altitude ou largura: a largura é assumida como 12 m. O comprimento usa o campo de cada GP no F1 Results Database. Por exemplo, Interlagos 1973 usa 7.960 m e 1979 usa 7.874 m, ainda que o catálogo F1DB local atribua ambos ao mesmo ID. Diferenças de raio de curva, escala local, largada e largura são possíveis. O arquivo `f1results_rosters.json` acrescenta 1.163 GPs e 1.066 pilotos, de 1950 a 2026, sem incluir o SQLite original. Os pilotos da corrida são aqueles com posição de largada registrada no GP. A fonte não contém cores de equipes nem siglas oficiais. O backend usa uma paleta local por equipe e gera uma cor estável para equipes fora da paleta. A sigla é gerada a partir do nome do piloto. A resposta informa a origem da cor e da sigla. Dez eventos não foram associados com segurança a um ID F1DB e aparecem como não mapeados. Quando um circuito recebeu mais de um GP no mesmo ano, a criação da corrida não escolhe um arbitrariamente. O modelo físico continua sendo o do simulador atual, não uma reprodução dos carros históricos.

A importação só aceita mapas com largada identificada, uma seta de sentido e linha central fechada sem ramificações. Também exige coincidência de localização e ano no histórico F1DB, e rejeita corridas ambíguas. Com a release indicada, 55 mapas tinham linha central ambígua/ramificada, sete não tinham largada aceita, um tinha sentido ambíguo e dois não puderam ser associados com confiança a um circuito; eles não foram incluídos. Os mapas não são automaticamente atualizados quando o F1DB muda.

## Regenerar a partir de um SQLite oficial

Baixe `sessionresults.zip` da [release da fonte](https://github.com/mclarenmp4-22/f1resultsdatabase/releases) e extraia `sessionresults.db` para fora do repositório. Para atualizar, instale as dependências **apenas no ambiente de importação**:

```bash
python -m pip install -r backend/scripts/tracks/requirements-historical.txt
python backend/scripts/tracks/import_f1results.py \
  --db /caminho/sessionresults.db \
  --f1db-catalog backend/config/historical_tracks/f1db_circuit_locations.json \
  --f1db-layouts backend/config/f1db_layouts.json \
  --release 'v2.10.1+20260921' \
  --output /tmp/f1results_tracks.json
python backend/scripts/tracks/import_f1results_drivers.py \
  --db /caminho/sessionresults.db \
  --f1db-catalog backend/config/historical_tracks/f1db_circuit_locations.json \
  --f1db-layouts backend/config/f1db_layouts.json \
  --release 'v2.10.1+20260921' \
  --output /tmp/f1results_rosters.json
```

Confira o diagnóstico, os anos selecionados e a licença da versão nova antes de substituir o catálogo. Para uma nova versão do F1DB, atualize também a lista de localizações e o catálogo de layouts: o cruzamento exige coordenadas próximas e anos de GPs compatíveis. O runtime não depende de Pillow, SciPy ou scikit-image para carregar o snapshot. `F1_RESULTS_TRACKS_PATH` permite apontar para outro snapshot no backend.

`F1_RESULTS_ROSTERS_PATH` permite selecionar outro snapshot de pilotos e eventos. A lista de pilotos de uma temporada inclui inscritos de vários GPs; equipe e número vêm da última inscrição registrada, indicada em `source_grand_prix`.
