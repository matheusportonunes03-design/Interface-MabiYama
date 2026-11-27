"""Versiona apenas os resultados do ETL no repositório da interface."""

from base64 import b64decode, b64encode
import json
from pathlib import Path

from github import Auth, Github, GithubException, InputGitTreeElement

from preparar_dados import TABELAS_COMPLETAS

REPOSITORIO = "matheusportonunes03-design/Interface-MabiYama"
URL_REPOSITORIO = f"https://github.com/{REPOSITORIO}"
BRANCH = "main"
DIRETORIO = "dados/tratados"
ARQUIVOS_TRATADOS = [*(f"{nome}.parquet" for nome in TABELAS_COMPLETAS), "relatorio_qualidade.md"]
LIMITE_GITHUB = 100 * 1024 * 1024


class PublicacaoConcorrente(RuntimeError):
    """O branch avançou desde o início da publicação."""


class BaseMuitoGrande(ValueError):
    """O resultado do ETL excede o limite de arquivo do GitHub."""


class RepositorioBases:
    def __init__(self, token: str):
        self.github = Github(auth=Auth.Token(token), timeout=30)
        self.repo = self.github.get_repo(REPOSITORIO)

    def versao_atual(self) -> str:
        return self.repo.get_git_ref(f"heads/{BRANCH}").object.sha

    def publicar(self, tratados: Path, versao_anterior: str) -> str:
        """Cria um commit para o lote e avança a referência sem force push."""
        arquivos = [tratados / nome for nome in ARQUIVOS_TRATADOS]
        for arquivo in arquivos:
            if arquivo.stat().st_size > LIMITE_GITHUB:
                raise BaseMuitoGrande(f"{arquivo.name} ultrapassa o limite de 100 MiB por arquivo do GitHub.")

        ref = self.repo.get_git_ref(f"heads/{BRANCH}")
        mensagem_conflito = "A versão do GitHub mudou durante o envio. Confira a versão atual e tente novamente."
        if ref.object.sha != versao_anterior:
            raise PublicacaoConcorrente(mensagem_conflito)

        pai = self.repo.get_git_commit(versao_anterior)
        entradas = []
        for arquivo in arquivos:
            conteudo = b64encode(arquivo.read_bytes()).decode("ascii")
            blob = self.repo.create_git_blob(conteudo, "base64")
            entradas.append(InputGitTreeElement(f"{DIRETORIO}/{arquivo.name}", "100644", "blob", sha=blob.sha))
        arvore = self.repo.create_git_tree(entradas, base_tree=pai.tree)
        if arvore.sha == pai.tree.sha:
            return pai.sha

        commit = self.repo.create_git_commit("Atualiza as bases tratadas pelo painel", arvore, [pai])
        try:
            ref.edit(commit.sha, force=False)
        except GithubException as erro:
            if erro.status in (409, 422) and self.versao_atual() != versao_anterior:
                raise PublicacaoConcorrente(mensagem_conflito) from erro
            raise
        return commit.sha

    def baixar(self, versao: str, destino: Path):
        """Lê todos os arquivos do mesmo commit, mesmo se o branch avançar."""
        entradas = self.repo.get_contents(DIRETORIO, ref=versao)
        arquivos = {entrada.name: entrada.sha for entrada in entradas if entrada.type == "file"}
        for nome in ARQUIVOS_TRATADOS:
            blob = self.repo.get_git_blob(arquivos[nome])
            (destino / nome).write_bytes(b64decode(blob.content))

    def previsao_m07(self, versao: str) -> tuple[bytes, dict] | None:
        """Só entrega o CSV quando o manifesto aponta para a árvore atual das bases."""
        dados = {item.name: item.sha for item in self.repo.get_contents("dados", ref=versao)}
        if not {"tratados", "previsao_m07.json", "previsao_m07.csv"} <= dados.keys():
            return None
        manifesto = json.loads(b64decode(self.repo.get_git_blob(dados["previsao_m07.json"]).content))
        if manifesto["arvore_bases"] != dados["tratados"]:
            return None
        return b64decode(self.repo.get_git_blob(dados["previsao_m07.csv"]).content), manifesto
