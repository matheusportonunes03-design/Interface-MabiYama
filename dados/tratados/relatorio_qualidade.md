# Relatório de Qualidade dos Dados (gerado pelo código)

Gerado em 28/11/2026 por `ETL/integracao.py`. Os números vêm da execução, não de digitação. Rodar de novo atualiza tudo.

## Premissas (o que estará disponível na hora da previsão)

- A previsão do dia D é feita às 05:00. Variáveis do dia D usam só dados em (D-1 05:00, D 05:00].
- O alvo do dia D é a falha de cada peça em (D 05:00, D+1 05:00].
- Falhas e manutenções são lançadas às 06:00, depois do corte, e por isso não entram nas variáveis do próprio dia.
- Horário dos turnos (**assumido, confirmar com o cliente**): manha 06:00 por 8 h, tarde 14:00 por 8 h, noite 22:00 por 8 h. Um turno só entra no dia D se terminou até o corte.
- `dias_desde_prev_*` (só preventivas) e `dias_desde_troca_*` (qualquer troca) contam até o corte; ficam vazios enquanto a peça não teve troca (não é erro).
- Datas fora do ISO são lidas como dia/mês/ano; as ilegíveis vão para `_rejeitados/`.
- Flags `flag_<problema>` (0/1) marcam toda linha cujo valor foi alterado; formatação pura (caixa, vírgula decimal) é contada aqui, mas não marcada.

## telemetria

Linhas lidas: **1006545** | linhas na saída: **1009424** | máquinas: 92

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| data_hora fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| Números com dois separadores (ex.: 1,736,809) | 0 | convertidos: o último separador é o decimal, os anteriores são milhar | O parser antigo trocava toda vírgula por ponto ('1.736.809'), que não é número, e o valor virava vazio. A conversão agora é conferida pela razão sensor_b/sensor_b_aux (regra rpm = rad/s x 60/2π). |
| Linhas sem data_hora válida ou id_maquina no padrão Mnnn | 0 | removidas da base tratada e salvas em _rejeitados/ | Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras tabelas; ficam guardadas à parte para conferência com o cliente. |
| Timestamps fora da hora cheia | 0 | arredondados para baixo (hora cheia) | A série é horária; a grade completa exige hora cheia. |
| Duplicatas exatas | 10002 | removidas (mantida a 1ª ocorrência) | Linha idêntica em todas as colunas é o mesmo registro lançado duas vezes. |
| Valor -999 (sem leitura) nos sensores | 1667 | convertido para vazio + flag_sentinela_999 | -999 é código de 'sem leitura', não medida. Fora dos sensores: 0 ocorrências. |
| Sensores com sinal negativo | 1619 | valor absoluto + flag_sinal_corrigido | Em módulo, os negativos caem na mesma faixa dos positivos (erro de sinal, não leitura nova). sensor_a: mediana /neg/=36.3 vs pos=36.2; P5-P95 /neg/=25.4-49.6 vs pos=25.2-48.2 / sensor_b: mediana /neg/=1919.4 vs pos=1923.8; P5-P95 /neg/=1589.1-2217.9 vs pos=1626.0-2211.2 / sensor_c: mediana /neg/=148.5 vs pos=148.7; P5-P95 /neg/=121.2-174.9 vs pos=122.6-176.3 / sensor_d: mediana /neg/=209.2 vs pos=210.8; P5-P95 /neg/=174.2-251.9 vs pos=170.1-252.6 |
| Zeros nos sensores | 1608 | convertidos para vazio + flag_zero_sensor | 1608 linhas; 0 com 2+ sensores zerados na mesma linha (se quase nunca há, é falha do sensor e não máquina parada); 1103 dessas linhas já vinham como 'suspeita'. Zero real puxaria as médias para baixo. |
| sensor_a ~10x maior que o normal da máquina | 2147 | dividido por 10 + flag_escala_sensor_a | Detectado por regra (valor / mediana da máquina entre 6 e 16, sustentado numa janela de 24 h), sem citar máquina no código. Janelas: M017: 2022-11-07 a 2022-12-21 (1078 linhas); M017: 2023-04-18 a 2023-06-01 (1069 linhas) |
| sensor_b vazio com sensor_b_aux preenchido | 10070 | recuperado: sensor_b_aux x 60/2π + flag_sensor_b_recuperado | As duas colunas medem a mesma grandeza (rpm x rad/s); razão observada 9.549 ± 0.019 em 981255 linhas (esperado 9.549 = 60/2π). O script para se a razão deixar de bater. |
| sensor_b_aux vazio com sensor_b preenchido | 4410 | recuperado: sensor_b x 2π/60 + flag_sensor_b_aux_recuperado | Mesmo caminho no sentido contrário. |
| qualidade_leitura = suspeita | 6411 | mantida como flag_suspeita; as leituras continuam nas médias | É pequena fração da base e os defeitos graves (-999, zeros, escala) já foram tratados à parte. A integração conta as suspeitas por dia (n_suspeita), assim a modelagem pode testar o efeito de excluí-las. |
| Mesma máquina e hora com valores diferentes | 2918 | média por máquina e hora + flag_conflito (qualidade 'suspeita' se alguma for) | As diferenças são pequenas, então a média é a estimativa mais neutra; 0 grupos têm 3+ linhas. Sensores já tratados (sem -999/zeros) entram na média; células vazias são ignoradas. |
| Horas faltando na série | 15799 | linhas criadas (grade horária completa por máquina), valores vazios + flag_hora_faltante | Sem a grade, médias e 'horas desde' ficam enviesadas. NÃO foi feita imputação: interpolação linear usa a hora seguinte (valor futuro) e atravessa o corte das 5:00. Imputar, se for o caso, deve ser feito na modelagem, ajustado só no treino. Máquinas que começam depois/terminam antes do período global: 92. |
| Outliers (limite superior IQR, após correções) | 48629 | mantidos, sem alteração | Pico alto em sensor é, em geral, o sinal que o modelo quer capturar; sem evidência de erro de lançamento não há motivo para removê-los. sensor_a: 10962 acima de 54.5 / sensor_b: 3126 acima de 2399.1 / sensor_c: 7409 acima de 192.3 / sensor_d: 4577 acima de 278.2 / temp_ambiente_c: 804 acima de 34.8 / sensor_b_aux: 3140 acima de 251.2 / vibracao_mm_s: 18611 acima de 7.6 |
| Umidade fora de 0-100 | 0 | mantidos (checagem) | Esperado 0 casos. |
| temp_ambiente_c / vibracao_mm_s negativos | 0 | mantidos (checagem) | Esperado 0 casos. |

