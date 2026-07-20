# Metodologia de construção da base geográfica

## Escopo

A base reunirá cemitérios públicos municipais, crematórios e agências funerárias vinculados à concessão dos serviços funerários e cemiteriais da cidade de São Paulo.

## Unidade de registro

Cada linha representará um equipamento físico ou uma unidade operacional. Vila Formosa I e Vila Formosa II permanecerão como registros distintos quando os documentos contratuais ou espaciais permitirem distingui-los.

## Etapas

1. Inventariar os equipamentos e endereços nos documentos da licitação e nas páginas oficiais da SP Regula.
2. Registrar bloco contratual, concessionária e categoria tarifária.
3. Identificar os equipamentos destinados à gratuidade e a natureza do serviço gratuito.
4. Geocodificar os endereços de forma preliminar.
5. Conferir cada localização com os documentos oficiais, ortofotos e camadas do GeoSampa.
6. Registrar distrito, subprefeitura e demais recortes territoriais por operação espacial.
7. Comparar tarifas apenas dentro de vigências e unidades de cobrança equivalentes.
8. Produzir arquivos derivados em CSV, GeoJSON e GeoPackage.

## Sistemas de referência

- EPSG:31983 — SIRGAS 2000 / UTM zona 23S, para análise métrica municipal;
- EPSG:4326 — WGS 84, para interoperabilidade e mapas web.

## Controle de qualidade

Cada coordenada receberá um campo de método e um grau de confirmação:

- `documental`: coordenada ou perímetro presente em documento oficial;
- `geosampa`: posição conferida em camada ou ortofoto municipal;
- `endereco_conferido`: geocodificação compatível com o endereço e inspecionada visualmente;
- `provisorio`: localização ainda não conferida.

Nenhum endereço ou ponto será considerado definitivo apenas porque um serviço automático de geocodificação retornou um resultado.

## Princípios de publicação

O repositório contém somente dados públicos, referências, rotinas técnicas e resultados reproduzíveis. Rascunhos autorais, entrevistas, memórias pessoais e notas privadas de pesquisa não devem ser publicados.
