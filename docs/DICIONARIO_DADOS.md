# Dicionário preliminar de dados

## Equipamentos funerários e cemiteriais

| Campo | Tipo | Descrição |
|---|---|---|
| `id_equipamento` | texto | Identificador estável criado para a pesquisa. |
| `nome_oficial` | texto | Nome usado nos documentos oficiais. |
| `nome_alternativo` | texto | Grafias ou denominações históricas. |
| `tipo` | categoria | `cemiterio`, `crematorio` ou `agencia`. |
| `endereco` | texto | Logradouro e número. |
| `bairro` | texto | Bairro informado na fonte. |
| `cep` | texto | CEP, preservando zeros à esquerda. |
| `bloco_concessao` | inteiro | Bloco contratual de 1 a 4. |
| `concessionaria` | texto | Operadora responsável. |
| `categoria_tarifaria` | inteiro | Categoria tarifária do cemitério, de 1 a 4. |
| `destino_gratuidade` | booleano | Indica destinação oficial para sepultamento gratuito. |
| `tipo_gratuidade` | texto | Sepultamento, cremação ou outra modalidade. |
| `tarifa_sepultamento` | decimal | Tarifa nominal da vigência selecionada. |
| `unidade_tarifa` | texto | Unidade de cobrança e condição de aplicação. |
| `inicio_vigencia` | data | Início da validade da tarifa. |
| `fim_vigencia` | data | Fim da validade, quando conhecido. |
| `latitude` | decimal | Latitude em WGS 84. |
| `longitude` | decimal | Longitude em WGS 84. |
| `coord_x_31983` | decimal | Coordenada E em SIRGAS 2000 / UTM 23S. |
| `coord_y_31983` | decimal | Coordenada N em SIRGAS 2000 / UTM 23S. |
| `metodo_geocodificacao` | categoria | Origem e método de obtenção da geometria. |
| `grau_confirmacao` | categoria | `documental`, `geosampa`, `endereco_conferido` ou `provisorio`. |
| `distrito` | texto | Distrito municipal obtido por operação espacial. |
| `subprefeitura` | texto | Subprefeitura obtida por operação espacial. |
| `fonte_principal` | texto | Documento ou página que sustenta o registro. |
| `observacoes` | texto | Ambiguidades, exceções e decisões metodológicas. |

## Regras

- valores monetários devem ser armazenados sem símbolo de moeda e acompanhados da vigência;
- categorias tarifárias não devem ser inferidas pela localização;
- destinos gratuitos devem ser confirmados em fonte oficial válida para o período;
- pontos de agências e polígonos de cemitérios devem permanecer em camadas distintas;
- qualquer alteração manual de coordenada deve ser registrada em `observacoes`.
