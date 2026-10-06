"""Provedor Anthropic, via API da Claude.

Pré-paga: exige crédito em console.anthropic.com. A assinatura do Claude.ai não
cobre a API. Cerca de 30 centavos de dólar por rodada com o modelo padrão.
"""
from __future__ import annotations

import logging

NOME = "Claude"
ENV_VAR = "ANTHROPIC_API_KEY"
MODELO_PADRAO = "claude-opus-5"
RPM_PADRAO = 0  # sem espaçamento: o limite da conta paga é bem acima do volume daqui

log = logging.getLogger("vagas.anthropic")

SCHEMA = {
    "type": "object",
    "properties": {
        "compatibilidade": {"type": "integer", "minimum": 0, "maximum": 10,
                            "description": "0 = nada a ver; 10 = candidatura óbvia para o perfil"},
        "comentario": {"type": "string",
                       "description": "1-2 frases: por que combina (ou não) e o que destacar"},
        "alerta": {"type": "string",
                   "description": "Requisito eliminatório que o candidato não atende. Vazio se não houver."},
    },
    "required": ["compatibilidade", "comentario", "alerta"],
    "additionalProperties": False,
}


def criar_cliente(cfg: dict):
    import anthropic

    return anthropic.Anthropic()


def _estrito(schema):
    """A saída estruturada da Anthropic exige `additionalProperties: false` em todo objeto."""
    if isinstance(schema, dict):
        out = {k: _estrito(v) for k, v in schema.items()}
        if out.get("type") == "object":
            out.setdefault("additionalProperties", False)
        return out
    if isinstance(schema, list):
        return [_estrito(v) for v in schema]
    return schema


def avaliar(cliente, system: str, texto: str, cfg: dict, schema: dict | None = None,
            max_tokens: int = 800) -> str:
    """`schema` e `max_tokens` permitem outros usos além da nota (extração do currículo)."""
    a = (cfg.get("anthropic") or {})
    resp = cliente.beta.messages.create(
        model=a.get("modelo", MODELO_PADRAO),
        max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        # o prompt do sistema é idêntico em todas as vagas da rodada: cacheá-lo
        # derruba o custo de entrada das 24 chamadas seguintes
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": texto}],
        output_config={"effort": a.get("esforco", "low"),
                       "format": {"type": "json_schema", "schema": _estrito(schema) if schema else SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        raise ValueError("a avaliação foi recusada por filtro de segurança")
    return next((b.text for b in resp.content if b.type == "text"), "")


def classificar_erro(exc: Exception) -> tuple[str, bool]:
    import anthropic

    if isinstance(exc, anthropic.AuthenticationError):
        return ("chave da Anthropic inválida ou revogada", True)
    if isinstance(exc, anthropic.RateLimitError):
        return ("limite de requisições da API", False)
    if isinstance(exc, anthropic.APIStatusError):
        msg = str(getattr(exc, "message", exc))
        if exc.status_code == 400 and "credit balance" in msg:
            return ("conta sem crédito em console.anthropic.com", True)
        return (f"HTTP {exc.status_code}: {msg}", False)
    if isinstance(exc, anthropic.APIConnectionError):
        return (f"falha de rede: {exc}", False)
    return (f"{type(exc).__name__}: {exc}", False)


def rpm(cfg: dict) -> int:
    return int((cfg.get("anthropic") or {}).get("rpm", RPM_PADRAO))
