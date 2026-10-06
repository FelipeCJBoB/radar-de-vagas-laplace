"""Escrita do config.yaml com comentários, a partir de um dicionário.

O `init` precisa gravar um arquivo que a pessoa vá ler e editar à mão. `yaml.safe_dump`
puro perde todo comentário, então cada seção de topo recebe aqui o seu cabeçalho
explicativo. Chaves desconhecidas são preservadas (no fim), para o `init` poder rodar
de novo sem apagar o que a pessoa acrescentou.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ORDEM = ["perfil", "intervalo_dias", "lookback_days", "first_run_lookback_days", "estado", "regiao", "alvo",
         "termos_busca", "categorias", "senioridade", "excluir_titulo", "habilidades", "fontes", "relatorio",
         "notificacoes", "avaliacao", "modelo"]

COMENTARIOS = {
    "perfil": "Seu resumo profissional, usado pela avaliação por IA (a variável PERFIL_MD tem precedência).",
    "intervalo_dias": "Cadência: executa se passaram >= N dias da última execução.",
    "estado": "Memória entre rodadas (state/seen.json).",
    "regiao": ("ONDE você busca. estados: siglas. base: cidade e UF. alcance: cidade | regiao_imediata | estado | lista.\n"
               "remoto: nao | aceitar | preferir | somente."),
    "alvo": "O QUE você busca. nivel: estagio | junior | pleno | senior | lideranca.",
    "termos_busca": "Termos enviados ao LinkedIn e ao Indeed. Cada um custa tempo de rodada: poucos e largos.",
    "categorias": ("Categorias (prioridade 1 = a mais desejada). titulo: termos que classificam pelo TÍTULO (30 pts);\n"
                   "descricao: 3 termos distintos classificam pela DESCRIÇÃO (12 pts); bonus: soma na nota (negativo = ponte);\n"
                   "excluir_titulo (dentro da categoria): homônimos que NÃO entram nesta categoria."),
    "senioridade": "Termos que indicam o nível da vaga, detectados no título.",
    "excluir_titulo": "Títulos que NUNCA interessam, em qualquer categoria.",
    "habilidades": "Suas habilidades: cada acerto soma pontos (máx. +18).",
    "fontes": "Fontes de vagas.",
    "relatorio": "Relatórios e painel. url_publica vazio = sem link nas notificações.",
    "notificacoes": "Canais. auto = envia se as variáveis de ambiente existirem.",
    "avaliacao": "Avaliação por IA (opcional): nota de 0 a 10 e comentário por vaga.",
    "modelo": "repositorio: dono/nome do repositório-modelo; o `doctor` avisa se há versão nova.",
}

CABECALHO = """# ============================================================
#  Radar de Vagas Laplace — configuração
#  Gerado por `python -m vagas_monitor init`. Edite à vontade; guia/04-personalizar.md explica cada seção.
# ============================================================
"""


class _Dumper(yaml.SafeDumper):
    """Mapeamentos em bloco; listas de valores simples em linha (os termos ficam legíveis)."""


def _sequencia(dumper, dados):
    simples = all(isinstance(x, (str, int, float, bool)) or x is None for x in dados)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", dados, flow_style=simples)


_Dumper.add_representer(list, _sequencia)


def _bloco(chave: str, valor) -> str:
    corpo = yaml.dump({chave: valor}, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=110,
                      default_flow_style=False)
    cab = "".join(f"# {linha}\n" for linha in COMENTARIOS.get(chave, "").splitlines())
    return cab + corpo


def escrever_config(cfg: dict, caminho: str | Path) -> None:
    cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    chaves = [k for k in ORDEM if k in cfg] + [k for k in cfg if k not in ORDEM]
    texto = CABECALHO + "\n" + "\n".join(_bloco(k, cfg[k]) for k in chaves)
    Path(caminho).write_text(texto, encoding="utf-8", newline="")
