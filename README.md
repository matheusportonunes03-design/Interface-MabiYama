# MaBiYama · Painel da Frota (Streamlit)

Versão em Python do painel feito no Lovable, com o mesmo visual: login, **Previsão & Modelagem**,
**Análise Exploratória** e **Perfil**.

## Rodar
```bash
pip install -r requirements.txt
python gerar_hash_senha.py          # gera o hash da senha
# copie .streamlit/secrets.toml.exemplo para .streamlit/secrets.toml e cole o login + hash
streamlit run app.py
```
No Streamlit Cloud: *Main file path* = caminho até `app.py`; o conteúdo do `secrets.toml` vai em *Settings → Secrets*.

## Como o visual foi reproduzido
- `app.py`: login, cabeçalho em degradê, abas e perfil, feitos com widgets do Streamlit e o CSS do Lovable
  (mesmas cores, fonte Nunito, botões e campos).
- `frontend/painel.js`: o componente das abas do Lovable (React + Recharts), portado sem etapa de build e
  alimentado com os dados reais. Roda dentro do app, sem depender de internet:
  - `frontend/vendor.js`: React 18, ReactDOM, Recharts 2.15, prop-types e htm (licenças MIT);
  - `frontend/painel.css`: Tailwind gerado a partir de `frontend/tw_entrada.css`;
  - `frontend/fontes.css`: fonte Nunito embutida (licença OFL).
- `painel_dados.py`: transforma a pasta `dados/` no JSON que o painel desenha.

Se mudar classes no `painel.js`, gere o CSS de novo:
`npx @tailwindcss/cli -i frontend/tw_entrada.css -o frontend/painel.css --minify`

## Dados (`dados/`)
A pasta só tem arquivos **agregados**: nenhuma base da competição vai para o repositório.

Gerados por `preparar_dados.py` a partir das bases tratadas (`*_corrigido.csv`):
```bash
python preparar_dados.py --bases <pasta com as bases tratadas>
```
| arquivo | conteúdo |
|---|---|
| indicadores.csv | nº de máquinas, falhas (sem as 15 suspeitas), preventivas, leituras |
| falhas_por_peca.csv, falhas_por_modelo.csv, falhas_por_idade.csv, mensal.csv | contagens para os gráficos |
| erros_pre_falha.csv | volume de cada código de erro e % lançado nas 24h antes de uma falha |
| sinal_pre_falha.csv | média do sensor de cada peça (em desvios do normal) nas 48h antes da falha |
| qualidade.csv | linhas, nulos e duplicatas de cada base tratada |
| maquinas_resumo.csv | só id, modelo e idade de cada máquina (para a tabela de prioridade) |

Vindos do modelo:
| arquivo | conteúdo |
|---|---|
| previsao.csv | previsão no formato da submissão (hoje a g2, Kaggle 0,70769: fusão "3 melhores posições" de y09 + v2 + membros A–E). Pode ser trocada pelo botão "Enviar dados do dia". |
| validacao.csv | escores fora da amostra da sub 37, rodada nas bases tratadas, nas 3 janelas de validação temporal |
| importancia.csv | importância das variáveis do ExtraTrees "hat" da sub 37, treinado nas bases tratadas |

### Tratamento das bases brutas (`ETL/`) e botão "Atualizar com bases brutas"
`ETL/` é o tratamento final da Etapa 2, copiado do repositório da equipe (`2026-2-t2-Equipe-05/ETL`). Rodado sobre as bases
brutas do cliente, reproduz célula a célula as 7 tabelas de `dados/tratados/` (conferido em 27/11/2026):
```bash
python ETL/integracao.py --dados <pasta com extraídos/>     # grava <pasta>/tratados/*_corrigido.csv, a base integrada e o relatório
python preparar_dados.py --bases <pasta>/tratados --so-tabelas   # converte para os .parquet do painel
```
Única mudança em relação ao repositório da equipe: `comum.dia_primeiro` decide pelos próprios dados se as datas fora do ISO
estão em dia/mês/ano ou mês/dia/ano (o Excel em inglês salva `10/1/2022 6:00`; antes isso virava 10 de janeiro).

Na aba **Dados tratados**, o botão **Atualizar com bases brutas** recebe os 6 CSVs brutos (`atualizar_bases.py`): reconhece cada
base pelo cabeçalho, roda o ETL num processo separado (~1 a 2 min, ~1 GB de pico), converte para Parquet e troca as tabelas da
aba e da ficha das máquinas **só na sessão de quem enviou** (os arquivos ficam em `/tmp` do servidor e são apagados depois de
1 dia). "Voltar às bases do projeto" desfaz. Os gráficos da Análise Exploratória e a previsão continuam os do projeto.

`ferramentas/integracao.py` é uma reimplementação só da etapa de integração (lê os `*_corrigido` em CSV ou Parquet), também
conferida contra a base integrada; o caminho oficial é `ETL/integracao.py`.