## falhas

Linhas lidas: **695** | linhas na saída: **695**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| data_hora fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| peca fora do padrão | 0 | padronizada (peca_A..peca_D) | Mesma regra da tabela de manutenção, para cruzar por peça. |
| Peça ou id_maquina fora do padrão | 0 | mantidos como vieram (checagem) | Esperado 0. |
| Linhas sem data_hora, id_maquina ou peca válidos | 0 | removidas da base tratada e salvas em _rejeitados/ | Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras tabelas; ficam guardadas à parte para conferência com o cliente. |
| Duplicatas exatas | 0 | removidas (mantida a 1ª ocorrência) | Mesma falha lançada duas vezes duplicaria o rótulo positivo. |
| Duas peças ou mais na mesma máquina e hora | 51 | mantidas | É legítimo: o alvo é por peça, cada peça vira um rótulo próprio. |
| Falhas fora do horário padrão e sem manutenção correspondente | 15 | mantidas na tabela com flag_falha_suspeita; EXCLUÍDAS do alvo na integração (e o dia fica marcado alvo_incerto) | O horário padrão de lançamento é 06:00 e as falhas normais têm manutenção no mesmo instante. Estas não têm nenhuma e caem em poucos instantes (2023-01-02 03:00 (15 falhas)), padrão de lançamento em lote errado, que ainda explicaria o pico do mês. Não se remove da tabela porque a origem precisa ser confirmada com o cliente; a decisão está num parâmetro da integração (ACAO_FALHA_SUSPEITA). |
| Cobertura temporal das falhas | 2022-10-03 a 2023-09-30 | registrada (a integração só rotula os dias até a última falha) | Depois da última falha não se sabe se houve ou não falha. Tratar esses dias como 'sem falha' ensinaria negativos falsos ao modelo; por isso o alvo fica vazio neles. |

