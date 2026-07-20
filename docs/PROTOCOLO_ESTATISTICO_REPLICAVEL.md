# Protocolo estatístico e cartográfico replicável

## Cidadania post mortem e desigualdade necroterritorial em São Paulo

**Versão:** 1.0  
**Unidade espacial de referência:** Município de São Paulo  
**Sistema de coordenadas analítico:** SIRGAS 2000 / UTM zona 23S - EPSG:31983  
**Sistema de coordenadas para publicação web:** WGS 84 - EPSG:4326

---

## 1. Finalidade do protocolo

Este documento fixa, antes das etapas confirmatórias, as regras de coleta, transformação, análise e interpretação dos dados. Seus objetivos são:

1. permitir a repetição integral das análises por terceiros;
2. impedir mudanças oportunistas de indicadores após a observação dos resultados;
3. distinguir evidência documental, descrição estatística, associação espacial e inferência causal;
4. registrar limitações, escolhas e resultados negativos;
5. oferecer respostas verificáveis a objeções metodológicas.

O repositório deve preservar dados brutos permitidos, scripts, versões processadas, dicionários, relatórios de qualidade e mapas derivados.

---

## 2. Pergunta geral

Como a organização territorial, tarifária e temporal dos serviços funerários e cemiteriais paulistanos distribui de maneira desigual o acesso ao sepultamento, a localização dos mortos, a permanência dos restos, a possibilidade de visita e a continuidade da memória?

### 2.1. Hipóteses principais

**H1 - Gradiente tarifário-territorial.** Cemitérios de categorias tarifárias superiores tendem a localizar-se em áreas mais centrais e de maior renda.

**H2 - Periferização da gratuidade.** Os destinos ordinários da gratuidade por hipossuficiência tendem a estar mais distantes da centralidade urbana e em territórios socialmente mais vulneráveis.

**H3 - Estratificação racial territorial.** Cemitérios de categorias inferiores e destinos gratuitos tendem a estar em distritos ou entornos com maior proporção de população preta e parda.

**H4 - Desigualdade temporal.** Modalidades associadas à hipossuficiência oferecem menor estabilidade espacial e menor capacidade de renovação que cessões pagas e por prazo indeterminado.

**H5 - Deslocamento desigual dos corpos.** Pessoas residentes em territórios mais vulneráveis percorrem, em média, maiores distâncias entre residência e cemitério de destino, especialmente nos sepultamentos gratuitos.

**H6 - Mecanismo necroimobiliário.** Diferenças de preço, disponibilidade, renovação, manutenção e recuperação de espaços convertem localização e permanência funerária em recursos economicamente diferenciados.

H5 depende de registros de origem e destino ainda não obtidos. H6 será tratada como hipótese até haver evidência de estoque, escassez, reconcessão, valorização ou circulação econômica de direitos funerários.

---

## 3. Conceitos operacionais

### 3.1. Cidadania post mortem

Conjunto de direitos e capacidades materiais relacionados a:

- acesso econômico a funeral e sepultamento;
- identificação e registro do morto;
- localização espacial dos restos;
- possibilidade de visita e elaboração do luto;
- permanência no espaço cemiterial;
- transmissão ou renovação de direitos funerários;
- conservação da memória individual, familiar e coletiva;
- tratamento digno em exumações, ossuários, cremações e translados.

### 3.2. Estratificação necroterritorial

Distribuição regulada de equipamentos, tarifas, formas de cessão e regimes de permanência no território urbano. É uma conclusão descritiva quando demonstrada por documentos e dados espaciais.

### 3.3. Estratificação necroimobiliária

Hierarquização econômica dos direitos de uso do espaço funerário segundo localização, categoria, duração, manutenção e possibilidade de renovação ou transmissão.

### 3.4. Especulação necroimobiliária

Hipótese mais exigente. Requer evidência de pelo menos um mecanismo de valorização ou exploração de escassez, como:

- restrição ou administração diferenciada da oferta;
- valorização real sistemática de cessões;
- recuperação e nova comercialização de espaços;
- mercado secundário ou intermediação;
- conversão da permanência em receita por manutenção ou renovação;
- relação demonstrável entre prestígio territorial e preço.