## Observações
- As probabilidades exibidas vêm do percentil do escore entre as linhas candidatas, convertido pela taxa de falha
  observada na validação temporal. São aproximadas: a submissão é um ranking, não uma probabilidade.
- Só as linhas em que D+1 é dia de grade (preventiva a cada 15 dias) recebem probabilidade; as demais ficam em 0%.
- O login usa hashes em `secrets.toml` (`[usuarios."login"]` com `nome` e `senha_sha256`). "Esqueci minha senha", "Cadastre-se" e os botões Google/Lovable aparecem como no Lovable, mas só mostram um aviso: o acesso é criado pela equipe.
- Nome e foto do perfil valem só durante a sessão (não há banco de dados).

## Barra lateral

- **Navegação** entre Previsão & Modelagem, Análise Exploratória e Perfil.
- **Filtros da previsão**: dia, peças, modelos de máquina, risco mínimo e busca por máquina. Valem para o alerta das
  cinco máquinas e para a tabela de prioridades.
- **Baixar lista do dia**: CSV (separador `;`) com as candidatas do dia que passam nos filtros, em ordem de prioridade.
- **Análise exploratória**: escolha de temas da galeria e opção de abrir todos os insights.
- **Sobre o modelo**: previsão em uso, AUC-PR da validação, nota no Kaggle e horizonte.

## Galeria da análise exploratória

A aba mostra primeiro os 4 indicadores (cada um abre um detalhe) e as **principais análises**: os 7 gráficos que mais explicam as
falhas, todos com botão **Insight**. O texto abre e fecha com uma expansão gradual (0,55 s), como a barra lateral. Logo abaixo,
**"Ver todas as análises (23)"** abre a galeria completa, organizada por tema (chips com a contagem de cada tema, um bloco por tema),
cada gráfico com seu Insight e clique para ampliar.

`dados/eda/` traz os 23 gráficos do notebook da Etapa 3 (WebP) e `graficos.json`, com título, tema e o parágrafo de
insight de cada um. Para trocar um gráfico, substitua o `.webp` com o mesmo nome; para mudar o texto, edite o JSON.

## Aba "Máquinas" (ficha da máquina)

Escolha uma máquina no seletor do topo da ficha ou na barra lateral; os dois ficam sincronizados. O seletor da página lista as
92 máquinas (sem os filtros da barra lateral), em ordem de **número** ou de **risco de falha**, com ◀ Anterior / Próxima ▶; se a
máquina escolhida estiver fora dos filtros da barra lateral, esses filtros são limpos. A ficha mostra:
- **Cadastro:** modelo, idade, fabricante, planta, linha e potência.
- **Risco previsto no período de teste:** cada círculo é um dia de grade da peça; o tamanho e o número mostram a probabilidade de falha.
- **Histórico:** falhas por peça, última preventiva e próxima data de grade de cada peça, erros por código.
- **Sensores:** leitura horária ou média diária do sensor da peça, com falhas, preventivas e corretivas marcadas. Por padrão, o período mostrado são as 4 semanas em volta da última falha da peça.

## Aba "Dados tratados"

Explorador das 7 bases tratadas completas: telemetria, base integrada, operação, manutenção, erros, falhas e máquinas.
- **Filtros:** máquina, período e colunas.
- **Indicadores do recorte:** linhas, colunas, máquinas e período.
- **Dicionário de colunas:** tipo, % de vazios e faixa de valores de cada coluna.
- **O que foi tratado:** o trecho do relatório de qualidade do ETL referente à tabela.
- **Download:** CSV do recorte (com `;` e vírgula decimal, abre direto no Excel), até 300 mil linhas.

As bases ficam em `dados/tratados/*.parquet` (cerca de 22 MB) e são geradas por:

    python preparar_dados.py --bases <pasta com as bases tratadas> --so-tabelas

(`--tabelas` gera também os resumos do painel.)

> **Atenção:** são as bases da competição. Mantenha o repositório **privado**, porque divulgar os dados pode ferir as regras do Kaggle. O Streamlit Cloud funciona normalmente com repositório privado.

## Barra lateral

Ao fechar a barra lateral, aparece o botão **Menu** no canto superior esquerdo, que a abre de novo.

## Replay da frota, Raio-X da falha e Simulador

Os três usam `dados/extras.json`, gerado a partir da **validação temporal** (31/12/2022 a 29/09/2023), o único período em que as
falhas reais são conhecidas (as do teste do Kaggle são ocultas).

- **Replay da frota** (aba Previsão & Modelagem, abaixo dos indicadores): mapa da planta por linha de produção; a cor de cada peça é o
  risco que o modelo (fusão g2) deu às 05:00; falhas reais pulsam em verde (estava no top-10 do dia) ou vermelho (escapou).