## manutencao

Linhas lidas: **4633** | linhas na saída: **4633**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| data_hora fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| peca fora do padrão | 450 | padronizado | Variações de caixa, acento e sufixo. |
| fornecedor_peca fora do padrão | 167 | padronizado | Variações de caixa, acento e sufixo. |
| custo_troca_reais com vírgula decimal | 137 | convertida para ponto | Formato brasileiro para número. |
| duracao_min com vírgula decimal | 0 | convertida para ponto | Formato brasileiro para número. |
| Valores fora do padrão (id_maquina, tecnico, lote_peca, peca, fornecedor) | 0 | mantidos como vieram (checagem) | Esperado 0 casos. id_maquina=0, tecnico=0, lote_peca=0, peca=0, fornecedor_peca=0 |
| Linhas sem data_hora, id_maquina ou peca | 0 | removidas da base tratada e salvas em _rejeitados/ | Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras tabelas; ficam guardadas à parte para conferência com o cliente. |
| Duplicatas exatas | 0 | removidas | Mesma troca lançada duas vezes. |
| Mesma máquina/data_hora/peça repetida | 0 | mantidas (checagem) | Esperado 0 casos. |
| lote_peca repetido em mais de uma linha | 322 | mantidos (checagem) | Um lote pode ser usado em mais de uma troca. |
| duracao_min <= 0 ou custo_troca_reais <= 0 | 0 | mantidos (checagem) | Esperado 0 casos. |
| Fornecedor diferente da letra do lote / AAMM do lote diferente da data | 0 | mantidos (checagem) | fornecedor x letra: 0; AAMM x data: 0. Esperado 0. |
| Manutenção corretiva x preventiva sem marcação | 680 | coluna tipo criada (corretiva = coincide máquina/hora/peça com uma falha) | 680 de 4633 trocas coincidem com falha. A corretiva é consequência da falha, não do calendário: misturar as duas confunde a idade da peça pelo calendário (dias_desde_prev) com o histórico de falhas. A integração gera as duas contagens (dias_desde_prev e dias_desde_troca), sempre com o corte das 05:00. |
| Intervalo entre trocas preventivas da mesma peça (múltiplo de 15 dias) | 3585 | informativo | 100.0% dos 3585 intervalos entre preventivas são múltiplos de 15 dias, o que confirma manutenção por calendário (útil na EDA). |
| custo_troca_reais acima do limite IQR | 0 | mantidos | Limite 4025.0. Peças diferentes têm custos diferentes; sem evidência de erro. |

## erros

Linhas lidas: **4768** | linhas na saída: **4718**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| data_hora fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| codigo_erro fora do padrão | 479 | padronizado (e encoding consertado) | Variações de caixa, acento, espaço e encoding quebrado do mesmo valor. |
| severidade fora do padrão | 171 | padronizado (e encoding consertado) | Variações de caixa, acento, espaço e encoding quebrado do mesmo valor. |
| Valores não reconhecidos em codigo_erro/severidade | 0 | mantidos como vieram (checagem) | Esperado 0 casos. |
| Linhas sem data_hora válida ou id_maquina no padrão Mnnn | 0 | removidas da base tratada e salvas em _rejeitados/ | Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras tabelas; ficam guardadas à parte para conferência com o cliente. |
| Duplicatas exatas | 50 | removidas (mantida a 1ª ocorrência) | Linha idêntica em todas as colunas é o mesmo alarme lançado duas vezes e inflaria qualquer contagem de erros. |
| Pico de erros às 06h | 1301 | mantidos e marcados com flag_horario_pico; a integração conta esses erros à parte | 1443 erros às 06h contra média de 142 nas outras horas (~1301 a mais), compatível com horário padrão de lançamento. 26 de 1443 têm outro registro da mesma id_maquina/codigo_erro no mesmo dia em outra hora (cópia lançada de novo). O horário exato desses erros não é informativo, então não entram na contagem principal (n_erros); ficam em n_erros_pico para a modelagem testar. |
| tempo_reconhecimento_min vazio | 91 | mantido vazio | Erro ainda não reconhecido ou sem registro; inventar um tempo criaria informação falsa. Se o modelo precisar, imputar na modelagem (ajustado só no treino). |
| tempo_reconhecimento_min acima do limite IQR | 256 | mantidos | Q1=7, Q3=21, limite=42, máximo=180 min. Tempos longos são plausíveis (alarme esquecido) e não há evidência de erro. |

