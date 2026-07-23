# Fonte Seade Mortalidade: arquitetura, API e regras de uso

## 1. Finalidade no projeto

As bases do Seade entram no projeto como medida do **fluxo demográfico dos mortos**. Elas permitem estimar quantos residentes morreram, sua distribuição territorial, temporal e etária e, em algumas séries, sexo e distrito de residência.

Elas não informam diretamente:

- onde o corpo foi sepultado ou cremado;
- qual agência, concessionária ou cemitério realizou o atendimento;
- modalidade tarifária ou gratuidade;
- exumação, reinumação, ossuário ou translado;
- tempo de permanência dos restos;
- localização residencial individual.

Portanto, óbito, evento funerário e destino cemiterial permanecem unidades distintas.

## 2. Duas famílias de dados

### 2.1. Seade Mortalidade

Série municipal anual desde 2000, preparada para o painel público. Reúne:

- óbitos em grandes faixas etárias;
- população correspondente;
- taxas específicas e taxa bruta;
- mortalidade infantil por período da morte;
- quatro grupos selecionados de causas infantis;
- esperança de vida ao nascer e aos 60 anos;
- códigos municipais e regionalizações.

É a fonte preferencial para denominadores populacionais, taxas publicadas e séries municipais comparáveis.

### 2.2. Seade Estatísticas Vitais

Séries derivadas dos registros civis, com maior granularidade:

- totais anuais por município de residência;
- mês de ocorrência;
- sexo;
- faixas etárias quinquenais;
- distrito de residência no Município de São Paulo;
- arquivos provisórios do ano corrente.

É a fonte preferencial para idade detalhada, sexo, sazonalidade e análise distrital.

## 3. API CKAN

O catálogo utiliza a Action API do CKAN. O endpoint-base empregado é:

```text
https://repositorio.seade.gov.br/api/3/action
```

A rotina usa principalmente:

```text
package_show?id=<identificador_do_conjunto>
datastore_search?resource_id=<identificador_do_recurso>&limit=0
```

`package_show` serve para descobrir recursos, URLs, datas de modificação, descrições, formatos e a indicação `datastore_active`. A tentativa de `datastore_search` é registrada no manifesto, mas a ingestão não depende do DataStore. Essa escolha evita que a reprodução falhe quando um CSV está no catálogo, mas não foi carregado para consulta linha a linha.

Cada arquivo é identificado por:

- package ID;
- resource ID;
- URL descoberta e URL de contingência;
- data UTC de acesso;
- tamanho em bytes;
- SHA-256;
- codificação e delimitador detectados;
- cabeçalhos e número de linhas;
- cobertura temporal inferida do conteúdo.

### 3.1. Limite operacional da automação

O recurso principal informa `datastore_active: false`. Logo, a Action API funciona como catálogo, mas não oferece consulta linha a linha para a base central. Em testes realizados em 22 de julho de 2026, o Cloudflare do domínio `repositorio.seade.gov.br` respondeu HTTP 403 tanto aos arquivos `/download/` quanto às chamadas da Action API originadas de runners hospedados pelo GitHub.

A coleta real, portanto, deve ser executada em ambiente local ou institucional que tenha acesso ao portal:

```bash
python scripts/fetch_seade_mortalidade.py
```

Quando os CSVs já tiverem sido baixados e auditados, a reprodução integral pode ser feita sem rede:

```bash
python scripts/fetch_seade_mortalidade.py \
  --offline-dir /caminho/para/os/csvs \
  --root .
```

O workflow `validar-seade-mortalidade.yml` não simula atualização remota. Ele compila o código e executa toda a transformação sobre uma fixture sintética internamente coerente. Isso testa parsing, reconciliações, relatórios e produtos, mas não substitui a auditoria de uma nova versão dos arquivos oficiais.

Essa separação é deliberada: é preferível declarar uma barreira externa a publicar como “automática” uma coleta que depende de contornar mecanismos de proteção do portal ou de proxies não auditados.

## 4. Arquivos anuais e arquivos correntes

Arquivos anuais consolidados são preservados em:

```text
data/raw/seade/mortalidade/annual/
```

Arquivos chamados `anoatual` mudam mensalmente. Para evitar crescimento excessivo do histórico Git, seus bytes não são versionados; o manifesto guarda hash e metadados, e os totais mensais presentes são agregados em:

```text
data/processed/seade_mortalidade_corrente_mes.csv
```

A presença de doze meses não basta para converter automaticamente um arquivo corrente em série consolidada. Registros tardios podem revisar os totais.