Tarifas diferentes, isoladamente, não provam especulação.

---

## 4. Unidades de análise

As unidades abaixo não podem ser confundidas.

### 4.1. Equipamento funerário ou cemiterial

Cemitério, crematório ou agência funerária. Permite analisar localização, categoria, lote, concessionária, tarifa, área e regime de gratuidade.

### 4.2. Território onde o equipamento está localizado

Distrito, subprefeitura, setor censitário ou buffer no entorno. Descreve o contexto do equipamento, não o perfil das pessoas sepultadas.

### 4.3. Pessoa falecida ou óbito

Unidade dos dados do SIM/PRO-AIM. Permite estudar residência, raça/cor, idade, escolaridade, sexo, causa e local de ocorrência.

### 4.4. Evento funerário

Contratação, remoção, funeral, sepultamento, cremação, exumação, reinumação, translado ou destinação a ossuário.

### 4.5. Coorte de sepultamento

Conjunto de sepultamentos ocorridos em determinado mês ou ano. É essencial para relacionar sepultamentos temporários e exumações posteriores.

### 4.6. Fluxo residência-destino

Ligação entre território de residência, modalidade tarifária, cemitério de destino e regime de permanência. É a unidade necessária para testar deslocamento desigual dos corpos.

---

## 5. Fontes e hierarquia de evidência

### 5.1. Fontes normativas e contratuais

- edital, contratos e anexos da concessão;
- política tarifária;
- legislação municipal cemiterial;
- decisões judiciais e atos regulatórios.

Servem para provar regras, categorias, obrigações e valores oficiais.

### 5.2. Fontes espaciais

- GeoSampa: cemitérios, distritos, subprefeituras, setores e demais camadas municipais;
- Fundação Seade: IPVS 2022;
- IBGE: Censo 2022 e malhas territoriais;
- OpenStreetMap/Nominatim: geocodificação inicial das agências, sempre sujeita a validação.

### 5.3. Fontes de mortalidade

- SIM/PRO-AIM da Secretaria Municipal da Saúde;
- TabNet municipal;
- bases de mortalidade por residência e ocorrência.

### 5.4. Fontes administrativas futuras

- SP Regula;
- concessionárias;
- cadastro do antigo SFMSP;
- processos do TCM;
- respostas e-SIC/LAI.

### 5.5. Imprensa, entrevistas e memória institucional

São usadas para localizar controvérsias, experiências e hipóteses. Não substituem documentos administrativos nem dados estatísticos.

---

## 6. Inventário dos equipamentos

Cada registro deve conter:

- identificador estável;
- nome oficial e nomes alternativos;
- tipo de equipamento;
- endereço oficial e CEP;
- bloco/lote e concessionária;
- categoria tarifária;
- destino da gratuidade;
- tarifa e data de referência;
- fonte de cada atributo;
- geometria e método de obtenção;
- grau de confiança;
- observações e pendências.

Vila Formosa I e Vila Formosa II são tratadas separadamente como pontos operacionais, mesmo quando documentos contratuais as agrupam em uma unidade.

---

## 7. Georreferenciamento

### 7.1. Cemitérios

1. consultar a camada oficial `geoportal:equipamento_cemiterio` do WFS do GeoSampa;
2. preservar a resposta bruta;
3. associar feições aos equipamentos mediante nome, endereço e inspeção;
4. dissolver feições múltiplas pertencentes ao mesmo equipamento;
5. calcular área, perímetro e centroide em EPSG:31983;
6. conservar o polígono como unidade principal;
7. usar centroide apenas para rótulo ou representação pontual;
8. criar, em etapa separada, pontos de entrada pública.

### 7.2. Agências funerárias

1. normalizar endereço e bairro publicados pela SP Regula;
2. geocodificar com consulta restrita ao Município de São Paulo;
3. preservar consulta e resposta bruta;
4. rejeitar coordenadas fora do limite municipal;
5. classificar qualidade:
   - 3: número ou edificação confirmado;
   - 2: estabelecimento/localidade plausível, revisão recomendada;
   - 1: nível de logradouro, provisório;
   - 0: não localizado;
6. validar níveis 1 e 2 no GeoSampa e em ortofoto;
7. nunca apresentar ponto de logradouro como acesso exato.

