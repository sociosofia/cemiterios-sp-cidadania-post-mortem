# Auditoria e integração das bases de mortalidade do Seade

**Data da extração auditada:** 22 de julho de 2026

## Escopo

A rotina integra duas famílias que não devem ser confundidas:

1. **Seade Mortalidade:** painel municipal anual com óbitos, população, taxas, mortalidade infantil e esperança de vida;
2. **Seade Estatísticas Vitais:** séries mais granulares por mês, sexo, idade quinquenal e, na capital, distrito de residência.

A API CKAN é usada para descobrir e auditar os recursos. Como o recurso principal não está ativo no DataStore, os CSVs oficiais foram baixados, validados e identificados por SHA-256 em ambiente com acesso ao portal.

## Resultados calculados

- Entre 2000 e 2024, a série registra **7.070.549 óbitos** de residentes no Estado de São Paulo.
- Em 2024, foram **351.354 óbitos**, ou **960,0 por dia**.
- Pessoas de 60 anos ou mais responderam por **74,7%** dos óbitos em 2024, ante **55,8%** em 2000.
- O maior total da série ocorreu em **2021**, com **429.481 óbitos**.
- O Município de São Paulo registrou **87.352 óbitos** em 2024.

Esses números medem óbitos por residência. Não equivalem a sepultamentos, cremações, ocupação de jazigos nem destino cemiterial.

## Cobertura provisória dos arquivos correntes

- Estado de São Paulo, 2025: **355.169 óbitos** nos meses presentes de janeiro a dezembro.
- Estado de São Paulo, 2026: **104.313 óbitos** de janeiro a abril.
- Município de São Paulo, 2025: **88.213 óbitos** nos meses presentes de janeiro a dezembro.
- Município de São Paulo, 2026: **17.197 óbitos** de janeiro a março.

Os arquivos correntes são incompletos e sujeitos a registros tardios. O nome `anoatual` pode conter também o ano anterior; a cobertura é inferida do conteúdo, não do nome do arquivo.

## Controle de qualidade

- Diferenças entre as duas séries anuais oficiais: **7 células**, diferença absoluta máxima de **10 óbitos**.
- Divergências entre soma mensal e total anual estadual: **2**.
- Divergências entre sexo/idade e total anual estadual: **1**.
- Divergências entre sexo/idade distrital e total anual do distrito: **1**.
- Casos em que a soma dos quatro grupos de causas infantis supera o total de óbitos infantis: **1**.
- A soma dos 97 códigos distritais reconcilia com o total municipal em todos os anos após interpretar corretamente separadores de milhar: **sim**.

### Inconsistências que exigem cautela

- descrições das páginas podem indicar término em 2023 enquanto o CSV já contém 2024;
- nomes de categorias de idade ignorada variam dentro do mesmo arquivo;
- há grafias incorretas nos cabeçalhos oficiais;
- pontos podem representar separadores de milhar, não casas decimais;
- séries anuais, mensais e por sexo/idade podem refletir revisões registrárias em momentos diferentes.

## Regra de uso no projeto

- usar `mortalidade_geral.csv` para população, grandes faixas etárias e taxas;
- usar Estatísticas Vitais para sexo, idade quinquenal, mês e distrito;
- publicar reconciliação entre fontes sempre que totais forem combinados;
- separar residência, ocorrência e destino funerário;
- nunca tratar arquivos correntes como anos completos;
- preferir taxas específicas ou padronizadas nas comparações territoriais.

## Produtos gerados pela rotina

- `data/processed/seade_mortalidade_municipio_ano.csv`;
- `data/processed/seade_mortalidade_estado_ano.csv`;
- `data/processed/seade_mortalidade_distrito_sp_ano.csv`;
- `data/processed/seade_mortalidade_corrente_mes.csv`;
- `data/raw/seade/mortalidade/manifest.json`;
- `data/raw/seade/mortalidade/quality_report.json`.

Os produtos tabulares são recriados pela rotina e ainda não foram incorporados ao branch como snapshots permanentes. As conclusões acima são **calculadas** e **descritivas**. Relações com tarifas, gratuidade, concessão e permanência post mortem exigem integração posterior com dados funerários administrativos.
