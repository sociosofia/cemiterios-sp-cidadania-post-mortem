# Cemitérios de São Paulo — cidadania post mortem

Dados, mapas e rotinas reproduzíveis para analisar tarifas, gratuidade, permanência e desigualdade socioespacial nos cemitérios públicos concedidos do Município de São Paulo.

![Mapa dos estratos tarifários e destinos gratuitos](maps/mapa_estratos_gratuidade.png)

## Primeiro resultado cartográfico

A base reúne **23 pontos operacionais**: 22 cemitérios considerados separadamente — incluindo Vila Formosa I e Vila Formosa II — e o Crematório Vila Alpina. A documentação da licitação agrupa Vila Formosa I e II em uma mesma unidade de memorial, razão pela qual diferentes documentos podem apresentar contagens distintas.

O mapa utiliza:

- polígonos oficiais da camada `geoportal:equipamento_cemiterio` do GeoSampa;
- limites dos 96 distritos municipais;
- classificação tarifária dos cemitérios em quatro estratos;
- indicação específica dos destinos da gratuidade por hipossuficiência;
- SIRGAS 2000 / UTM zona 23S (`EPSG:31983`) para cálculos espaciais;
- WGS 84 (`EPSG:4326`) para o mapa web.

Os marcadores estão posicionados nos **centroides geométricos** dos polígonos e não representam portões ou entradas. Os pontos de acesso público serão construídos como uma camada separada.

## Centro e periferia

Tomando o centroide geométrico do distrito Sé como referência analítica:

| Estrato tarifário | Média de distância | Mediana |
|---:|---:|---:|
| 1 | 5,0 km | 4,6 km |
| 2 | 10,1 km | 9,6 km |
| 3 | 20,7 km | 20,3 km |
| 4 | 13,0 km | 11,0 km |

Os cinco destinos ordinários de sepultamento gratuito por hipossuficiência pertencem aos estratos 3 ou 4. Eles apresentam distância média de **15,9 km** e mediana de **17,2 km** em relação à referência central. Nos demais cemitérios, a média é **10,9 km** e a mediana, **8,6 km**.

## Contexto socioeconômico dos territórios

Cada equipamento foi associado ao distrito que contém a maior parcela de sua área. Os indicadores vêm dos agregados distritais do Censo 2022.

| Grupo | Equipamentos | Renda mediana distrital — média entre equipamentos | Mediana das rendas distritais | Proporção preta+parda média |
|---|---:|---:|---:|---:|
| Destinos gratuitos | 5 | R$ 2.560 | R$ 2.000 | 41,8% |
| Demais cemitérios | 17 | R$ 4.818 | R$ 3.800 | 31,7% |

Por estrato tarifário:

| Estrato | Cemitérios | Renda mediana distrital média | Proporção preta+parda média |
|---:|---:|---:|
| 1 | 6 | R$ 7.733 | 17,5% |
| 2 | 7 | R$ 4.072 | 30,2% |
| 3 | 6 | R$ 1.800 | 54,5% |
| 4 | 3 | R$ 3.000 | 34,7% |

Os resultados são descritivos e se referem à **localização do cemitério**, não ao perfil individual dos mortos ou de suas famílias. A tabela completa está em [`docs/RESULTADOS_SOCIOECONOMICOS.md`](docs/RESULTADOS_SOCIOECONOMICOS.md).

## Fluxo demográfico dos mortos

A integração das bases Seade Mortalidade e Seade Estatísticas Vitais produz painéis municipais, estaduais e distritais por residência. Na série consolidada de 2000 a 2024:

- o Estado de São Paulo registrou **7.070.549 óbitos** de residentes;
- 2024 teve **351.354 óbitos**, aproximadamente 960 por dia;
- 74,7% das mortes de 2024 ocorreram entre pessoas de 60 anos ou mais;
- o Município de São Paulo registrou **87.352 óbitos** em 2024;
- o pico foi 2021, com **429.481 óbitos**.

Esses números representam fluxo de óbitos por residência. Não equivalem a sepultamentos, cremações, ocupação de jazigos nem destino cemiterial. A auditoria, as inconsistências encontradas e as regras de uso estão em [`docs/RESULTADOS_SEADE_MORTALIDADE.md`](docs/RESULTADOS_SEADE_MORTALIDADE.md) e [`docs/FONTE_SEADE_MORTALIDADE.md`](docs/FONTE_SEADE_MORTALIDADE.md).

## Desigualdade temporal do direito ao sepulcro

O Decreto Municipal nº 59.196/2020 distingue:

- gaveta comum de três anos, renovável mediante pagamento;
- gaveta social por hipossuficiência de três anos, **não renovável e não transmissível**;
- terreno comum de prazo indeterminado, sujeito às regras de manutenção, sucessão e extinção.

Depois do fim da cessão fixa, a administração pode realizar a exumação se o interessado não a requerer em 30 dias. Restos não requisitados podem ser levados ao ossuário geral e, após os procedimentos legais, incinerados. A reconstrução do fluxo e suas ressalvas está em [`docs/TEMPORARIEDADE_E_OSSADAS.md`](docs/TEMPORARIEDADE_E_OSSADAS.md).

## Eixo analítico: cidadania post mortem

O projeto investiga cinco dimensões mensuráveis:

1. **acesso econômico:** quanto custa conseguir sepultar alguém;
2. **localização:** onde os diferentes regimes tarifários e destinos gratuitos estão situados;
3. **acessibilidade:** quanto a família precisa se deslocar e quais meios de transporte possui;
4. **permanência:** por quanto tempo o morto permanece identificado e localizado;
5. **memória:** quais condições materiais existem para registro, visita e continuidade dos vínculos.