### 7.3. Projeção cartográfica

Cálculos de distância, área, buffer e interseção são realizados em EPSG:31983. EPSG:4326 é usado apenas para publicação web e intercâmbio.

---

## 8. Variáveis principais

### 8.1. Exposições

- categoria tarifária: 1, 2, 3 ou 4;
- destino da gratuidade: sim/não;
- concessionária ou lote;
- período de gestão: público, pandemia, implantação concessionada, consolidação;
- regime de cessão: social, prazo fixo renovável, prazo fixo não renovável, prazo indeterminado;
- distância à centralidade;
- vulnerabilidade do entorno;
- renda distrital;
- composição racial territorial.

### 8.2. Desfechos espaciais

- distância euclidiana ao centroide da Sé;
- distância pela rede viária;
- tempo de viagem por automóvel e transporte coletivo;
- área e perímetro do cemitério;
- IPVS em buffers de 500 m, 1 km e 2 km;
- renda mediana e média do distrito;
- proporção preta+parda do distrito ou setor.

### 8.3. Desfechos funerários futuros

- quantidade de sepultamentos;
- proporção de gratuidades;
- cremações;
- exumações;
- reinumações;
- translados;
- destinação a ossuário;
- duração da permanência;
- renovação e extinção da cessão;
- disponibilidade de vagas e terrenos.

### 8.4. Mortalidade

- número de óbitos;
- taxa de mortalidade;
- idade mediana ao morrer;
- mortalidade prematura;
- anos potenciais de vida perdidos;
- raça/cor;
- escolaridade;
- sexo;
- causa básica;
- residência e local de ocorrência.

---

## 9. Periodização e controle da Covid-19

### 9.1. Períodos principais

- 2015-2019: pré-pandemia e pré-concessão;
- 2020-2022: choque pandêmico sob gestão pública;
- 2023-2024: implantação da concessão;
- 2025 em diante: consolidação, correções tarifárias e intervenção judicial/regulatória.

### 9.2. Regras

- apresentar 2020, 2021 e 2022 separadamente sempre que possível;
- calcular resultados com e sem os anos pandêmicos;
- usar março de 2020 e março de 2023 como marcos distintos em séries interrompidas;
- controlar excesso de mortalidade, sazonalidade e estrutura etária;
- relacionar exumações de 2023-2025 às coortes de sepultamento de 2020-2022;
- testar defasagens de 24, 36 e 48 meses.

A Covid-19 é tratada como choque de mortalidade e de infraestrutura, não como simples variável posterior no tempo.

---

## 10. Estatística descritiva

Para cada grupo, informar:

- número de equipamentos e número de territórios únicos;
- média, mediana, desvio-padrão e intervalo interquartil;
- mínimo e máximo;
- denominadores utilizados;
- quantidade de dados ausentes;
- distribuição completa quando o número de unidades for pequeno.

Com poucos cemitérios por estrato, resultados devem ser descritos como padrões da rede observada, não como amostra aleatória de uma população hipotética.

### 10.1. Dupla unidade de ponderação

Resultados serão apresentados:

1. por equipamento;
2. por distrito único.

Isso evita que distritos com dois equipamentos, como Consolação ou Carrão, recebam peso duplicado sem transparência.

---

## 11. Comparações entre grupos

### 11.1. Destinos gratuitos versus demais cemitérios

Comparar:

- distância ao centro;
- renda mediana;
- proporção preta+parda;
- IPVS do entorno;
- categoria tarifária;
- área disponível;
- regime de permanência.

### 11.2. Quatro estratos tarifários

Apresentar tendência e exceções. Não presumir relação perfeitamente linear entre categoria, renda e raça.

### 11.3. Testes inferenciais

Quando adequados:

- testes de permutação para diferenças de média ou mediana;
- bootstrap com intervalos de confiança;
- correlação de Spearman para categoria ordinal e indicadores territoriais;
- regressão robusta ou quantílica;
- modelos espaciais apenas se houver unidades suficientes e diagnóstico de autocorrelação.

Valores de p não serão apresentados isoladamente. Devem acompanhar tamanho de efeito, intervalo de confiança e interpretação substantiva.

---

## 12. Análise espacial

### 12.1. Centralidade