- **Raio-X da falha** (mesma aba, no fim): 4 casos reais animados hora a hora: sensor da peça, janela de 96 h do filtro casado e a evidência
  convertida em probabilidade (razão de verossimilhança × taxa base do ciclo), comparada com a probabilidade final do modelo.
- **Simulador** (aba própria): política "antecipar a preventiva" por limiar de risco e capacidade diária, com premissas de custo ajustáveis;
  Monte Carlo (durações de parada Gama, eficácia Bernoulli, dias reamostrados), curva custo × limiar e mapa de decisão.

Para regenerar: `python ferramentas/oof_g2.py` e `python ferramentas/gerar_extras.py` (ajuste os caminhos no topo dos scripts:
pasta dos CSV tratados e pasta `resultados/` do notebook da Etapa 4).

## Aparência, marca e barra lateral por aba

- `tema.py`: logo da MaBiYama sem fundo (`frontend/marca/logo_claro.webp` e `logo_escuro.webp`, esta com o roxo e o azul clareados
  para fundo escuro), navegação com ícones e marcador âmbar, ondas animadas no cabeçalho e na barra lateral, e o **modo claro/escuro**
  (no fim da barra lateral). O tema escuro troca as variáveis de cor do app e das páginas em iframe; tabelas e gráficos Altair também mudam.
- **Dados tratados**: ordenar por coluna, ir para uma linha, para uma coluna ou para uma célula (o valor aparece na barra lateral e a célula
  fica destacada), buscar um valor em todas as colunas ou numa só (com ◀ ▶ entre as ocorrências), ir ao topo ou ao fim, e ver a linha inteira.
- **Máquinas**: ordenar a frota (maior risco, mais falhas, código), filtrar por linha e modelo, escolher a máquina, ◀ anterior / próxima ▶,
  atalhos para as de maior risco, peça e resolução do sensor e download do histórico da máquina.
- **Simulador**: cenários prontos de premissas, período de 2023, peças, linhas de produção e número de cenários de Monte Carlo.
- **Galões** (aba Previsão & Modelagem): os 4 indicadores viram reservatórios animados; o botão "Insight" abre a explicação e leva ao gráfico.
- **Replay** no estilo rede hidráulica: linhas de produção como canos, máquinas como bombas (pingam acima de 40%).
- **Tela de entrada "Maré"** e **cabeçalho com borda ondulada** (máscara CSS animada em `tema.py`), com a logo em branco
  (`frontend/marca/logo_cabecalho.webp`) no lugar do nome e bolhas subindo (`BOLHAS_CAB`).
- Paleta do modo escuro em azul mais sóbrio (sem brilho nos selecionados nem anel de foco luminoso).

## Animação de boas-vindas e ajudantes (Beto e Floco)
Ao entrar, o operário **Beto** chega à fábrica, veste capacete, colete, luvas e óculos, pega a chave inglesa e a caixa de
ferramentas e pergunta em qual máquina fazer manutenção primeiro. O **Floco** (robô-boneco-de-neve, que representa o modelo)
se apresenta e responde com as 5 máquinas de maior probabilidade da previsão em uso. Depois a rolagem é liberada.

Em todas as páginas (Previsão & Modelagem, Análise Exploratória, Simulador, Máquinas e Dados tratados) os dois ficam **juntos na
lateral direita**: o Floco do lado do conteúdo, apontando para o bloco, e o Beto ao lado dele. Para cada bloco o Beto faz uma
pergunta e o Floco explica, num balão de diálogo; o bloco explicado ganha uma moldura.

Como o bloco é escolhido:
- vale o bloco que está **sob o mouse** (a troca acontece depois de ~0,3 s parado em cima dele, inclusive enquanto a página rola);
- com o mouse fora de qualquer bloco, ou sem mouse (toque), vale o que está **no centro da tela**; no começo e no fim da página a
  "linha de leitura" sobe ou desce, para os primeiros e os últimos blocos também serem explicados;
- nesse modo, cartões lado a lado na mesma altura são explicados **da esquerda para a direita**, um depois do outro;
- a troca só acontece quando a escolha fica estável, para não piscar.

Início da cena: a capa "Entrando na fábrica…" fica na tela até a página terminar de carregar (script do Streamlit parado, iframes
prontos e fontes carregadas, estável por 0,6 s; no máximo 15 s). Só então a cena começa, desde a fábrica vista de fora, para nada
ser cortado. "Rever animação" toca a entrada inteira de novo.

Personalização do operário: botão **Personalizar** (barra lateral, em Ajudantes, ou no canto superior direito da tela). Abre um
painel com prévia animada (dá para girar o personagem e tirar os EPIs) e escolhe nome, sexo, pele, cabelo (curto, raspado,
cacheado, rabo de cavalo, longo), cor do cabelo, barba, camisa, calça, calçado, capacete, colete e luvas (paleta ou qualquer cor).
Fica salvo no navegador (`localStorage`, chave `mby_operario`); o nome aparece nos balões e no diálogo. Nos textos de
`animacao.py`, `{beto}` é trocado pelo nome escolhido.

