# Cemitérios particulares no GeoSampa — inventário preliminar

## Por que esta frente foi aberta

A análise do sistema funerário paulistano estava concentrada nos 22 cemitérios municipais concedidos e no Crematório Vila Alpina. Para compreender a geografia funerária da cidade inteira e distinguir gestão privada de propriedade privada, é necessário incluir os cemitérios particulares como uma camada própria.

Este inventário não altera o foco principal do artigo, que permanece na transformação da rede pública municipal. Ele cria um universo comparativo para responder a três perguntas:

1. o que já existia como mercado cemiterial antes da concessão;
2. o que é específico da operação privada de bens públicos concedidos;
3. como os equipamentos particulares alteram a distribuição espacial da oferta funerária em São Paulo.

## Fonte e método

A camada oficial `geoportal:equipamento_cemiterio` do GeoSampa foi capturada em 20 de julho de 2026 e contém 46 feições. A descrição oficial informa que ela reúne cemitérios públicos e privados e serviços funerários.

A classificação não pode utilizar diretamente o campo de esfera administrativa. Na captura atual, todas as 46 feições aparecem como `MUNICIPAL`, inclusive equipamentos que, por nome e trajetória institucional, parecem ser particulares, associativos ou religiosos.

Foi adotado o seguinte procedimento:

1. partir das 46 feições da camada oficial;
2. identificar as feições já vinculadas documentalmente aos 23 pontos operacionais da rede pública concedida por meio de `data/reference/geosampa_mapping.csv`;
3. classificar as feições restantes como candidatas a cemitérios particulares ou a outros equipamentos não pertencentes à rede concedida;
4. agregar feições com o mesmo nome e endereço normalizados;
5. manter a classificação como provisória até validação regulatória, ambiental, sanitária ou fiscal.

## Resultado preliminar

- 46 feições na camada do GeoSampa;
- 24 feições vinculadas à rede pública concedida;
- essas 24 feições representam 23 pontos operacionais, porque o Cemitério do Lageado possui duas feições;
- 22 feições não vinculadas à rede concedida;
- as 22 feições correspondem a 21 unidades candidatas, porque o Cemitério do Morumby aparece em duas feições idênticas.

**Resultado provisório: o GeoSampa sugere 21 cemitérios particulares, associativos, religiosos ou não pertencentes à rede municipal concedida.**

Esse número não deve ainda ser apresentado como quantidade oficial de cemitérios particulares ativos no Município. O GeoSampa informa a existência espacial do equipamento, mas não estabelece de forma confiável sua natureza jurídica, seu regime de acesso ou sua situação atual de funcionamento.

## Candidatos identificados

1. Cemitério da Colônia;
2. Cemitério da Paz;
3. Cemitério da Terceira Ordem do Carmo;
4. Cemitério de Congonhas;
5. Cemitério do Carmo I;
6. Cemitério do Carmo II;
7. Cemitério do Morumby;
8. Cemitério dos Protestantes;
9. Gethsemani Morumbi;
10. Cemitério Horto Florestal;
11. Cemitério Israelita de São Paulo;
12. Cemitério Israelita do Butantã;
13. Cemitério Jardim do Pêssego;
14. Memorial Parque das Cerejeiras;
15. Parque Cemitério Gethsêmani Anhanguera;
16. Cemitério Parque da Cantareira;
17. Cemitério Parque dos Girassóis;
18. Cemitério Parque dos Pinheiros;
19. Cemitério Parque Jaraguá;
20. Cemitério Redentor;
21. Cemitério Santíssimo Sacramento.

A relação completa, com endereços, CEPs e identificadores das feições, está em `data/processed/cemiterios_particulares_candidatos_geosampa.csv`.

## Achado metodológico relevante

A principal descoberta inicial não é apenas o número 21. É a inconsistência classificatória da própria camada: o GeoSampa reúne públicos e privados, mas atribui esfera municipal a todas as feições.

Isso reforça uma hipótese mais ampla do projeto: a governança funerária é fragmentada também no plano informacional. A cidade possui uma camada espacial abrangente, mas ela não permite distinguir com segurança propriedade, operação, acesso e situação regulatória.

A divergência deve ser tratada primeiro como problema de qualidade e integração cadastral. Somente após a triangulação será possível discutir se ela expressa desatualização, herança institucional do antigo SFMSP ou ausência de padronização entre órgãos.

## Consequência analítica

O sistema funerário paulistano deve ser descrito por pelo menos três configurações:

| Propriedade | Operação | Configuração |
|---|---|---|
| pública | pública | autarquia municipal até 2022 |
| pública | privada | rede municipal concedida desde 2023 |
| privada | empresarial, associativa ou religiosa | cemitérios particulares |

Essa triangulação impede que concessão e propriedade privada sejam tratadas como sinônimos. Ela também permite investigar se a concessão criou novas relações mercantis ou incorporou à rede pública práticas já consolidadas no circuito particular.

## Limites atuais

O inventário ainda não informa de maneira validada:

- propriedade ou CNPJ;
- entidade administradora;
- acesso aberto ou restrito;
- situação ativa, interditada ou encerrada;
- existência de crematório, ossuário, columbário e velório;
- preços e formas de manutenção;
- renovação, transmissão e retomada dos direitos funerários;
- data de início e atos de autorização.

## Próximas validações

1. solicitar à SP Regula a relação atualizada de cemitérios particulares e administradores;
2. cruzar os candidatos com processos de regularização ambiental da SVMA;
3. consultar registros sanitários e fiscais;
4. validar individualmente natureza jurídica, funcionamento e acesso;
5. incorporar os polígonos validados ao mapa geral em camada distinta;
6. comparar preços, temporalidades e direitos com a rede pública concedida.

## Estatuto do resultado

- **documentado:** a camada possui 46 feições e se descreve como abrangendo cemitérios públicos e privados;
- **calculado:** 22 feições não pertencem ao mapeamento validado da rede concedida;
- **resultado preliminar:** essas feições formam 21 unidades candidatas após a agregação de duplicatas;
- **questão aberta:** quantas dessas 21 unidades são oficialmente particulares e estão atualmente em funcionamento.