O plano analítico e seus limites de inferência estão em [`docs/PLANO_ANALISE_SOCIOESPACIAL.md`](docs/PLANO_ANALISE_SOCIOESPACIAL.md).

## Arquivos principais

### Inventários e dados processados

- [`data/reference/cemiterios_crematorio.csv`](data/reference/cemiterios_crematorio.csv) — endereços, blocos, concessionárias, estratos, gratuidade e tarifa avulsa de sepultamento;
- [`data/reference/agencias_funerarias.csv`](data/reference/agencias_funerarias.csv) — 40 agências funerárias;
- [`data/reference/geosampa_mapping.csv`](data/reference/geosampa_mapping.csv) — associação auditável entre equipamentos e GeoSampa;
- [`data/processed/cemiterios_concessao_31983.geojson`](data/processed/cemiterios_concessao_31983.geojson) — polígonos para análise métrica;
- [`data/processed/cemiterios_concessao_4326.geojson`](data/processed/cemiterios_concessao_4326.geojson) — polígonos para mapas web;
- [`data/processed/cemiterios_contexto_socioeconomico.csv`](data/processed/cemiterios_contexto_socioeconomico.csv) — renda e composição racial do distrito de localização;
- [`data/processed/resumo_estratos_renda_raca.json`](data/processed/resumo_estratos_renda_raca.json) — resultados agregados;
- [`data/processed/distancias_centroide_se.csv`](data/processed/distancias_centroide_se.csv) — indicador preliminar de centralidade.

### Rotinas e documentação da mortalidade

- [`scripts/fetch_seade_mortalidade.py`](scripts/fetch_seade_mortalidade.py) — coleta, integração, validação e geração dos painéis Seade;
- [`tests/test_seade_mortalidade.py`](tests/test_seade_mortalidade.py) — teste integral offline com fixture coerente;
- [`docs/RESULTADOS_SEADE_MORTALIDADE.md`](docs/RESULTADOS_SEADE_MORTALIDADE.md) — resultados auditados e inconsistências encontradas;
- [`docs/FONTE_SEADE_MORTALIDADE.md`](docs/FONTE_SEADE_MORTALIDADE.md) — arquitetura das fontes, API, limites e regras de uso.

A execução bem-sucedida da rotina gera, sem que esses snapshots estejam ainda incorporados ao branch:

- `data/processed/seade_mortalidade_municipio_ano.csv`;
- `data/processed/seade_mortalidade_estado_ano.csv`;
- `data/processed/seade_mortalidade_distrito_sp_ano.csv`;
- `data/processed/seade_mortalidade_corrente_mes.csv`;
- `data/raw/seade/mortalidade/manifest.json` e `quality_report.json`.

### Mapas

- [`maps/mapa_estratos_gratuidade.png`](maps/mapa_estratos_gratuidade.png) — mapa estático;
- [`maps/mapa_estratos_gratuidade.svg`](maps/mapa_estratos_gratuidade.svg) — versão vetorial;
- [`maps/cemiterios_concessao_interativo.html`](maps/cemiterios_concessao_interativo.html) — mapa interativo.

## Cuidado interpretativo

A tarifa indicada no inventário é a tarifa **avulsa de sepultamento ou inumação por categoria**, na referência de janeiro de 2026. Ela não deve ser somada automaticamente a todos os pacotes funerários.

A gratuidade não é uma categoria tarifária. O campo correspondente identifica os destinos disponibilizados para sepultamentos gratuitos por hipossuficiência; doadores de órgãos possuem regra específica.

O perfil socioeconômico do território onde está um cemitério não equivale ao perfil individual das pessoas enterradas nele. Para testar a distribuição social efetiva dos mortos, serão necessários registros administrativos anonimizados de origem, modalidade de atendimento e destino.

## Automação

O workflow territorial continua responsável por GeoSampa, Censo 2022, IPVS, documentos e mapas. A mortalidade possui validação separada: o GitHub compila a rotina e reproduz todas as transformações sobre uma fixture offline. A extração real dos CSVs precisa ser executada localmente, porque o recurso principal não está ativo no DataStore e o Cloudflare do portal bloqueia runners hospedados pelo GitHub. O procedimento e os comandos estão documentados em [`docs/FONTE_SEADE_MORTALIDADE.md`](docs/FONTE_SEADE_MORTALIDADE.md).

## Próximas etapas

- incorporar snapshots versionados dos painéis após definir política de atualização e reutilização;
- cruzar fluxo de óbitos, tarifas, gratuidade e capacidade funerária;
- localizar e validar os portões de acesso público;
- medir distâncias e tempos de deslocamento pela rede;
- obter atas e propostas dos grupos de trabalho sobre ossadas;
- localizar relatórios de estoque de ossadas por cemitério;
- buscar registros anonimizados de origem e destino dos sepultamentos.

As pendências documentais estão em [`docs/PENDENCIAS_DOCUMENTAIS.md`](docs/PENDENCIAS_DOCUMENTAIS.md).

## Fontes principais

- Prefeitura de São Paulo — edital, contratos, anexos e legislação;
- SP Regula — endereços, concessionárias, agências, gratuidades e tarifas;
- GeoSampa — camadas geográficas municipais, sob licença CC BY-SA 4.0;
- Fundação Seade — Mortalidade, Estatísticas Vitais, regionalizações e IPVS;
- IBGE — Censo Demográfico 2022.

A metodologia completa está em [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).
