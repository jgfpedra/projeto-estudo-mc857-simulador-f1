# REALISMO-1: armazenamento dos CSVs

Os 186 CSVs de corrida foram compactados sem perda como `.csv.gz` para reduzir
o tamanho do checkout. O conteúdo descomprimido foi validado byte a byte pelo
SHA-256 antes de remover cada CSV original.

`CSV_COMPRESSION_MANIFEST.csv` mapeia cada nome original para o arquivo
compactado e registra hashes e tamanhos de ambos. Os hashes SHA-256 citados nos
relatórios de execução continuam sendo os hashes dos bytes descomprimidos.

Para recuperar um CSV individual:

```sh
gzip -cd c7/10_ON_INTERLAGOS_N6.csv.gz > /tmp/10_ON_INTERLAGOS_N6.csv
```

O pandas lê diretamente os arquivos `.csv.gz`; o script `c6a_train_analysis.py`
foi atualizado para usar esse formato.
