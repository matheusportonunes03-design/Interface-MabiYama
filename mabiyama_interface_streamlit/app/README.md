# MaBiYama · Painel da Frota (Streamlit)

Versão em Python do painel feito no Lovable: login, **Previsão & Modelagem**, **Análise Exploratória** e **Perfil**.

## Rodar
```bash
pip install -r requirements.txt
python gerar_hash_senha.py          # gera o hash da senha
# copie .streamlit/secrets.toml.exemplo para .streamlit/secrets.toml e cole o email + hash
streamlit run app.py
```

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
- O login usa hashes em `secrets.toml`. No Streamlit Community Cloud, cole o mesmo conteúdo em *Settings → Secrets*.