A distância ao centroide da Sé é um indicador simples e reproduzível, não uma medida completa de centralidade. Serão testadas alternativas:

- distância ao marco zero;
- distância ao centro histórico;
- tempo de viagem;
- acessibilidade à rede de transporte;
- centralidades do Plano Diretor.

### 12.2. Buffers

Buffers de 500 m, 1 km e 2 km serão calculados em EPSG:31983. A composição do IPVS será estimada por interseção espacial, preferencialmente ponderada por população, não apenas por área.

### 12.3. Autocorrelação

Quando houver número suficiente de territórios:

- Moran global;
- indicadores locais de associação espacial;
- erros-padrão espaciais ou modelos adequados.

Não se aplicará estatística espacial complexa a apenas 22 cemitérios sem justificativa.

### 12.4. Fluxos

A matriz futura `residência -> modalidade -> destino -> permanência` permitirá:

- linhas de desejo;
- matrizes origem-destino;
- distância média ponderada;
- proporção de fluxos centro-periferia;
- comparação racial e socioeconômica;
- acessibilidade familiar à memória.

---

## 13. Mortalidade e desigualdade racial

### 13.1. Denominadores

Contagens de óbitos devem ser acompanhadas de população residente por raça/cor, idade, sexo e território quando o objetivo for estimar risco.

### 13.2. Padronização etária

Comparações raciais e distritais devem usar:

- taxas específicas por faixa etária;
- padronização direta ou indireta;
- mortalidade prematura;
- anos potenciais de vida perdidos.

Idade média bruta ao morrer não é suficiente.

### 13.3. Dados ignorados

Raça/cor e escolaridade ignoradas devem ser exibidas por período e território. Análises serão repetidas:

- excluindo ignorados;
- mantendo ignorados como categoria;
- redistribuindo proporcionalmente apenas como análise de sensibilidade claramente identificada.

---

## 14. Dados ausentes e qualidade

Para cada variável, registrar:

- origem da ausência;
- percentual ausente;
- padrão temporal e territorial;
- possibilidade de ausência diferencial entre grupos;
- regra de exclusão ou imputação.

Imputação não será usada para inventar cemitério de destino, modalidade tarifária ou raça/cor individual. Quando aplicada a covariáveis, deverá ser documentada e comparada com análise de casos completos.

---

## 15. Testes de sensibilidade obrigatórios

1. incluir e excluir 2020-2022;
2. excluir apenas 2020-2021;
3. comparar 2017-2019 com 2023-2025;
4. usar média e mediana de renda;
5. calcular por equipamento e por território único;
6. usar três referências de centralidade;
7. usar buffers de 500 m, 1 km e 2 km;
8. incluir apenas geocodificações exatas e depois todas as plausíveis;
9. testar com e sem registros de raça/cor ignorada;
10. padronizar taxas por idade;
11. separar residência, ocorrência e destino;
12. testar defasagens de exumação de 24, 36 e 48 meses;
13. corrigir valores monetários pelo IPCA e comparar também com salário mínimo;
14. excluir equipamentos atípicos e documentar a mudança;
15. informar quando uma conclusão depende de uma única escolha analítica.

---

## 16. Inferência causal

A análise cartográfica inicial é observacional e descritiva. Ela pode demonstrar:

- existência de categorias tarifárias;
- distribuição territorial desigual;
- associação entre categoria, centralidade, renda e composição racial;
- diferenças jurídicas de permanência.

Ela não demonstra, isoladamente:

- que o entorno corresponde ao perfil dos mortos;
- que a concessão causou toda desigualdade observada;
- que empresas escolheram deliberadamente segregar corpos;
- que tarifa diferenciada equivale a especulação;
- que um aumento de exumações decorre da concessão e não da pandemia.

Para efeitos de gestão, serão considerados desenhos como:

- séries temporais interrompidas com marcos em 2020 e 2023;
- diferenças em diferenças, apenas se houver grupo comparável e tendências paralelas plausíveis;
- controle por excesso de mortalidade, inflação e mudanças regulatórias;
- triangulação com documentos e fiscalização.

---

## 17. Privacidade e ética

O repositório público não deve conter:

