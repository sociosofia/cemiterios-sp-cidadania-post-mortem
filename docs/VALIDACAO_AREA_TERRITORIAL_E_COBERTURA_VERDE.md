# Validação da área territorial e da alegação de cobertura verde

## Pergunta de pesquisa

Qual é a extensão territorial atual dos cemitérios públicos concedidos de São Paulo e em que medida essa grandeza valida as formulações históricas de que as necrópoles municipais somavam aproximadamente 3,3 ou 3,6 milhões de metros quadrados e constituíam a segunda maior área verde da cidade?

## Resultado principal

A soma das áreas dos 23 polígonos operacionais atualmente associados à concessão — 22 cemitérios e o Crematório Vila Alpina — é de **2.959.916,850 m²**, equivalentes a **295,992 hectares**.

Excluindo o crematório, os 22 cemitérios somam **2.906.401,133 m²**.

Esses valores foram calculados a partir dos polígonos oficiais da camada `geoportal:equipamento_cemiterio` do GeoSampa, projetados em SIRGAS 2000 / UTM 23S (`EPSG:31983`) e dissolvidos por equipamento. A rotina de origem está em `scripts/build_cemiterios_concessao.py`, e a validação agregada está em `scripts/validate_cemetery_environmental_footprint.py`.

## Totais por bloco da concessão

| Bloco | Operador | Área territorial | Participação no total |
|---:|---|---:|---:|
| 1 | Consolare | 1.082.171,611 m² | 36,56% |
| 2 | Cortel SP | 809.764,850 m² | 27,36% |
| 3 | Grupo Maya | 412.642,357 m² | 13,94% |
| 4 | Velar SP | 655.338,032 m² | 22,14% |
| **Total** | — | **2.959.916,850 m²** | **100%** |

O bloco 4 inclui o Crematório Vila Alpina, com 53.515,717 m².

## Maiores equipamentos

| Equipamento | Área territorial |
|---|---:|
| Vila Formosa I | 373.387,695 m² |
| Vila Formosa II | 300.363,480 m² |
| São Luiz | 235.332,920 m² |
| Vila Nova Cachoeirinha | 231.460,667 m² |
| Dom Bosco | 224.577,305 m² |
| São Pedro | 223.941,397 m² |
| Araçá | 221.429,873 m² |

Vila Formosa I e II somam **673.751,175 m²** na base atual.

## Comparação com as cifras históricas

### Informação oficial de 2014–2015

Notícias oficiais da Prefeitura publicadas nas operações de Finados de 2014 e 2015 afirmaram que as 22 necrópoles municipais somavam **3.278.272 m²** e constituíam o segundo maior volume de área arborizada da capital.

A diferença entre essa cifra e a soma atual dos 23 equipamentos é de **318.355,150 m²**, ou **9,711%** da referência histórica.

A própria informação de 2015 atribuía ao Vila Formosa 763.175 m². A soma atual dos dois polígonos de Vila Formosa é 673.751,175 m², diferença de 89.423,825 m². Parte da divergência agregada pode decorrer de mudanças de delimitação, critérios de mensuração, incorporação de áreas contíguas ou estimativas administrativas antigas.

### Estimativa de 3,6 milhões de m²

A cifra aproximada de **3,6 milhões de m²**, utilizada na tese e em memórias institucionais, não é confirmada pela base geográfica atual. A diferença é de **640.083,150 m²**, equivalente a **17,780%** da estimativa.

Até que sua fonte primária seja localizada, essa cifra deve ser apresentada como estimativa histórica ou memória institucional, não como medida territorial validada.

## O que esta validação não demonstra

A análise atual mede **área territorial do equipamento**, não área verde em sentido ambiental.

Quatro grandezas precisam permanecer separadas:

1. **área territorial cemiterial:** extensão integral do polígono do equipamento;
2. **área livre ou permeável:** parcela não edificada ou impermeabilizada;
3. **cobertura vegetal:** superfície ocupada por vegetação;
4. **cobertura arbórea:** projeção horizontal das copas das árvores.

Um cemitério pode possuir grande área territorial e baixa cobertura arbórea. Também pode conter vegetação, vias internas, edifícios, quadras tumulares impermeabilizadas, terrenos vazios e áreas operacionais. Portanto, a expressão “segunda maior área verde” não pode ser validada apenas pela soma dos perímetros.

A formulação histórica “segundo maior volume de área arborizada” deve ser tratada, nesta etapa, como uma **afirmação institucional oficial**, não como resultado ambiental reproduzido pelo repositório.

## Próxima validação ambiental

Para testar a dimensão ambiental propriamente dita, o projeto deverá:

1. localizar uma camada municipal de cobertura vegetal, copas arbóreas, vegetação significativa, impermeabilização ou uso do solo;
2. padronizar a camada para `EPSG:31983`;
3. intersectá-la com os polígonos dos 23 equipamentos;
4. calcular, por cemitério e por bloco:
   - metros quadrados de cobertura vegetal;
   - percentual do perímetro coberto por vegetação;
   - cobertura arbórea, quando disponível;
   - área permeável;
   - fragmentação e continuidade da vegetação;
5. comparar o conjunto cemiterial com parques e demais áreas administradas pela Secretaria Municipal do Verde e do Meio Ambiente usando a mesma definição e a mesma fonte cartográfica.

Sem essa comparação homogênea, não é possível validar cientificamente a posição dos cemitérios como “segunda maior área verde” da cidade.

## Consequência analítica para o Artigo Holanda

A documentação confirma que o discurso ambiental possuía base territorial expressiva: os equipamentos ocupam quase 296 hectares. Contudo, o argumento da “devolução dos cemitérios à cidade” não deve confundir extensão fundiária com qualidade ambiental.

O ponto sociologicamente mais forte é acompanhar a transformação do estatuto dessas áreas:

> a autarquia mobilizava a grande extensão e a arborização dos cemitérios como fundamento de uma missão pública de abertura, cultura e ocupação cidadã; a concessão preserva a dimensão ambiental, mas a decompõe em obrigações contratuais, indicadores, compensações, manejo e repartição de riscos.

A validação quantitativa deve, portanto, sustentar — e não substituir — a análise da disputa institucional sobre quem define, administra e usufrui a função ambiental dos cemitérios.

## Fontes documentais externas

- Prefeitura de São Paulo. **Operação Finados 2014**. Informação oficial de 3.278.272 m².
- Prefeitura de São Paulo. **Operação Finados 2015**. Informação oficial de 3.278.272 m², referência ao Vila Formosa e à segunda maior área arborizada.
- Prefeitura de São Paulo. **Concessão dos Serviços Funerários — perguntas e respostas**. Reconhecimento dos cemitérios como integrantes do sistema municipal de áreas verdes e previsão de compensação verde.

## Arquivos reproduzíveis

- `data/reference/geosampa_mapping.csv`
- `data/processed/cemiterios_concessao_31983.geojson`
- `data/processed/cemiterios_concessao_centroides.csv`
- `data/processed/resumo_area_territorial_cemiterios.json`
- `scripts/build_cemiterios_concessao.py`
- `scripts/validate_cemetery_environmental_footprint.py`
