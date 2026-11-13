# EXECUÇÃO REALISMO-1 · C6-B2 — `--lat-offset-slots`

**Data:** 2026-11-04
**Freeze:** `cb0ebe856c0dd93709e3bd8128b2f4206a80a2ce`
**Estado:** execução concluída; relatório staged sem commit.

## 1. Veredito operacional

- Implementação opt-in de `--lat-offset-slots` nos dois runners.
- Teste focado C6-B2: **14 passed**.
- Suíte serial: **20F/497P/3S**, com fail-set idêntico ao baseline histórico de 20 falhas.
- Controles canônicos: 4/4 passaram `cmp` no CSV e sidecar.
- Tratamentos ON: 20/20 concluídos, com 30.002 linhas e sidecar.
- Extração: 96/96 leituras determinísticas; todos os pares passaram `cmp`, cross-hash e `integrity.ok=true`.
- **Veredito formal C6-B2: FAIL nos gates de segurança/primários.** A flag permanece não homologada e não deve ser promovida ao C7.

## 2. Implementação

A flag altera somente o canal policy-facing `obs4`:

```text
tels[i, 4] = (signed - off_i) / hw
```

com `hw=6,0 m`. `drv_signed`, `drv_lat`, raios, `s`, posição, heading, CSV físico, longitudinal, residual e física permanecem inalterados.

Vetores congelados usados:

- Composite: `[0.273, -1.000, -0.693, 0.590, 1.000, -0.784, 0.018, -0.902, 0.064, 1.000]`;
- Blind: `[0.251, -0.003, -0.549, -0.042, -0.879, -0.518, 0.896, 0.142, 0.694, 0.180]`.

O runner visual recebeu o mapeamento driver-slot. A flag default OFF permaneceu sem alteração no caminho canônico.

## 3. Controles e tratamentos

| Run | Perfil | Pista | N | Contatos | Laps | Fora rows | Fora% | Colado s | Deadlocks |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | composite OFF | Interlagos | 0 | 107 | 44 | 7905 | 26,4 | 32,6 | 0 |
| 2 | composite OFF | Monaco | 0 | 210 | 31 | 14963 | 49,9 | 80,2 | 1 |
| 3 | blind OFF | Interlagos | 0 | 764 | 49 | 6769 | 22,6 | 178,2 | 6 |
| 4 | blind OFF | Monaco | 0 | 696 | 32 | 14236 | 47,5 | 108,6 | 3 |

### ON: Composite

| Pista | N | Contatos | Laps | Fora rows | Fora% | Colado s | Deadlocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 0 | 375 | 44 | 8108 | 27,0 | 69,4 | 1 |
| Interlagos | 1 | 521 | 44 | 7745 | 25,8 | 77,8 | 1 |
| Interlagos | 2 | 457 | 44 | 7784 | 25,9 | 52,0 | 1 |
| Interlagos | 3 | 338 | 43 | 8018 | 26,7 | 30,2 | 0 |
| Interlagos | 4 | 434 | 45 | 7949 | 26,5 | 119,2 | 6 |
| Monaco | 0 | 255 | 32 | 14484 | 48,3 | 70,6 | 2 |
| Monaco | 1 | 394 | 30 | 15192 | 50,6 | 115,4 | 2 |
| Monaco | 2 | 359 | 31 | 14849 | 49,5 | 140,2 | 4 |
| Monaco | 3 | 1068 | 30 | 15330 | 51,1 | 233,4 | 4 |
| Monaco | 4 | 598 | 30 | 15143 | 50,5 | 113,0 | 3 |

### ON: Blind

