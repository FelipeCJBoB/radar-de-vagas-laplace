"""Remoção local de dados pessoais do currículo, ANTES de qualquer envio a uma IA externa.

O Gemini gratuito pode usar o texto enviado para treinar, e um currículo traz nome, CPF,
telefone, e-mail e endereço. Nada disso ajuda a descobrir a área e as capacidades da
pessoa, então sai aqui, na máquina dela, por padrão e com o resultado à mostra para ela
aprovar. É redução de risco, não garantia: o texto resultante ainda pode conter nomes
de empresas, escolas e projetos, que a pessoa pode ocultar com `ocultar=[...]`.
"""
from __future__ import annotations

import re
from collections import Counter

# (rótulo, regex, substituição). A ordem importa: CNPJ e CPF antes do telefone para que
# uma sequência de dígitos de documento não seja lida como telefone.
_PADROES = [
    ("e-mail", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[e-mail removido]"),
    ("link", re.compile(r"(?:https?://|www\.)\S+|(?:linkedin|github|instagram|facebook|twitter|x)\.com/\S+", re.I),
     "[link removido]"),
    ("CNPJ", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ removido]"),
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b(?<=CPF)[: ]+\d{11}\b"), "[CPF removido]"),
    ("telefone", re.compile(r"(?<![\w/])(?:\+?55[ .-]?)?\(?\d{2}\)?[ .-]?9?\d{4}[ .-]?\d{4}(?!\d)"), "[telefone removido]"),
    ("CEP", re.compile(r"\b\d{5}-\d{3}\b"), "[CEP removido]"),
    ("RG", re.compile(r"\bRG\b[: ]*[\d.\-xX]{6,}", re.I), "[RG removido]"),
    ("nascimento", re.compile(r"\b(?:data de nascimento|nascimento|nascido(?:\(a\))? em|idade)\b\s*[:\-]?\s*[\d/.\- ]+(?:anos)?", re.I),
     "[nascimento removido]"),
    ("endereço", re.compile(r"\b(?:rua|r\.|avenida|av\.|travessa|alameda|rodovia|estrada|praça)\s[^\n,;|]{3,}(?:,\s*\d+[^\n]*)?", re.I),
     "[endereço removido]"),
]
_ROTULO_LINHA = re.compile(r"^\s*(?:endere[çc]o|telefone|celular|whatsapp|e-?mail|cpf|rg)\s*[:\-].*$", re.I | re.M)
_PALAVRAS_DE_CARGO = {"analista", "desenvolvedor", "engenheiro", "assistente", "auxiliar", "curriculo", "currículo",
                      "resumo", "objetivo", "perfil", "experiência", "formação", "contato", "dados", "pessoais"}


def _parece_nome(linha: str) -> bool:
    palavras = linha.strip().split()
    if not 2 <= len(palavras) <= 6 or any(any(c.isdigit() for c in p) for p in palavras):
        return False
    if any(p.lower().strip(".,:;") in _PALAVRAS_DE_CARGO for p in palavras):
        return False
    if not all(p.replace("-", "").replace("'", "").isalpha() for p in palavras):
        return False
    return all(p[0].isupper() or p.lower() in {"de", "da", "do", "dos", "das", "e"} for p in palavras)


def anonimizar(texto: str, nomes: list[str] | None = None, ocultar: list[str] | None = None) -> tuple[str, dict]:
    """Devolve (texto sem dados pessoais, contagem do que foi removido por tipo).

    `nomes`: o nome da pessoa, por extenso, para troca global. Sem isso, a primeira linha é
    tratada como nome se tiver cara de nome. `ocultar`: empregadores, escolas etc.
    """
    achados: Counter = Counter()

    def trocar(rx, marca, rotulo, s):
        s, n = rx.subn(marca, s)
        achados[rotulo] += n
        return s

    for rotulo, rx, marca in _PADROES:
        texto = trocar(rx, marca, rotulo, texto)
    texto = trocar(_ROTULO_LINHA, "[dado de contato removido]", "linha de contato", texto)

    candidatos = list(nomes or [])
    if not candidatos:
        primeira = next((ln for ln in texto.splitlines() if ln.strip()), "")
        if _parece_nome(primeira):
            candidatos.append(primeira.strip())
    for nome in sorted(set(candidatos), key=len, reverse=True):
        partes = [nome] + [p for p in nome.split() if len(p) >= 4 and p.lower() not in {"silva", "santos", "souza"}]
        for parte in partes:
            rx = re.compile(rf"\b{re.escape(parte)}\b", re.I)
            texto = trocar(rx, "[nome]", "nome", texto)
    for termo in ocultar or []:
        if termo.strip():
            texto = trocar(re.compile(re.escape(termo.strip()), re.I), "[oculto]", "ocultado", texto)
    return texto, {k: v for k, v in achados.items() if v}


def resumo(achados: dict) -> str:
    if not achados:
        return "nenhum dado pessoal reconhecido (confira o texto mesmo assim)"
    return ", ".join(f"{n} {k}" for k, n in achados.items())
