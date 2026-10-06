"""Avaliação de compatibilidade vaga × perfil, independente de provedor.

O que muda entre Gemini e Claude é só como a chamada é feita e como o erro se
chama. O prompt, o esquema de saída, o disjuntor de falhas e o tratamento da
resposta são os mesmos, e vivem aqui.

A avaliação é sempre opcional: qualquer falha vira um motivo legível que sobe para
o relatório, e a rodada segue sem as notas.
"""
from __future__ import annotations

import json
import logging
import time

from .config import env
from .models import Job
from .providers import DISPONIVEIS, ORDEM_AUTO

log = logging.getLogger("vagas.ia")

FALHAS_SEGUIDAS_ATE_DESISTIR = 3
# Espera entre as tentativas da MESMA vaga. O 503 "high demand" do nível gratuito
# do Gemini é rotina em horário de pico e passa em segundos; sem retentar, uma
# oscilação de trinta segundos custaria a avaliação da rodada inteira.
ESPERA_ENTRE_TENTATIVAS = (2.0, 6.0, 15.0)

def montar_system(contexto: dict | None = None) -> str:
    """Prompt de sistema montado a partir de quem busca, e não de um perfil fixo.

    `contexto` vem de `validar.contexto_ia`: áreas (categorias do config, por
    prioridade), nível-alvo e idioma da resposta. Tudo o que descreve a PESSOA
    (formação, tecnologias, projetos) vem do perfil, que é anexado depois deste texto.
    """
    ctx = contexto or {}
    areas = ", ".join(ctx.get("areas") or []) or "a área de atuação do candidato"
    nivel = ctx.get("nivel") or "compatível com a experiência do candidato"
    idioma = ctx.get("idioma") or "pt-BR"
    return (
        f"Você é um recrutador experiente nas áreas de {areas}, no Brasil.\n"
        "Avalie a compatibilidade entre a VAGA e o CANDIDATO abaixo. "
        f"O candidato busca uma posição de nível {nivel}.\n\n"
        f"Critérios, em ordem: (1) senioridade compatível com o nível {nivel}; (2) aderência "
        "às habilidades, à formação e à experiência descritas no perfil; (3) requisitos "
        "eliminatórios (anos de experiência exigidos, idiomas, formação concluída, registro "
        "profissional); (4) local/remoto.\n"
        f"Seja direto e específico. Escreva o comentário e o alerta em {idioma}. "
        "Responda apenas com o JSON pedido.\n\n"
        "=== CANDIDATO ===\n"
    )


def escolher_provedor(cfg: dict) -> str | None:
    """Nome do provedor a usar, ou None se nenhum estiver configurado."""
    escolha = str(cfg.get("provedor", "auto")).lower()
    if escolha in ("nenhum", "none", "off", "false"):
        return None
    if escolha in DISPONIVEIS:
        return escolha if env(DISPONIVEIS[escolha].ENV_VAR) else None
    return next((n for n in ORDEM_AUTO if env(DISPONIVEIS[n].ENV_VAR)), None)


def _job_text(job: Job) -> str:
    desc = (job.description or "").strip()
    if len(desc) > 5000:
        desc = desc[:5000] + " […]"
    return (f"=== VAGA ===\nTítulo: {job.title}\nEmpresa: {job.company or '(não informada)'}\n"
            f"Local: {job.location or '-'} | Modalidade: {job.workplace} | Fonte: {job.source}\n"
            f"Senioridade detectada por regra: {job.seniority}\n\n"
            f"Descrição:\n{desc or '(sem descrição disponível)'}")


def _aplicar(job: Job, bruto: str) -> bool:
    """Escreve a nota na vaga. False se a resposta não veio utilizável."""
    try:
        data = json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        log.warning("resposta não-JSON para '%s'", job.title)
        return False
    try:
        job.fit = max(0, min(10, int(data.get("compatibilidade", 0))))
    except (TypeError, ValueError):
        log.warning("nota fora do formato para '%s'", job.title)
        return False
    nota = (data.get("comentario") or "").strip()
    alerta = (data.get("alerta") or "").strip()
    job.fit_note = nota + (f" ⚠ {alerta}" if alerta else "")
    return True


def enrich(jobs: list[Job], profile: str, cfg: dict) -> tuple[int, str | None]:
    """Avalia até `max_vagas` vagas. Devolve (quantas avaliou, motivo da falha).

    Desiste depois de algumas falhas seguidas: saldo zerado ou chave inválida valem
    para todas as vagas, e insistir só gasta tempo da rodada.
    """
    nome = escolher_provedor(cfg)
    if not nome:
        return 0, None
    prov = DISPONIVEIS[nome]

    try:
        cliente = prov.criar_cliente(cfg)
    except ImportError:
        log.warning("pacote do provedor %s não instalado", prov.NOME)
        return 0, f"pacote do provedor {prov.NOME} não instalado"
    except Exception as e:  # noqa: BLE001
        return 0, f"não foi possível iniciar {prov.NOME}: {e}"[:200]

    limite = int(cfg.get("max_vagas", 25))
    alvo = jobs[:limite]
    # o nível gratuito limita por minuto; espaçar evita transformar a rodada
    # inteira numa sequência de 429
    intervalo = 60.0 / prov.rpm(cfg) if prov.rpm(cfg) > 0 else 0.0
    system = montar_system(cfg.get("_contexto")) + profile
    log.info("avaliando %d vaga(s) com %s%s", len(alvo), prov.NOME,
             f" (1 a cada {intervalo:.1f}s)" if intervalo else "")

    # `get(..., padrão)` e não `or`: lista vazia é um valor legítimo, significa
    # "não retente", e com `or` ela cairia silenciosamente no padrão
    esperas = list(cfg.get("esperas_tentativa", ESPERA_ENTRE_TENTATIVAS))
    done, seguidas, ultimo_erro, desistir = 0, 0, None, False

    for i, job in enumerate(alvo):
        if desistir:
            break
        if intervalo and i:
            time.sleep(intervalo)

        bruto = None
        for tentativa in range(len(esperas) + 1):
            try:
                bruto = prov.avaliar(cliente, system, _job_text(job), cfg)
                break
            except Exception as e:  # noqa: BLE001
                motivo, fatal = prov.classificar_erro(e)
                ultimo_erro = f"{prov.NOME}: {motivo}"[:200]
                if fatal:
                    log.error("avaliação por IA interrompida: %s", ultimo_erro)
                    desistir = True
                    break
                if tentativa < len(esperas):
                    espera = esperas[tentativa]
                    log.warning("%s — nova tentativa em %.0fs", ultimo_erro, espera)
                    time.sleep(espera)
                    continue
                # esgotou as tentativas desta vaga: agora sim conta para o disjuntor
                seguidas += 1
                log.warning("%s (%d vaga[s] seguida[s] sem resposta)", ultimo_erro, seguidas)
                if seguidas >= FALHAS_SEGUIDAS_ATE_DESISTIR:
                    log.error("avaliação por IA abortada após %d vagas seguidas sem resposta", seguidas)
                    desistir = True

        if bruto is not None and _aplicar(job, bruto):
            done += 1
            seguidas = 0

    log.info("%s: %d vaga(s) avaliada(s)", prov.NOME, done)
    return done, (ultimo_erro if done == 0 else None)