## 5. Regras de leitura numérica

Os arquivos não seguem um único padrão de codificação ou notação numérica. A rotina:

1. tenta UTF-8 com e sem BOM, Windows-1252 e Latin-1;
2. detecta delimitador entre ponto e vírgula, vírgula, barra vertical e tabulação;
3. interpreta vírgula como separador decimal;
4. interpreta padrões como `1.708` como separador de milhar quando o campo é inteiro;
5. conserva códigos territoriais como texto;
6. normaliza apenas rótulos conhecidos de idade ignorada, preservando o valor original no relatório de qualidade.

Essa regra é necessária porque a série distrital contém ao menos um total grafado com ponto de milhar em meio a valores sem separador.

## 6. Validações obrigatórias

### 6.1. Mortalidade geral

- unicidade de `cod_ibge × ano`;
- soma das faixas etárias igual ao total;
- soma das populações etárias igual à população total;
- recálculo das taxas com tolerância compatível com arredondamento a uma casa decimal;
- cobertura dos códigos na tabela de municípios e regiões;
- separação do código `3500000`, sem especificação de município.

### 6.2. Mortalidade infantil

- soma de menos de 7 dias, 7 a 27 dias e 28 a 364 dias igual ao total de menores de um ano;
- igualdade dos nascidos vivos entre os dois arquivos infantis;
- alerta quando a soma dos quatro grupos selecionados de causas supera o total infantil.

Os quatro grupos não devem ser tratados como partição exaustiva das causas sem confirmação metodológica.

### 6.3. Reconciliação entre séries

- `Mortalidade geral` versus `Estatísticas Vitais` por município-ano;
- soma dos meses versus total anual;
- soma de sexo e idade versus total anual;
- soma dos 97 códigos distritais versus Município de São Paulo;
- soma mensal e soma sexo/idade versus total de cada distrito.

Pequenas diferenças são preservadas, não corrigidas silenciosamente.

## 7. Produtos analíticos

### Painel município-ano

```text
data/processed/seade_mortalidade_municipio_ano.csv
```

Integra óbitos, população, taxa bruta, mortalidade infantil e regionalizações. A linha `3500000` permanece identificada como sem especificação municipal.

### Painel Estado-ano

```text
data/processed/seade_mortalidade_estado_ano.csv
```

Contém totais, estrutura etária, taxa recalculada, mortos por dia, total da capital e acumulado desde 2000.

### Painel distrito-ano

```text
data/processed/seade_mortalidade_distrito_sp_ano.csv
```

Contém os 96 distritos e o código adicional de residência sem especificação. Refere-se ao distrito de residência, não ao distrito de ocorrência ou ao cemitério de destino.

## 8. Hierarquia de uso

1. **Taxas e população municipal:** Seade Mortalidade.
2. **Total anual:** apresentar a fonte escolhida e informar divergências na reconciliação.
3. **Sexo e idade quinquenal:** Estatísticas Vitais.
4. **Mês de ocorrência:** Estatísticas Vitais.
5. **Distrito de residência na capital:** Estatísticas Vitais do Município de São Paulo.
6. **Causa básica, raça/cor, escolaridade e local de ocorrência:** SIM/PRO-AIM, com denominadores adequados.
7. **Sepultamento, cremação, gratuidade e destino:** registros funerários administrativos.

## 9. Limites de inferência

A mortalidade por residência pode ser relacionada a tarifas e infraestrutura apenas como aproximação da demanda social potencial. Não autoriza afirmar que:

- residentes de um distrito foram enterrados no cemitério mais próximo;
- a distribuição dos óbitos reproduz a distribuição dos sepultamentos;
- o aumento de mortes produziu automaticamente igual aumento de ocupação cemiterial;
- tarifa ou concessão causou determinada mortalidade;
- taxa bruta maior significa pior condição de saúde sem controle da estrutura etária.

Comparações territoriais devem preferir taxas específicas ou padronizadas. Municípios pequenos devem ser analisados com médias plurianuais e intervalos de incerteza.

## 10. Integrações prioritárias

A contribuição analítica mais forte surgirá da associação entre:

```text
município/distrito de residência
        × fluxo anual de óbitos
        × estrutura etária
        × vulnerabilidade social
        × tarifa e gratuidade
        × capacidade funerária
        × regime de permanência
```

Essa associação permite medir pressão demográfica, cobertura institucional e custo social, mas não substitui a futura matriz:

```text
residência → modalidade de atendimento → destino funerário → permanência
```

A matriz depende de dados administrativos anonimizados ou agregados obtidos por transparência pública.