- nomes de falecidos;
- CPF;
- endereço residencial completo;
- número de declaração de óbito;
- dados individuais que permitam reidentificação;
- depoimentos ou memórias institucionais sem autorização.

Resultados de origem-destino devem ser agregados. Células pequenas serão suprimidas ou agrupadas conforme risco de reidentificação.

---

## 18. Reprodutibilidade computacional

Cada produto deve registrar:

- URL e data de acesso;
- hash ou versão do arquivo bruto;
- ambiente e versões de bibliotecas;
- script responsável;
- CRS de entrada e saída;
- parâmetros analíticos;
- data UTC de geração;
- advertências e contagens de qualidade.

O workflow automatizado deve:

1. baixar ou consultar fontes públicas;
2. preservar dados brutos;
3. processar geometrias;
4. gerar tabelas e relatórios;
5. executar validações;
6. recriar mapas;
7. publicar apenas quando as verificações mínimas forem satisfeitas.

---

## 19. Validações mínimas antes da publicação

### 19.1. Espaciais

- todas as geometrias possuem CRS declarado;
- cemitérios ficam dentro do município;
- área e perímetro são positivos;
- não há duplicidades não justificadas;
- Vila Formosa I e II permanecem distinguíveis;
- pontos de agência fora do município são rejeitados;
- rótulos não substituem coordenadas.

### 19.2. Tabulares

- identificadores são únicos;
- categorias pertencem ao domínio esperado;
- valores monetários têm data de referência;
- totais por grupo reconciliam com o inventário;
- denominadores são registrados;
- dados ausentes são contabilizados.

### 19.3. Estatísticas

- resultados reproduzidos por script;
- tabelas exibem número de unidades;
- análises de sensibilidade foram executadas;
- conclusões não excedem a unidade observada;
- efeitos da Covid são tratados separadamente.

---

## 20. Respostas a objeções previsíveis

### “O perfil do bairro não é o perfil dos mortos.”

Correto. A análise territorial descreve a localização do equipamento. A distribuição individual exige a matriz residência-destino.

### “Os cemitérios sempre foram desiguais; não foi a concessão que criou isso.”

A pesquisa não pressupõe ruptura total. Reconstrói continuidades e mudanças antes e depois da concessão, controlando período histórico e pandemia.

### “A categoria tarifária pode refletir custo ou patrimônio, não classe.”

Por isso a categoria é tratada como regra administrativa. A associação com renda, centralidade e prestígio é testada empiricamente, não presumida.

### “Há poucos cemitérios para testes estatísticos.”

Os 22 equipamentos são a população da rede concedida, não uma amostra. A inferência principal é descritiva; testes servem como medidas auxiliares de incerteza e sensibilidade.

### “A Covid distorceu tudo.”

A periodização separa 2015-2019, 2020-2022, 2023-2024 e 2025 em diante, com análises que excluem anos pandêmicos e testam defasagens de exumação.

### “Tarifa maior não prova especulação.”

Concordamos. O termo especulação só será sustentado mediante evidência de valorização, escassez, reconcessão ou circulação econômica.

### “Geocodificação automática é imprecisa.”

Cada resultado recebe grau de qualidade, é limitado ao município, preserva a resposta bruta e deve ser validado no GeoSampa/ortofoto antes de uso confirmatório.

---

## 21. Produtos previstos

- inventário auditável dos equipamentos;
- mapa dos quatro estratos tarifários;
- mapa da gratuidade;
- mapa da rede de agências;
- mapas de renda, raça/cor e IPVS;
- painel de mortalidade por residência;
- análise de permanência e exumação;
- matriz origem-destino, após LAI;
- séries tarifárias corrigidas por IPCA e salário mínimo;
- relatório técnico e capítulo acadêmico.

---

## 22. Regra de redação dos resultados

Cada conclusão deverá ser classificada internamente como:

- **documentada:** consta diretamente de norma, contrato ou base oficial;
- **calculada:** deriva de transformação reproduzível;
- **descritiva:** resume o conjunto observado;
- **associativa:** relaciona variáveis sem afirmar causa;
- **inferência forte:** sustentada por múltiplas fontes e testes;
- **hipótese:** ainda depende de dados adicionais.

A linguagem do texto deve refletir essa classificação.
