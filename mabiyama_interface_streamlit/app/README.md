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
| previsao.csv | previsão no formato da submissão (hoje a y01, Kaggle 0,69146). Pode ser trocada pelo botão "Enviar dados do dia". |
| validacao.csv | escores fora da amostra da sub 37, rodada nas bases tratadas, nas 3 janelas de validação temporal |
| importancia.csv | importância das variáveis do ExtraTrees "hat" da sub 37, treinado nas bases tratadas |

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

`dados/eda/` traz os 23 gráficos do notebook da Etapa 3 (WebP) e `graficos.json`, com título, tema e o parágrafo de
insight de cada um. Para trocar um gráfico, substitua o `.webp` com o mesmo nome; para mudar o texto, edite o JSON.