| Pista | N | Contatos | Laps | Fora rows | Fora% | Colado s | Deadlocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 0 | 816 | 45 | 7693 | 25,6 | 126,4 | 1 |
| Interlagos | 1 | 991 | 46 | 7246 | 24,2 | 136,8 | 4 |
| Interlagos | 2 | 1301 | 47 | 7033 | 23,4 | 184,0 | 6 |
| Interlagos | 3 | 1428 | 43 | 8074 | 26,9 | 158,6 | 4 |
| Interlagos | 4 | 1069 | 50 | 6558 | 21,9 | 171,0 | 5 |
| Monaco | 0 | 561 | 32 | 14151 | 47,2 | 60,6 | 1 |
| Monaco | 1 | 675 | 32 | 13991 | 46,6 | 97,4 | 2 |
| Monaco | 2 | 1080 | 31 | 14460 | 48,2 | 149,6 | 2 |
| Monaco | 3 | 1074 | 30 | 14326 | 47,8 | 134,4 | 2 |
| Monaco | 4 | 642 | 33 | 14448 | 48,2 | 100,8 | 3 |

## 4. Gates formais

| Perfil | Pista | Gate | ON observado | Limite | Status |
|---|---|---|---:|---:|---|
| Composite | Interlagos | C6 colado | 1743 | `<815` | **FAIL** |
| Composite | Interlagos | C6 deadlock N0..4 | `[1,1,1,0,6]` | `<= [0,0,0,1,1]` | **FAIL** |
| Composite | Interlagos | B-1 contatos | 2125 | `<=589` | **FAIL** |
| Composite | Interlagos | R-1 laps | 220 | `>=209` | PASS |
| Composite | Interlagos | R-2 fora | 39604 | `<=41025` | PASS |
| Composite | Monaco | C6 colado | 3363 | `<2005` | **FAIL** |
| Composite | Monaco | C6 deadlock N0..4 | `[2,2,4,4,3]` | `<= [1,1,1,1,1]` | **FAIL** |
| Composite | Monaco | B-1 contatos | 2674 | `<=1155` | **FAIL** |
| Composite | Monaco | R-1 laps | 153 | `>=147` | PASS |
| Composite | Monaco | R-2 fora | 74998 | `<=76315` | PASS |
| Blind | Interlagos | C6 colado | 3884 | `<4405` | PASS |
| Blind | Interlagos | C6 deadlock N0..4 | `[1,4,6,4,5]` | `<= [6,6,6,6,6]` | PASS |
| Blind | Interlagos | B-1 contatos | 5605 | `<=4202` | **FAIL** |
| Blind | Interlagos | R-1 laps | 231 | `>=232` | **FAIL** |
| Blind | Interlagos | R-2 fora | 36604 | `<=35345` | **FAIL** |
| Blind | Monaco | C6 colado | 2714 | `<2565` | **FAIL** |
| Blind | Monaco | C6 deadlock N0..4 | `[1,2,2,2,3]` | `<= [3,3,3,3,3]` | PASS |
| Blind | Monaco | B-1 contatos | 4032 | `<=3828` | **FAIL** |
| Blind | Monaco | R-1 laps | 158 | `>=152` | PASS |
| Blind | Monaco | R-2 fora | 71376 | `<=72680` | PASS |

O mecanismo falhou principalmente por aumento de contatos e colado no composite, e por regressão de contatos/ritmo/fora no blind Interlagos. Não há promoção da flag para o C7.

## 5. Extração e integridade

Os 24 runs produziram CSV, sidecar e log. Cada run teve duas leituras de `base_metrics` e duas de `realismo_metrics`:

- 96 leituras totais;
- 48 pares byte-idênticos;
- `canonical.metrics_sha256` conferiu com o `metrics_sha256` de `base_metrics` em 24/24 runs;
- `integrity.ok=true` em 24/24 runs.

## 6. Encerramento

C6-B2 está concluído com **FAIL formal**. A flag `--lat-offset-slots` permanece research-only e não deve ser combinada ou promovida em C7.

Nenhum commit foi feito nesta etapa. Este relatório e os artefatos ficam staged para o Closing do Dono.

## 7. Hashes e proveniência

### 24 arquivos de corrida

