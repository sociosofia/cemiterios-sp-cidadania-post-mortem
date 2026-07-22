# Valor territorial no entorno dos cemitérios

## Pergunta

Qual é o valor oficial do metro quadrado do terreno no entorno imediato de cada cemitério da cidade de São Paulo, e como esse valor se relaciona com categoria tarifária, bloco de concessão, gratuidade, renda, raça e regime de propriedade?

## Distinções necessárias

O projeto não tratará como equivalentes:

1. **PGV/IPTU** — valor unitário fiscal de metro quadrado de terreno, atribuído a faces de quadra, quadras, logradouros ou regiões;
2. **Cadastro de Valor de Terreno para Outorga Onerosa** — valor urbanístico em R$/m² usado para calcular contrapartidas pelo potencial construtivo;
3. **valor de mercado** — preço observado em transações ou anúncios imobiliários.

A PGV 2026 será o indicador principal. A Outorga Onerosa será usada como teste de robustez. Dados de mercado ficam para etapa posterior.

## Fontes oficiais

- Lei municipal 18.330/2025, especialmente o Anexo II, que estabelece a Listagem de Valores Unitários de Metro Quadrado de Terreno para 2026;
- Lei municipal 10.235/1986, arts. 2º a 5º, que define a lógica de atribuição dos valores unitários;
- GeoSampa: polígonos dos cemitérios, lotes, quadras fiscais, logradouros, faces de quadra e demais camadas necessárias ao vínculo espacial e cadastral;
- Decreto 64.884/2025 e Portaria SMUL/G 8/2026 para o Cadastro de Valor de Terreno da Outorga Onerosa.

## Unidade espacial

A análise partirá do **perímetro oficial do equipamento**, e não do centroide. Serão produzidos anéis externos que excluem a área interna do cemitério:

- 0–250 m;
- 250–500 m;
- 500–1.000 m.

Também será produzido um indicador de contato direto, baseado nas faces de quadra ou lotes que confrontam o perímetro cemiterial, quando a topologia permitir.

## Indicadores por cemitério e anel

- mediana do valor fiscal em R$/m²;
- média ponderada pela extensão da face ou área do lote, conforme a unidade da fonte;
- primeiro e terceiro quartis;
- mínimo e máximo;
- número de observações válidas;
- proporção do anel coberta por observações;
- dispersão entre os diferentes lados do cemitério.

A mediana será o indicador sintético principal. A média simples não será usada como medida central sem avaliação de cobertura e de valores extremos.

## Complexos e duplicidades

Vila Formosa I e Vila Formosa II serão apresentadas:

1. separadamente, como pontos operacionais;
2. conjuntamente, como complexo territorial;
3. em análises de sensibilidade nas médias por categoria, para impedir a dupla contagem de um mesmo contexto urbano.

O mesmo princípio será aplicado a feições duplicadas ou equipamentos contíguos identificados no GeoSampa.

## Hipóteses registradas antes do cálculo

1. A categoria 1 terá valores territoriais medianos superiores aos das categorias 2, 3 e 4.
2. A diferença entre categorias 1 e 3 será mais estável que um gradiente monotônico 1–2–3–4.
3. Vila Formosa elevará o valor mediano observado para a categoria 4 em relação a grandes cemitérios periféricos da categoria 3.
4. Os destinos de gratuidade estarão, em média, em entornos de menor valor fiscal que os demais cemitérios da rede concedida.
5. O valor territorial imediato explicará parte, mas não toda, da classificação tarifária.
6. Cemitérios particulares e associativos formarão um conjunto internamente heterogêneo, não necessariamente mais valorizado em todos os casos.

## Limites interpretativos

- Valor fiscal não é preço de mercado.
- O valor do entorno não é o valor econômico do solo interno do cemitério.
- Associação entre categoria e valor territorial não prova que a categoria tenha sido definida pelo valor da terra.
- A mudança entre PGVs não estima causalmente o efeito da concessão.
- A qualidade do resultado depende da correspondência correta entre a listagem de valores e as faces de quadra.

## Produtos previstos

- `data/raw/pgv_2026/` — fonte oficial preservada;
- `data/processed/pgv_2026_faces.csv` — listagem normalizada por face, trecho ou unidade equivalente;
- `data/processed/cemiterios_valor_territorial_2026.csv` — indicadores por cemitério e anel;
- `data/processed/categorias_valor_territorial_2026.csv` — síntese por categoria com análise de sensibilidade;
- `maps/valor_territorial_entorno_cemiterios_2026.*` — mapas reproduzíveis;
- nota metodológica com cobertura, perdas de vínculo e validação manual.

## Estatuto atual

A frente está em fase de coleta das fontes primárias e descoberta das camadas cadastrais. Nenhum valor por cemitério deve ser publicado antes da validação da correspondência entre PGV, CODLOG/face de quadra e geometrias do GeoSampa.