## operacao

Linhas lidas: **126132** | linhas na saída: **126132**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| data fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| turno fora do padrão | 0 | padronizado | Variações de caixa e acento. |
| hora_extra fora do padrão | 115778 | padronizado | Variações de caixa e acento. |
| classe_risco fora do padrão | 70373 | padronizado | Variações de caixa e acento. |
| consumo_energia_kwh com vírgula decimal | 2552 | convertida para ponto | Formato brasileiro para número. |
| utilizacao_pct com vírgula decimal | 2545 | convertida para ponto | Formato brasileiro para número. |
| ind_quebra com vírgula decimal | 0 | convertida para ponto | Formato brasileiro para número. |
| score_saude com vírgula decimal | 0 | convertida para ponto | Formato brasileiro para número. |
| Valores fora do padrão (turno, hora_extra, classe_risco, ids) | 0 | mantidos como vieram (checagem) | Esperado 0 casos. |
| Linhas sem data ou id_maquina válidos | 0 | removidas da base tratada e salvas em _rejeitados/ | Sem a chave não dá para posicionar a linha no tempo nem cruzar com as outras tabelas; ficam guardadas à parte para conferência com o cliente. |
| Duplicatas exatas | 0 | removidas | Mesmo turno lançado duas vezes. |
| Mesma máquina/data/turno repetida | 0 | mantidas (checagem) | Esperado 0 casos. |
| Linhas faltando na grade máquina x dia x turno | 0 | mantidas (checagem) | Esperado 0 casos (grade completa). |
| meta_producao vazia | 3701 | 3698 recuperadas pelo valor dos outros turnos do dia + flag_meta_imputada; 3 continuam vazias | A meta é igual nos turnos da mesma máquina e dia (0 conflitos), então copiar não inventa informação. As que continuam vazias não têm nenhum turno do dia com meta. |
| classe_risco diferente da regra do dicionário (ind_quebra) | 162 | recalculada pela regra (<=40 baixo, <=70 médio, >70 alto) + flag_classe_risco_recalculada | A coluna é derivada do índice; manter valor divergente criaria duas fontes de verdade. |
| utilizacao_pct fora de 0-100 | 0 | mantidos (checagem) | Esperado 0 casos. |
| ind_quebra fora de 0-100 | 0 | mantidos (checagem) | Esperado 0 casos. |
| score_saude fora de 0-100 | 0 | mantidos (checagem) | Esperado 0 casos. |
| pecas_defeituosas maior que pecas_produzidas | 0 | mantidas (checagem) | Esperado 0 casos; se houver, conferir com o cliente. |

## maquinas

Linhas lidas: **92** | linhas na saída: **92**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| modelo fora do padrão | 9 | padronizado | Variações de caixa, espaço e formato. |
| fabricante fora do padrão | 7 | padronizado | Variações de caixa, espaço e formato. |
| pais_origem fora do padrão | 0 | padronizado | Variações de caixa, espaço e formato. |
| linha_producao fora do padrão | 6 | padronizado | Variações de caixa, espaço e formato. |
| Máquinas distintas no cadastro | 92 | registrado | A proposta do projeto cita 100 máquinas; a base tem esta quantidade. |
| modelo/fabricante/país vazios | 10 | 10 células preenchidas pela correspondência 1 para 1 + flag_trio_preenchido | Cada modelo tem um único fabricante e país (e vice-versa), então um dado conhecido define os outros sem ambiguidade. Vazios restantes: 0. Correspondência: modelo_A=Fabrimaq/Brasil; modelo_B=Indutec/Alemanha; modelo_C=Metalforte/Italia; modelo_D=Vortex/China |
| data_instalacao fora do formato ISO | 0 | 0 convertidas lendo dia/mês/ano; 0 ilegíveis viram vazio (e a linha vai para _rejeitados/ se for chave) | Formatos misturados no mesmo arquivo. A saída sai toda em ISO. Exemplos ilegíveis: nenhum |
| idade vazia | 13 | 11 recuperadas (2022 - ano de instalação) + flag_idade_recuperada; 2 continuam vazias com flag_sem_idade_nem_data | idade + ano de instalação = 2022 em todas as 71 máquinas que têm os dois dados (o script para se isso deixar de valer). As sem idade e sem data não têm de onde recuperar. |
| data_instalacao vazia | 10 | mantida vazia; ano recuperado da idade em 8 (flag_ano_instalacao_imputado) | O ano é recuperável (referência - idade), o dia não. Na integração usa-se o meio do ano (1º de julho), e a idade fica marcada como aproximada. |
| Idade com ano de referência arbitrário (2024) | 0 | não recalculada: a coluna fica na referência 2022 | A idade correta depende da data da previsão (data - data de instalação), calculada na integração. Fixar um ano criaria uma idade que não vale para nenhuma data real. |