| Run | CSV SHA-256 | events SHA-256 | log SHA-256 |
|---:|---|---|---|
| 1_CTRL_COMPOSITE_INTERLAGOS_N0 | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` | `3ffd979e23e50840b17ad066f23574f1f5c2f6284c529bcbcac890774fc876c7` |
| 2_CTRL_COMPOSITE_MONACO_N0 | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` | `ec97364b999877edcc7721ae84a052e91a98d31e8b8785a1341cbaf1e6224c6c` |
| 3_CTRL_BLIND_INTERLAGOS_N0 | `9d2a08427d4c5bdad0d6611df2caa7b4d7f02c5a5584c71a49d412c763c67e12` | `4260568e2b453899cfc12e25576d780a2592338cd8909a369a7e4a3a3ce781ed` | `7d9c21f0f8044f1c60d51c2bb40075e6e420ad204f05071422510118d3c07241` |
| 4_CTRL_BLIND_MONACO_N0 | `15fb3da069adb7369741e90fdffca00f12cbe2abd75481b217c9c962bfacdd11` | `8a5f461e010571341528a17ddf2aa612f245b74152755d3ef1e1596b5c4ca527` | `282c6885dfe2e64956f2e72b6982860ee5f4949c9ebc46e6c069e3572b4ca948` |
| 5_ON_COMPOSITE_INTERLAGOS_N0 | `af424ae006f480c9874f1176cb6b6ad887c0cddafedb0a8b0360bfcbe27274a8` | `bda19c5ebcbffbd1cea81f1e8f7679ec71c917c1d617b749b74dbf8c43b57058` | `dc895fc68d542654d82dfdf5d64b7677d3e06e4e30468d9851568d94b58dad9e` |
| 6_ON_COMPOSITE_INTERLAGOS_N1 | `c3314d1f50969cab5027f742aee7650419cc9bf0148104b23acbcf9b152e8da6` | `0466b488b16dc362d4f2fbe0dc930723b0361376ed423fb02be7358180edaae2` | `8c077e7265727fcc8d0b13f94a97bc1d8207b2de3370835c37fb850f0280025d` |
| 7_ON_COMPOSITE_INTERLAGOS_N2 | `a4610b3bbeef2146fbf421587b5003c5e225c04a33d3e2aa9f92e8e09ffe6b9b` | `0d077339fe54263d05a083ce8c34973fd1f4dbe911045c14f1d5b045856fb2ca` | `45a4a2fe952dada91241bc22819437ea83fa05ff0b8d5a2c001710ec2258fee4` |
| 8_ON_COMPOSITE_INTERLAGOS_N3 | `f2885d5339c54111fc4caee5e5219c58370d7126f19790213be87b301afa48ff` | `56d356d05f7197e657d43006e99f763b53a3a2cee7165c32518d986b3669509e` | `a4694ab6cdeb9e13dc0601cd47a9f2ce6936459c567805bd3d961a17a15f54e9` |
| 9_ON_COMPOSITE_INTERLAGOS_N4 | `ea742fdd3dfc1a48fbb67cdac48dafc68d69f8750e89b4602ad6abdcecf3b726` | `f8c149da0c13ff5d10195d91172a5738de79a2fb37e9e8dbfd47d00f798e7cff` | `2c03778d908252dada7e2e9dd823791b5c96f17b6579c58e4620882f9794de54` |
| 10_ON_COMPOSITE_MONACO_N0 | `221d0405db63b5776b5171706966683d3df7870cb30c049d416c5c10f661c132` | `46b599c9e904bef37bf9a7edc28ed4b82fbf541f344bd616c808e2b32d183eb6` | `db1b5835cd39ca3415d0a842f1d2818e84674d3fa9fca7f0d6a0003c3fe400f0` |
| 11_ON_COMPOSITE_MONACO_N1 | `ece1f22effdf35125c7bebd5983fb166ef51eb38beeaef524cd75d5fbe39f4cc` | `22cf95996fce79d4855c24b74a6cea9c239045b989dc0df781d851795c27ae2f` | `a6976250d1f9ace1188054b964281bbf96c64137e9f7374b1cd29e8dffa719e4` |
| 12_ON_COMPOSITE_MONACO_N2 | `e0a3bdbcd162c56688beeb0659974fe14028a1f5813da2936533c5a4e34fa8fd` | `999bd71f9bf03367742d1ff9b8fb1f215a7f82c6d19680632c6fbe52475153f6` | `1fedcb2d5d07cd5e46ef0d0073f826d02675251deda072d22573d787d7b2df43` |
| 13_ON_COMPOSITE_MONACO_N3 | `9f73222f49f00b9baa6ca4a80767dbda18d550a302f2670ba000b037ba992e4d` | `4d232ef04940eb555dfc7b6b7bd1e5c719ab0726260bc2314f9c045b3fe85bca` | `3010f3819bb83b5a2d411b353ff3158e2179a75ab6257b7c7dc633cf3cca1194` |
| 14_ON_COMPOSITE_MONACO_N4 | `2c4aff8bfeb4596dd54e600028ed5ad4e975061feffb6db90e650a9d04c6fc20` | `d51493a106f38b99e4988cea3fcf33712614993d6f6dedac4ad87b2685b6df81` | `8f65f05153823207a6ddacc665583434d4683da2c98dace87a72dfde2cd888cd` |
| 15_ON_BLIND_INTERLAGOS_N0 | `d3567b39652207f2b6d5d495ff3b4b91e6e95d192a250e6ab100f426128a5cce` | `eb8453ea288c716343b2ee6e793c222e1045c5949325ee512f4345ded92aa520` | `663501e93cc73e2a8c4a90d802cb0bdaf93b462f85b4397f2526c4af5f74104a` |
| 16_ON_BLIND_INTERLAGOS_N1 | `2633101de05bde450e245f7d476a81dcd3addf8b134cdb5776a4858e811cc717` | `7a3b409062c4aa26ac91f229452a882a74a025f53c1a839dd9648df4561b56ae` | `1bed7989399a037e4be778335c0e2f9bd17c7378700311ba2c0b08407ce7a67d` |
| 17_ON_BLIND_INTERLAGOS_N2 | `ad2e602ab5d408c6d80846b465e5a51c6d663c5b6b0c3806c4af193c529adc99` | `baccae47c7806bd1b8ef6ce12904ec291ab91f51d932c0509459b1d8a9faa0fc` | `ddeb13c16043dcc86e7b1c9e3613f635087e45709725999f61c6eb7575acd011` |
| 18_ON_BLIND_INTERLAGOS_N3 | `ebdf137277c7232929877daa4875ab35d0c782c6f5e55ed271bbf0fd967db34e` | `40f7325ded328f75f590ae69fa1df150890be1f24b524d6c56ed8fa2e2918026` | `a455a043bd7764c4eaa1a0a774580a3bbfb6a06b00515065faec5a21629a18cf` |
| 19_ON_BLIND_INTERLAGOS_N4 | `2693d062b350c4fb4abfbdf5fe067da88a1c2fe2a0ee0bc971e0358655bcc5c3` | `09b47ebd06a876689d4efb753206f5c49ecceaf9a92dc03334ca7f80218152da` | `75fe092a41bffca0a0c1f2f2164ccae1c40cba85c7036f15f8b20df7cc4f8bdc` |
| 20_ON_BLIND_MONACO_N0 | `4728d25747c32895e9d1c894cf9782daf9fd418bbf91ce0fcfa56e9c8337d3bf` | `2b1a667e88787fdd7388d77a4902d9ce2e6959826e1ca389c7ed215068a3728e` | `e2e870fea23b8e476daccf17932bfeabccba9f79a5fc65a8a1acc7457e4e6a87` |
| 21_ON_BLIND_MONACO_N1 | `1cb441094e19c9ad627f72fb1383aa76a511ce9083c146e823c2dac02c0e27e5` | `8e62a5734bd17116b13d923ff597cc19e92de11e8faf8b52d3aaf269fd7015eb` | `c1ae98acc27b0f95bd5ec58f49eed44a478b99c6640c44574de47e1f4c63b7e6` |
| 22_ON_BLIND_MONACO_N2 | `673d01b2cad3371d3732d99e8010daae755f8ce4170b142ab424127292f42a68` | `7f58000831100773fef51b89b173b92871594d269d50de034b263398eac7f4e8` | `1a3a14256b1150eb609732d692358b1824d72a91867bb473f098b28371ef77d4` |
| 23_ON_BLIND_MONACO_N3 | `3ec2e21180f3dedaffb67579e34b6dadd4cff23b414bbb5c8456fa8e53b72436` | `50e3ec8579fd6f7349ef62893cff6c3cc4f2cb7d1c9cef29fdcd672f59162ff5` | `23a8dca9bab68bad9702771932f44a7ebe0740ef7691bd9b3cd1ca719de78240` |
| 24_ON_BLIND_MONACO_N4 | `1b41727d9ae0870e20f7fd7e51e752cbf8d2b77c50a196a727eba393bc366785` | `cd80cad368846576f58d8985a3db125d02ae108444edd41aa137a7bdcc91c15b` | `4ebf119be456b26086957eadd4a5125ae13b4040a6168e84b5e185e21de5a2df` |

