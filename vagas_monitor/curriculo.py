"""Do currículo à proposta de configuração.

Três passos, todos testáveis sem rede:

1. `ler_texto`: lê o currículo (.txt, .md, .docx ou .pdf).
2. `anonimizar` (módulo à parte): tira os dados pessoais antes de qualquer envio.
3. `propor`: pede a uma IA uma proposta ESTRUTURADA (ocupações, ferramentas, nível, áreas
   com papel de alvo, adjacente ou ponte, termos de busca, homônimos a excluir) e a valida.

A IA só PROPÕE. O resultado é um conjunto de arquivos editáveis que a pessoa revisa, e a
calibração com vagas reais mede se funcionou. Campo sem base no currículo fica vazio:
inventar uma experiência que a pessoa não tem seria o pior erro possível aqui.
"""
from __future__ import annotations

import json
import re
import time
import zipfile
from pathlib import Path

from . import areas
from .validar import NIVEIS, normalizar_nivel

PAPEIS = areas.PAPEIS


# --------------------------------------------------------------------------- leitura
def ler_texto(caminho: str | Path) -> str:
    """Texto do currículo. PDF exige `pypdf`; se faltar, a mensagem diz como seguir."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"currículo não encontrado: {p}")
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".text", ""):
        for cod in ("utf-8", "cp1252", "latin-1"):
            try:
                return p.read_text(encoding=cod)
            except UnicodeDecodeError:
                continue
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab/>", "\t", xml)
        texto = "".join(a or b for a, b in re.findall(r"<w:t[^>]*>([^<]*)</w:t>|(\n)", xml))
        return (texto.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&apos;", "'"))
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError("para ler PDF instale o pypdf (pip install pypdf) ou salve o currículo como "
                               ".txt ou .docx") from e
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    raise ValueError(f"formato '{ext}' não suportado. Use .txt, .md, .docx ou .pdf.")


# --------------------------------------------------------------------------- proposta
def _lista(desc: str):
    return {"type": "array", "items": {"type": "string"}, "description": desc}


PROPOSTA_SCHEMA = {
    "type": "object",
    "properties": {
        "perfil_md": {"type": "string", "description": "Texto do perfil profissional em Markdown, em terceira "
                      "pessoa neutra, SÓ com o que consta no currículo, sem dados pessoais."},
        "nivel_sugerido": {"type": "string", "enum": list(NIVEIS)},
        "ocupacoes": {"type": "array", "items": {"type": "object", "properties": {
            "cargo": {"type": "string"}, "tipo_de_empresa": {"type": "string"},
            "anos": {"type": "number"}, "funcoes": {"type": "string"}},
            "required": ["cargo", "tipo_de_empresa", "anos", "funcoes"]}},
        "formacao": _lista("cursos e níveis de formação, com situação (concluído ou em andamento)"),
        "ferramentas": _lista("ferramentas, tecnologias e sistemas que a pessoa efetivamente usou"),
        "registros": _lista("registros e certificações profissionais (CRC, COREN, OAB, CREA, NR...)"),
        "areas": {"type": "array", "items": {"type": "object", "properties": {
            "slug": {"type": "string", "description": "slug de um pack do catálogo"},
            "papel": {"type": "string", "enum": list(PAPEIS)},
            "motivo": {"type": "string"}}, "required": ["slug", "papel", "motivo"]}},
        "categorias_extras": {"type": "array", "description": "áreas que NÃO estão no catálogo",
                              "items": {"type": "object", "properties": {
                                  "nome": {"type": "string"}, "papel": {"type": "string", "enum": list(PAPEIS)},
                                  "titulo": _lista("expressões de título de vaga, específicas"),
                                  "descricao": _lista("expressões de descrição de vaga")},
                                  "required": ["nome", "papel", "titulo", "descricao"]}},
        "termos_busca": _lista("2 a 6 termos largos para as buscas"),
        "excluir_titulo": _lista("homônimos: expressões de título que NÃO interessam"),
        "habilidades": _lista("habilidades da pessoa que valem pontos na pontuação"),
        "avisos": _lista("dúvidas e lacunas do currículo que a pessoa deve conferir"),
    },
    "required": ["perfil_md", "nivel_sugerido", "ocupacoes", "formacao", "ferramentas", "registros", "areas",
                 "categorias_extras", "termos_busca", "excluir_titulo", "habilidades", "avisos"],
}


def catalogo_texto() -> str:
    return "\n".join(f"- {slug}: {p['nome']} ({p['resumo'].split('.')[0]})" for slug, p in areas.listar().items())


def montar_system() -> str:
    return (
        "Você é um orientador de carreira no mercado de trabalho brasileiro. Receba o CURRÍCULO (com dados "
        "pessoais já removidos) e o OBJETIVO da pessoa e proponha a configuração de um monitor de vagas.\n\n"
        "Regras:\n"
        "1. Use SOMENTE o que está no currículo e no objetivo. Não invente experiência, ferramenta, registro "
        "nem tempo. Sem informação, deixe o campo vazio e registre a dúvida em `avisos`.\n"
        "2. `areas`: escolha slugs do CATÁLOGO abaixo e dê a cada um um papel. `alvo` é o que a pessoa QUER "
        "(vem do objetivo). `ponte` é o que a experiência atual sustenta mas não é o desejo. `adjacente` é "
        "vizinho legítimo. Se uma área não existir no catálogo, use `categorias_extras`.\n"
        "3. Termos de título: expressões COMPLETAS e específicas ('analista financeiro'), nunca palavras soltas "
        "e ambíguas ('financeiro', 'fiscal', 'segurança').\n"
        "4. `excluir_titulo`: homônimos que enganariam a busca ('fiscal de loja' para quem busca a área fiscal).\n"
        "5. `nivel_sugerido`: o do OBJETIVO, se a pessoa disse; senão, o que o currículo sustenta.\n"
        "6. `perfil_md`: formato de perfil profissional (objetivo, formação, experiência, habilidades, registros, "
        "idiomas), sem nome, contato nem endereço.\n\n"
        "CATÁLOGO de áreas:\n" + catalogo_texto() + "\n"
    )


def montar_texto(curriculo: str, objetivo: str, nivel: str | None = None) -> str:
    return (f"=== OBJETIVO ===\n{objetivo.strip() or '(não informado)'}\n"
            f"Nível desejado: {nivel or '(não informado)'}\n\n=== CURRÍCULO ===\n{curriculo.strip()}")


class PropostaInvalida(ValueError):
    pass


def validar_proposta(dados: dict) -> dict:
    """Confere o formato e separa o que o catálogo não conhece. Não inventa nada."""
    if not isinstance(dados, dict):
        raise PropostaInvalida("a resposta da IA não é um objeto JSON")
    catalogo = set(areas.listar())
    boas, fora = [], []
    for a in dados.get("areas") or []:
        if not isinstance(a, dict) or a.get("papel") not in PAPEIS:
            continue
        (boas if a.get("slug") in catalogo else fora).append(a)
    extras = [e for e in dados.get("categorias_extras") or []
              if isinstance(e, dict) and e.get("nome") and e.get("titulo") and e.get("papel") in PAPEIS]
    if not boas and not extras:
        raise PropostaInvalida("a IA não indicou nenhuma área do catálogo nem categoria nova")
    nivel = normalizar_nivel(dados.get("nivel_sugerido"))
    out = dict(dados)
    out.update(areas=boas, categorias_extras=extras, nivel_sugerido=nivel or "",
               areas_fora_do_catalogo=[a.get("slug") for a in fora])
    for campo in ("termos_busca", "excluir_titulo", "habilidades", "avisos", "ferramentas", "formacao", "registros"):
        out[campo] = [str(x).strip() for x in dados.get(campo) or [] if str(x).strip()]
    return out


def propor(curriculo_anonimizado: str, objetivo: str, cfg_avaliacao: dict, nivel: str | None = None,
           prov=None, cliente=None, esperas=(2.0, 6.0, 15.0), dormir=time.sleep) -> dict:
    """Pede a proposta à IA configurada. `prov` e `cliente` existem para os testes."""
    from .enrich import escolher_provedor
    from .providers import DISPONIVEIS

    if prov is None:
        nome = escolher_provedor(cfg_avaliacao)
        if not nome:
            raise RuntimeError("nenhuma chave de IA encontrada (GEMINI_API_KEY ou ANTHROPIC_API_KEY). "
                               "Use `init --manual`, que não precisa de IA.")
        prov = DISPONIVEIS[nome]
    cliente = cliente or prov.criar_cliente(cfg_avaliacao)
    system, texto = montar_system(), montar_texto(curriculo_anonimizado, objetivo, nivel)
    ultimo = None
    for tentativa in range(len(esperas) + 1):
        try:
            bruto = prov.avaliar(cliente, system, texto, cfg_avaliacao, schema=PROPOSTA_SCHEMA, max_tokens=6000)
            return validar_proposta(json.loads(bruto))
        except (json.JSONDecodeError, PropostaInvalida) as e:
            ultimo = f"resposta inválida da IA: {e}"
        except Exception as e:  # noqa: BLE001
            motivo, fatal = prov.classificar_erro(e)
            ultimo = f"{prov.NOME}: {motivo}"
            if fatal:
                break
        if tentativa < len(esperas):
            dormir(esperas[tentativa])
    raise RuntimeError(ultimo or "falha ao obter a proposta da IA")
