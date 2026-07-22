# Nota analítica — PGV 2026 no entorno dos cemitérios particulares candidatos

## Estatuto

Esta nota interpreta os resultados produzidos por `scripts/analyze_private_cemetery_land_values_2026.py`. O universo de 21 unidades foi obtido por diferença entre a camada completa de cemitérios do GeoSampa e as feições já vinculadas à rede municipal concedida. A propriedade, a situação de funcionamento e o regime de acesso continuam pendentes de validação externa.

Os números não permitem afirmar que São Paulo possui exatamente 21 cemitérios privados ativos. Eles caracterizam 21 unidades espaciais candidatas a cemitérios particulares, associativos, religiosos ou não concessionados.

## Resultado principal

No anel de 0 a 250 metros, 20 das 21 unidades candidatas receberam valor da PGV. A mediana das medianas cemiteriais foi de R$ 920,50/m², com primeiro quartil de R$ 562,25/m², terceiro quartil de R$ 3.472,50/m² e amplitude entre R$ 320,00/m² e R$ 17.906,00/m².

O resultado agregado é próximo da categoria 3 da rede municipal concedida, cuja mediana é R$ 895,25/m². Essa proximidade não significa equivalência entre os regimes. O universo candidato é internamente muito mais heterogêneo e reúne equipamentos inseridos tanto em territórios centrais e altamente valorizados quanto em áreas periféricas com baixa valoração fiscal.

## Heterogeneidade interna

Os maiores valores no entorno imediato foram observados em:

- Terceira Ordem do Carmo: R$ 17.906,00/m²;
- Protestantes: R$ 17.906,00/m²;
- Redentor: R$ 10.222,00/m²;
- Santíssimo Sacramento: R$ 5.834,00/m²;
- Israelita de São Paulo: R$ 5.241,00/m².

Entre os menores valores registrados estão:

- Colônia: R$ 320,00/m²;
- Parque dos Girassóis: R$ 320,00/m²;
- Parque da Cantareira: R$ 320,00/m²;
- Carmo I: R$ 428,00/m²;
- Carmo II: R$ 446,00/m².

Essa distribuição impede tratar “cemitério privado” como categoria espacial ou econômica única. A propriedade privada pode abrigar circuitos historicamente associativos e religiosos em áreas centrais, cemitérios-parque em zonas periféricas, equipamentos comerciais de diferentes padrões e unidades cujo acesso pode ser restrito.

## Sensibilidade à cobertura da PGV

A mediana de R$ 920,50/m² utiliza todas as unidades com algum valor disponível. A cobertura cadastral, porém, é desigual e parece relacionada à própria posição periférica de alguns equipamentos.

Quando se exigem coberturas mínimas no indicador `cobertura_area_quadras_pgv_pct`, a mediana muda:

| Cobertura mínima | Unidades incluídas | Mediana no anel de 0–250 m |
|---:|---:|---:|
| qualquer cobertura positiva | 20 | R$ 920,50/m² |
| 40% | 19 | R$ 978,00/m² |
| 50% | 17 | R$ 1.397,00/m² |
| 80% | 14 | R$ 1.841,00/m² |
| 90% | 13 | R$ 2.051,00/m² |

A variação mostra que o resumo agregado depende de como tratamos áreas com baixa correspondência entre quadras fiscais e registros da PGV. Não é metodologicamente seguro concluir, com a mediana simples, que o universo particular se localiza em territórios menos valorizados que a rede municipal.

Casos que exigem cautela especial no anel imediato:

- Memorial Parque das Cerejeiras: nenhuma quadra vinculada à PGV;
- Colônia: 5,22% de cobertura das quadras intersectadas;
- Parque dos Pinheiros: 42,16%;
- Parque Jaraguá: 47,93%;
- Horto Florestal: 56,41%.

A ausência ou baixa cobertura não é apenas ruído técnico. Pode refletir áreas extensas, rurais, ambientais ou pouco parceladas, justamente características relevantes da geografia de alguns cemitérios periféricos. Por isso, esses casos devem ser preservados e analisados, não simplesmente excluídos.

## Anomalias que orientam a validação

Alguns resultados sugerem que a unidade espacial e a nomenclatura institucional precisam ser verificadas:

1. Terceira Ordem do Carmo e Protestantes apresentam o mesmo valor e compartilham praticamente o mesmo entorno central. São unidades institucionais distintas, mas não observações territoriais independentes em sentido forte.
2. Israelita de São Paulo e Israelita do Butantã aparecem no mesmo endereço publicado, mas com polígonos e valores muito diferentes. É necessário confirmar se são unidades operacionais distintas, setores de um mesmo complexo ou registros históricos sobrepostos.
3. Parque Jaraguá e Gethsêmani Anhanguera aparecem em trechos muito próximos da Rodovia Anhanguera. A relação espacial, proprietária e operacional entre ambos precisa ser validada.
4. O Cemitério do Morumby apresenta mediana de R$ 1.631,00/m², valor inferior ao que o nome do bairro poderia sugerir. Isso reforça que PGV, limite do polígono e posição específica no território são mais informativos que reputações genéricas de bairro.

## Comparação correta com a rede municipal

A rede municipal concedida está dividida em categorias tarifárias formalmente reguladas. O universo particular candidato não possui uma classificação equivalente. Portanto, a comparação não deve opor uma média “pública” a uma média “privada” como se fossem grupos homogêneos.

A comparação mais promissora é distributiva e relacional:

- verificar quais circuitos particulares se aproximam da categoria 1;
- identificar unidades particulares inseridas em territórios semelhantes às categorias 3 e 4;
- distinguir cemitérios históricos, associativos, religiosos, cemitérios-parque e equipamentos comerciais;
- cruzar valor territorial com preço, acesso, permanência, manutenção e transmissão de direitos funerários.

## Formulação provisória

A camada particular não forma um estrato superior uniforme ao sistema municipal. Ela amplia a polarização da geografia funerária paulistana: reúne alguns dos cemitérios situados nos territórios fiscalmente mais valorizados da cidade e, ao mesmo tempo, equipamentos periféricos em áreas de baixa valoração e cobertura cadastral incompleta.

Esse resultado fortalece a necessidade de tratar a cidade funerária como um campo composto por regimes distintos, e não como oposição simples entre cemitérios públicos pobres e cemitérios privados ricos.