### JSONs de extração

| Run | base_metrics SHA-256 (read1=read2) | realismo SHA-256 (read1=read2) |
|---|---|---|
| 1_CTRL_COMPOSITE_INTERLAGOS_N0 | `c5b43eb5c4bf12cc6bcb3d49facf43616fd67f700c23ba1bdaaee7979a585d6f` | `018a1cc486a7b8f6e67d9246c15e7513f72314e9b68428529866eb2144e49c85` |
| 2_CTRL_COMPOSITE_MONACO_N0 | `14a9c61729231af56e264815dd1fe46037d86707889caffbbcbb705f73f495b5` | `c7659d46306e87823cda08ae0f65d4c43d41356d64a585026137b4cfb174aa85` |
| 3_CTRL_BLIND_INTERLAGOS_N0 | `a953e3df9b32a84728687b63cd0b489346d5d37d0df71aaef309981825d61066` | `f9686ea28e2ecbdf45ceae5d2349ccbe03cbf093fcbadecb76d97a3ab017251e` |
| 4_CTRL_BLIND_MONACO_N0 | `1f9b8a8791fcd2b35f7aaedeaa20e26b6ba133cc2efefd73e6400d603f46a539` | `b2de2d9d2c4839845daa1ccb0ec2e9a5e56b8a82f63f6330e97445742c1867cb` |
| 5_ON_COMPOSITE_INTERLAGOS_N0 | `0db09aad5cf067016d05aacb2441bc7e6cd59d641581a3a47cef2cc3784adc8c` | `ea7ea8d925d6695823c4ed825b88c2ac839d96519d1d8157a92968e7cf62af54` |
| 6_ON_COMPOSITE_INTERLAGOS_N1 | `ecbe7f570e88b348aff843aabb7dee7dc6484f5f86d471f8a962df338b60fade` | `5fcdadad427709662b2568c253c05c7fe314d073da9ffa15d85df040324a1f05` |
| 7_ON_COMPOSITE_INTERLAGOS_N2 | `c86a5c39369f13ce05278feaab90808d04b7bd87a9301af420938fd5f6d8ded2` | `71b0ae05c7d34d295678eb5c994e4ad8b65f14a4b23eb053ffaebacdf8e24d19` |
| 8_ON_COMPOSITE_INTERLAGOS_N3 | `d031ff306c37c34cd752feb204d04dcee6161823dbf0e840743d21fd73285252` | `bc9fb5aa86a5abc5d6d99ae4a0e47b62d47c99be20e4118e8c1f4df4a67cf649` |
| 9_ON_COMPOSITE_INTERLAGOS_N4 | `f91f783977c0c0d5648f1d71ff7c6b570eb2e2fe7a8d2430af455924eda469a6` | `0c8b4bbf45c21700abb9090866e033418725f0d71846e4f0f9647850e3f84f8b` |
| 10_ON_COMPOSITE_MONACO_N0 | `a3fa0921d2277c869810b07078c3ce2acb3e1457658f63e15e08b5a36a915e64` | `bd9bc4f080b00111929d02a02e3c8fbfacd97d2eb6e544a6064939ce057e0396` |
| 11_ON_COMPOSITE_MONACO_N1 | `ae5ef7467125d26e5cb769f89bf475a4703bca3e55c12907f3c92677d775a1f9` | `03e681acef1b50e8365851cb015f84ffb67c1f92eab940a57f642d12db53f717` |
| 12_ON_COMPOSITE_MONACO_N2 | `b550443969da0ebce27c657c081544772dc1355a813525dcdf7500c2381ca630` | `32ac2d37490495054f273f970d3b4065edfbb6968c176d118796dad12bd79e6b` |
| 13_ON_COMPOSITE_MONACO_N3 | `0147ae25d45a8f2fadacb6569d0e3505fbd530bbd562346e45c47be07a1b20c5` | `193921c13deac0ca0c0a1866c7d4e7d1fa529cc0366313c2305a5db8fc2b62df` |
| 14_ON_COMPOSITE_MONACO_N4 | `9f450e63ff6559c0a43d9604ac118c5bdc1dcc0b2044ce75cbb95ecad808b12e` | `73213b63951760041bd16b9dfc5a04fac365032baad8b2bde9327fc7490a5ba0` |
| 15_ON_BLIND_INTERLAGOS_N0 | `c959d6535d80af796a022428b92ed21624618efbc7d7849740a690cb83a791f6` | `5e4452ec564310f0188b156f4b677db8da1b6a564f9f97446847c6f6ffc22025` |
| 16_ON_BLIND_INTERLAGOS_N1 | `a26a1a8c2390008cda78582bfbe0046139c9b5f71d1489efa0e0850130e649cd` | `bab5257fe21b5d7474174eaf60a49d6025f9f68c970c1b514a7e138cac3c1d89` |
| 17_ON_BLIND_INTERLAGOS_N2 | `d220be7155dfc91e14a9c1ed410c48e236aeee8e9c5881bbd7416ddc15b7b496` | `2e9c1dc559266151b8d0651d69b8fa7efca8222cf6ae1a7eb4e357a63d2e9e82` |
| 18_ON_BLIND_INTERLAGOS_N3 | `e0d51a3ec4d62647ec19b62971a38355110a482d562a6b328aab095fce207e9f` | `152bd3ef4d424fd04524e2a8426e63704520992486fa15c5e9bb04cfb6e0671a` |
| 19_ON_BLIND_INTERLAGOS_N4 | `184ba70ff497e34ae4b3cc0573c7d53d47b507a62c06a70486c5a42abd340e6b` | `c7b24d6c1875573f7629e515bc692a8dcc5be17d87a3ab3f2b0857b8fcebf098` |
| 20_ON_BLIND_MONACO_N0 | `018887c9b79468941cfd631bf28d53a445f506fb039c882b16615d0e47048523` | `72a88349dc012fd014cec8ae1f6d0471000c7e319d39136c793d42dcb8664405` |
| 21_ON_BLIND_MONACO_N1 | `aa804dc46a41315785477a353c90df71d484e3c61fb80d5e9a32ac8023000aac` | `9f791084686d069ebeb06dfb8fe0ed2238e49096aa8ef3a32e641227272b4e43` |
| 22_ON_BLIND_MONACO_N2 | `0a10459405e7042670beb78e4bcb79a49f7a417e675c9882693af71880b707ba` | `fc1eb2befad975af8df186ea2b7f414e3c04ba3c03743544a0f1d0e78bd2576e` |
| 23_ON_BLIND_MONACO_N3 | `fc28c6b8acf9dce23fc6e4da0821d57c95c5be47a43a13500b3540cf2fdf81cd` | `73bc98aa0ddef9807e92c941448c00d4fa70453c52330a84f8422dc8c7902a28` |
| 24_ON_BLIND_MONACO_N4 | `ca7a4d1fae75ae7b631f6c06a70f2d745361978076e281f63a2b34595bc6b255` | `f1fd3431fcd05da2055a88f0f8c0e5c9cd8ed8fe3f252faee39f87b1fb87725e` |