## integracao

Linhas na saída: **42136**

| Problema | Casos | Decisão | Justificativa |
|---|---:|---|---|
| Colunas redundantes do cadastro (fabricante, país, capacidade, potência) | 4 | fora da base integrada (continuam em maquinas_corrigido.csv) | São 1 para 1 com o modelo; usar só o modelo evita variáveis duplicadas. |
| id_maquina fora do cadastro (em qualquer tabela) | 0 | ignorados na integração (checagem) | Esperado 0 casos. |
| Turno vazio ou fora de comum.TURNOS | 0 | linha fora da agregação da operação | Sem saber o fim do turno não dá para garantir que ele terminou antes do corte das 05:00. Valores encontrados: []. |
| dias_desde_prev vazio (nenhuma preventiva da peça antes do corte) | 581 | mantido vazio | Não existe troca anterior para medir; zero ou outro número inventaria uma idade de peça. Acontece nos primeiros dias da série e em peças sem preventiva registrada. A modelagem decide (ex.: indicador de 'sem histórico' + imputação ajustada só no treino). Por peça: peca_A=152, peca_B=273, peca_C=0, peca_D=156 |
| dias_desde_troca (qualquer troca, preventiva ou corretiva) | 4 | colunas dias_desde_troca_peca_X criadas, com o mesmo corte das 05:00 | Depois de uma troca corretiva a peça é nova, e só a contagem por preventiva diria que ela é velha. A corretiva de uma falha lançada às 06:00 de D entra só nas variáveis de D+1 (depois do corte), então não vaza o alvo de D; o teste de vazamento cobre isso. |
| Dias depois da última falha registrada | 8648 | alvo vazio e alvo_disponivel = 0 | A tabela de falhas termina em 2023-09-30. Esses dias não são 'sem falha': não se sabe. Rotulá-los 0 criaria negativos falsos. Excluir do treino/validação. |
| Máquina-dias com falha suspeita na janela do alvo | 15 | alvo_incerto = 1 (ACAO_FALHA_SUSPEITA = 'excluir_do_alvo') | Recomenda-se tirar essas linhas do treino enquanto a origem das falhas suspeitas não é confirmada com o cliente. |
| Cobertura temporal por tabela | telemetria 2022-10-01 a 2024-01-01; erros 2022-10-01 a 2024-01-01; manutencao 2022-03-01 a 2024-01-01; falhas 2022-10-03 a 2023-09-30; operacao 2022-10-01 a 2023-12-31 | registrada (checagem) | Tabelas que começam depois ou terminam antes das outras deixam variáveis vazias nesses dias. Se falhas começar depois da telemetria, os dias anteriores ficam rotulados 0 sem que se saiba se houve falha: conferir antes de treinar. |
| idade_anos negativa (dia anterior à instalação) | 0 | mantida (checagem) | Esperado 0 casos; se houver, a data de instalação ou a série está errada. |
| Janela de previsão | 42136 | máquina x dia; variáveis em (D-1 05:00, D 05:00]; alvo em (D 05:00, D+1 05:00] | Falhas e manutenções são lançadas às 06:00; o corte às 05:00 impede que o registro do dia entre nas variáveis do próprio dia (vazamento). |
