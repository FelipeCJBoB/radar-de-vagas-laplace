"""Pontuação 0-100 de compatibilidade da vaga com o perfil (regras explícitas, auditáveis)."""
from __future__ import annotations

from datetime import date

from .models import Job
from .text import any_term, normalize
from .validar import ESCALA, nivel_na_escala

ROTULO = {"junior": "júnior/estágio", "pleno": "pleno", "senior": "sênior/liderança"}


def _pontos_nivel(nivel_vaga: str, cfg: dict) -> tuple[int, str]:
    """Pontos pela distância entre o nível da vaga e o nível que a pessoa busca.

    Antes eram constantes de quem busca vaga júnior (+25 júnior, +8 pleno, -30
    sênior), o que invertia o ranking para qualquer outro nível. Agora o degrau do
    alvo vale +25, o vizinho +8 e dois ou mais degraus de distância -30. Para o alvo
    júnior o resultado é idêntico ao antigo. Níveis em `alvo.aceita_niveis` nunca
    ficam abaixo do vizinho. Vaga sem nível detectado vale +5.
    """
    alvo = cfg.get("_nivel_alvo")
    if nivel_vaga not in ESCALA or alvo not in ESCALA:
        return 5, ""
    dist = abs(ESCALA.index(nivel_vaga) - ESCALA.index(alvo))
    pts = 25 if dist == 0 else 8 if dist == 1 else -30
    aceitos = {nivel_na_escala(n) for n in ((cfg.get("alvo") or {}).get("aceita_niveis") or [])}
    if nivel_vaga in aceitos:
        pts = max(pts, 8)
    return pts, f"{ROTULO[nivel_vaga]} ({pts:+d})"


def score_job(job: Job, cfg: dict, cat_points: dict, today: date) -> tuple[int, list[str]]:
    s = 0
    reasons: list[str] = []
    cats = cfg["categorias"]

    pts = cat_points.get(job.category, 0)
    if job.category:
        s += pts
        reasons.append(f"{cats[job.category]['nome']} (+{pts})")
        # Bônus por categoria. Existe porque só "prioridade" não bastava: o acerto de
        # título vale 30 para qualquer categoria, então uma vaga júnior de suporte na
        # região passava à frente de uma vaga de dados, que é o alvo. O bônus pode ser
        # negativo para categorias de reserva, que devem aparecer sem disputar o topo.
        prio = cats[job.category].get("prioridade", 4)
        bonus = int(cats[job.category].get("bonus", max(0, 5 - prio)))
        s += bonus
        if bonus:
            reasons.append(f"prioridade da categoria ({bonus:+d})")
    extras = [c for c in job.categories if c != job.category]
    if extras:
        s += 3 * len(extras)
        reasons.append("também: " + ", ".join(cats[c]["nome"] for c in extras) + f" (+{3 * len(extras)})")

    pts_nivel, motivo_nivel = _pontos_nivel(job.seniority, cfg)
    s += pts_nivel
    if motivo_nivel:
        reasons.append(motivo_nivel)

    if job.matched_city:
        s += 20
        reasons.append(f"{job.matched_city} (+20)")
    elif job.workplace == "remote" and cfg.get("_remoto") == "preferir":
        s += 12
        reasons.append("remoto (+12)")

    hay = normalize(f"{job.title} | {job.description}")
    skills = any_term(hay, cfg.get("habilidades", []))
    if skills:
        bonus = min(3 * len(skills), 18)
        s += bonus
        reasons.append("skills: " + ", ".join(skills[:6]) + f" (+{bonus})")

    if job.date_posted:
        try:
            age = (today - date.fromisoformat(job.date_posted[:10])).days
            if age <= 7:
                s += 5
                reasons.append("publicada há ≤7 dias (+5)")
        except ValueError:
            pass

    return max(0, min(100, s)), reasons