## 8. Apêndice do dono — verificação independente e closing (2026-11-04)

1. **Verificação de integridade.**
   - HEAD base `883a8ca46baf9c541b5d8a03f8c1f368bb78d2fd` (Provenance REALISMO-1 C6-B1).
   - 176 arquivos staged com rastreabilidade completa: código opt-in C6-B nos dois runners (`race_diagnostic.py` e `run_race_10_cars.py`), novo teste de conformidade (`tests/test_lat_offset_slots.py`, 14 passed), suíte com fail-set idêntico ao canônico (20F/497P/3S, zero nova falha), 24 corridas completas (30.002 linhas, sidecars e logs), 96 arquivos de extração determinística (48 pares read1/read2 com cmp=0, `canonical.metrics_sha256 == base_metrics.metrics_sha256` e `integrity.ok=true` em 24/24), 3 ledgers idênticos e o presente relatório de execução.
   - Strays não rastreados (`.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`) rigorosamente preservados fora do stage e do repositório.
   - 4 controles canônicos (2 composite, 2 blind) com identidade byte a byte contra os baselines congelados.

2. **Avaliação científica dos gates formais.**
   - O mecanismo `--lat-offset-slots` (deslocamento estático exclusivo do canal `obs4` por slot de grid dentro de $[-1,0, +1,0]\,\text{m}$) falhou decisivamente nos gates formais pré-registrados:
     - **Composite Interlagos:** tempo colado aumentou para 1.743 s (teto $<815\,\text{s}$) — **FAIL**; deadlocks $[1,1,1,0,6]$ (teto $\le [0,0,0,1,1]$) — **FAIL**; B-1 contatos explodiu para 2.125 (teto $\le 589$) — **FAIL**; R-1 e R-2 aprovados.
     - **Composite Monaco:** tempo colado aumentou para 3.363 s (teto $<2.005\,\text{s}$) — **FAIL**; deadlocks $[2,2,4,4,3]$ (teto $\le [1,1,1,1,1]$) — **FAIL**; B-1 contatos subiu para 2.674 (teto $\le 1.155$) — **FAIL**; R-1 e R-2 aprovados.
     - **Blind Interlagos:** tempo colado reduziu para 3.884 s ($<4.405\,\text{s}$) — PASS; deadlocks $[1,4,6,4,5]$ — PASS; porém B-1 contatos explodiu para 5.605 (teto $\le 4.202$) — **FAIL**; R-1 ritmo caiu para 231 voltas (piso $\ge 232$) — **FAIL**; R-2 fora subiu para 36.604 (teto $\le 35.345$) — **FAIL**.
     - **Blind Monaco:** tempo colado subiu para 2.714 s (teto $<2.565\,\text{s}$) — **FAIL**; deadlocks $[1,2,2,2,3]$ — PASS; B-1 contatos subiu para 4.032 (teto $\le 3.828$) — **FAIL**; R-1 e R-2 aprovados.
   - **Diagnóstico físico:** A ilusão sensorial injetada em `obs4` sem coerência com a física real e com a percepção dos outros carros quebrou a estabilidade lateral do pelotão. O resultado foi um aumento dramático de colisões mútuas em todos os perfis e pistas (B-1 falhou em 4 de 4 cenários) e nenhum benefício consistente de destravamento no perfil composite.

3. **Decisão de engenharia.**
   - **Veredito formal: FAIL (REPROVADO).**
   - O mecanismo `--lat-offset-slots` **NÃO** é homologado para produção.
   - O valor default permanece estritamente `OFF`.
   - A flag permanece apenas como instrumento de pesquisa/diagnóstico e **NÃO** é promovida para o Ciclo C7.

4. **Próximo passo autorizado.**
   - Ciclo C6 formalmente encerrado.
   - Autorizado o avanço para o **Ciclo C7 (Consolidação Final em N=5..8 — Task 15)**.
   - Escopo de C7: consolidação das únicas flags homologadas ao longo do programa REALISMO-1 (`--rejoin-handoff align` do Ciclo C2 e `--rejoin-ramp` do Ciclo C3) nas realizações $N=5..8$ deslacradas.