Arquivos:
- `animacao.py`: o top 5 da cena e os blocos de cada página (`blocos_modelo`, `blocos_eda`, `blocos_maquinas`, `blocos_dados`,
  `blocos_sim`), cada um com o título que aparece na tela, a pergunta do Beto e a explicação do Floco, montados com os dados reais.
  Os 23 gráficos da galeria usam o insight do `graficos.json`. Para mudar um texto, edite a função da página.
- `frontend/fabrica_cena.js` (sala isométrica, máquinas, personagens em pixel-art), `fabrica_motor.js` (roteiro, escolha do bloco,
  diálogo, rolagem), `fabrica_perso.js` (painel de personalização) e `fabrica.css`.
- Botões: "Pular animação" (ou Esc), "Personalizar" e "Ocultar ajudantes" (canto superior direito), "Rever animação" e
  "Personalizar" (barra lateral, em Ajudantes) e o × do diálogo.
  Clicar no diálogo mostra o texto inteiro na hora.
- Os ajudantes somem no Perfil e em telas estreitas (área do conteúdo abaixo de 760 px). Com `prefers-reduced-motion`, a cena é pulada.
- Velocidade da cena: `RITMO` no topo de `animacao.py`.


## Enviar dados do dia (botão no cabeçalho)
Abre um campo para enviar um CSV no formato da submissão do Kaggle (`id,peca_A,peca_B,peca_C,peca_D`, com `id` = `Mxxx_AAAA-MM-DD`
e as probabilidades de 0 a 1). O arquivo é lido por `painel_dados.montar` e passa a valer **só nesta sessão**: alerta das 5
máquinas, fila de prioridades, tanques, filtros, exportação, risco da aba Máquinas e o top 5 que o Floco anuncia. Indicadores
de validação (AUC-PR, recall, curvas, replay e simulador) continuam os da validação temporal. "Voltar à previsão padrão" desfaz.
Nada é gravado no repositório: ao sair ou recarregar a página, volta a previsão padrão (`dados/previsao.csv`).

## Animação de entrada das abas
Ao abrir uma aba, os blocos surgem em cascata. Nas páginas em iframe (`frontend/entrada.js`): cada bloco sobe e aparece quando
chega à tela, e cartões com barra colorida na lateral (o aviso "Atenção", os indicadores, os cartões dos gráficos) nascem da barra
e deslizam para a direita, com o conteúdo vindo atrás. Nas páginas nativas (Máquinas, Dados tratados, Simulador, Perfil) e na
parte da barra lateral que muda de aba para aba, `app.py` (`entrada_da_aba`) emite o CSS de entrada só na primeira execução da
aba. Mexer num filtro ou trocar de máquina não repete a animação; na primeira entrada ela espera a cena do Beto terminar.

## Simulador: controles na página
Cenário pronto, período, cenários de Monte Carlo, peças e linhas aparecem num cartão no topo da página e também na barra lateral;
os dois conjuntos ficam sincronizados (chaves `*_pg` copiadas para as da barra lateral).

## Perfil: personalização do operário
A aba Perfil tem o mesmo painel de personalização do botão "Personalizar", embutido na página (o motor da animação monta o painel
no marcador `.mby-perso-inline`). "Salvar" grava no navegador; "Desfazer" volta ao último salvo.

## Logo animada (`logo_animado.py`)
Na tela de entrada e no topo da barra lateral. A logo foi **recriada em vetor**: a engrenagem é paramétrica (14 dentes, para girar
inteira); "MaBiYama" e o slogan são contornos da fonte Exo 2 (Black Itálico e SemiBold Itálico, a mais próxima do desenho
original); a bomba, o crescente e as gotas são vetores suaves em quatro tons com gradientes; a água são 4 faixas de curvas
recalculadas a cada quadro. Geometria em `frontend/marca/logo_vetor.json`; animação em `frontend/logo_anim.js`, com física
simples a 60 quadros por segundo:
- a água entra desenhando as faixas e não para de ondular (todas seguem a mesma onda, então as folgas brancas se mantêm);
- a engrenagem cai do céu com gravidade, quica duas vezes, respinga e passa a girar devagar;
- a bomba sobe de dentro da água numa mola amortecida, com respingos, ondas circulares e as gotas saltando; depois boia;
- um brilho atravessa a bomba (e repete a cada ~7 s); o nome entra num corte da esquerda para a direita e o slogan sobe.
Roda num `components.html` com fundo transparente (versão clara ou escura conforme o tema). Com `prefers-reduced-motion`, a logo
aparece parada.
