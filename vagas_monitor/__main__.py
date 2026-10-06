"""CLI: python -m vagas_monitor <comando>"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path


def _setup_logging(verbose: bool) -> None:
    for fluxo in (sys.stdout, sys.stderr):  # Windows: acentos no console (cp1252 vira "S?o Jos?")
        try:
            fluxo.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S",
                        stream=sys.stdout)
    for noisy in ("urllib3", "httpx", "httpcore", "JobSpy", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def cmd_run(a) -> int:
    from .pipeline import run
    from .validar import ConfigInvalida
    try:
        summary = run(force=a.force, dry_run=a.dry_run, notify=not a.no_notify, lookback=a.lookback,
                      config_path=a.config, skip=tuple(a.skip or ()))
    except ConfigInvalida as e:
        print(e)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if summary.get("notify_failed") else 0


def cmd_status(a) -> int:
    from .config import ROOT, load_config
    from .state import State
    cfg = load_config(a.config)
    st = State(ROOT / "state" / "seen.json")
    print(f"última execução : {st.data.get('last_run') or '— (nunca)'}")
    d = st.days_since_last_run()
    if d is not None:
        print(f"há              : {d:.1f} dias (cadência {cfg.get('intervalo_dias', 5)} dias)")
    print(f"próxima rodada  : {'agora' if st.due(int(cfg.get('intervalo_dias', 5))) else 'ainda não'}")
    print(f"vagas conhecidas: {len(st.data['jobs'])}")
    return 0


def cmd_setup_telegram(a) -> int:
    from .config import ROOT, env, load_config
    from .notify import telegram
    load_config(a.config)
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Defina TELEGRAM_BOT_TOKEN no .env primeiro (crie o bot em @BotFather).")
        return 1
    print("Procurando conversas com o bot… (mande qualquer mensagem para ele no Telegram, se ainda não mandou)")
    chats = telegram.discover_chat_id(token)
    if not chats:
        print("Nenhuma conversa encontrada. Envie uma mensagem para o bot e rode de novo.")
        return 1
    for cid, name in chats:
        print(f"  chat_id {cid}  ({name})")
    cid = chats[0][0] if len(chats) == 1 else input("Digite o chat_id a usar: ").strip()
    telegram.write_env(ROOT / ".env", "TELEGRAM_CHAT_ID", cid)
    ok = telegram.send_message(token, cid, "✅ <b>Radar de Vagas</b> conectado. Você receberá o resumo a cada rodada.")
    print("Gravado em .env e mensagem de teste", "enviada." if ok else "FALHOU.")
    return 0 if ok else 1


def cmd_test_notify(a) -> int:
    from .config import env, load_config
    cfg = load_config(a.config)
    cidade = (cfg.get("cidades") or ["Cidade Exemplo"])[0]
    ctx = {"run_date_br": datetime.now().strftime("%d/%m/%Y"), "total": 1, "new_count": 1, "lookback_days": 7,
           "categorias": {"dados": {"nome": "Dados"}}, "report_url": "",
           "jobs": [{"is_new": True, "score": 88, "fit": None, "fit_note": "", "url": "https://example.com",
                     "title": "Vaga de teste", "company": "Empresa Exemplo",
                     "matched_city": cidade, "workplace": "hybrid", "location": cidade,
                     "seniority": "junior", "category": "dados"}]}
    rc = 0
    if env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHAT_ID"):
        from .notify import telegram
        n = telegram.send(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"), ctx)
        print("telegram:", "ok" if n else "FALHOU")
        rc |= int(not n)
    else:
        print("telegram: não configurado (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
    if env("SMTP_USER") and env("SMTP_PASSWORD") and env("EMAIL_TO"):
        from .notify import email_
        ok = email_.send(env("SMTP_HOST", "smtp.gmail.com"), int(env("SMTP_PORT", "465")), env("SMTP_USER"),
                         env("SMTP_PASSWORD"), env("EMAIL_TO"), ctx)
        print("email:", "ok" if ok else "FALHOU")
        rc |= int(not ok)
    else:
        print("email: não configurado (SMTP_USER / SMTP_PASSWORD / EMAIL_TO)")
    return rc


def cmd_check_ia(a) -> int:
    """Faz UMA chamada real e mostra a nota, para validar a chave sem esperar a rodada."""
    from .config import avaliacao_cfg, load_config
    from .enrich import enrich, escolher_provedor
    from .models import Job
    from .providers import DISPONIVEIS

    cfg = load_config(a.config)
    aval = avaliacao_cfg(cfg)
    print("Chaves encontradas no ambiente:")
    for nome, mod in DISPONIVEIS.items():
        from .config import env
        print(f"  {mod.NOME:8s} ({mod.ENV_VAR}): {'sim' if env(mod.ENV_VAR) else 'não'}")
    escolhido = escolher_provedor(aval)
    print(f"Configuração: provedor={aval.get('provedor', 'auto')} -> usaria: {escolhido or 'nenhum'}")
    if not escolhido:
        print("\nNenhum provedor utilizável. Preencha GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env.")
        return 1

    vaga = Job(source="teste", title="Vaga de teste", company="Empresa Exemplo",
               url="https://exemplo/1", location=(cfg.get("cidades") or ["Cidade Exemplo"])[0], workplace="hybrid",
               description="Rotina com as ferramentas da área. Formação em andamento é aceita.")
    vaga.seniority = "junior"
    print(f"\nEnviando 1 vaga de teste para {DISPONIVEIS[escolhido].NOME} …")
    from .validar import contexto_ia
    done, motivo = enrich([vaga], load_profile_safe(cfg),
                          {**aval, "max_vagas": 1, "_contexto": contexto_ia(cfg)})
    if done:
        print(f"OK — nota {vaga.fit}/10\n     {vaga.fit_note}")
        return 0
    print(f"FALHOU — {motivo or 'sem resposta utilizável'}")
    return 1


def load_profile_safe(cfg) -> str:
    from .config import load_profile
    try:
        return load_profile(cfg)
    except OSError:
        return ""


def explicar_titulo(titulo: str, cfg: dict, descricao: str = "") -> list[str]:
    """Linhas que dizem o que o monitor faz com um título e por quê.

    É a ferramenta de calibração: quando uma vaga que você queria não aparece, ou uma
    que não serve aparece, isto mostra QUAL termo decidiu.
    """
    from . import filters
    from .models import Job
    from .text import any_term, normalize

    vaga = Job(source="teste", title=titulo, company="-", url="-", description=descricao)
    linhas = [f"título: {titulo}"]
    bloqueio = any_term(normalize(titulo), cfg.get("excluir_titulo") or [])
    if bloqueio:
        return linhas + [f"  EXCLUÍDA por excluir_titulo: {', '.join(bloqueio)}"]
    primaria, ordem, pontos = filters.classify(vaga, cfg.get("categorias") or {})
    for chave, cat in (cfg.get("categorias") or {}).items():
        so_nela = any_term(normalize(titulo), cat.get("excluir_titulo") or [])
        if so_nela:
            linhas.append(f"  {cat['nome']}: ignorada por excluir_titulo da categoria ({', '.join(so_nela)})")
    if not primaria:
        linhas.append("  SEM CATEGORIA: nenhum termo de título bateu (nem 3 de descrição). A vaga é descartada.")
    for chave in ordem:
        cat = cfg["categorias"][chave]
        por_titulo = any_term(normalize(titulo), cat.get("titulo") or [])
        motivo = f"título: {', '.join(por_titulo)}" if por_titulo else "descrição (3 ou mais termos)"
        marca = " <- principal" if chave == primaria else ""
        linhas.append(f"  {cat['nome']} (+{pontos[chave]}) por {motivo}{marca}")
    linhas.append(f"  nível detectado: {filters.detect_seniority(vaga, cfg.get('senioridade') or {})}")
    cidade = filters.match_city(vaga, cfg.get("cidades") or [], cfg.get("cidades_alias"))
    linhas.append(f"  cidade-alvo no título: {cidade or 'nenhuma'}")
    return linhas


def cmd_classificar(a) -> int:
    from .config import load_config
    cfg = load_config(a.config)
    for titulo in a.titulos:
        for linha in explicar_titulo(titulo, cfg, a.descricao or ""):
            print(linha)
    return 0


def _perguntar(texto: str, padrao: str | None = None, obrigatorio: bool = True) -> str:
    sufixo = f" [{padrao}]" if padrao else ""
    while True:
        r = input(f"{texto}{sufixo}: ").strip() or (padrao or "")
        if r or not obrigatorio:
            return r
        print("  (obrigatório)")


def cmd_init(a) -> int:
    """Configura o monitor para a pessoa: config.yaml, perfil.md e referência de calibração."""
    from . import anonimizar, areas, assistente, calibracao
    from .config import avaliacao_cfg, load_config
    from .enrich import escolher_provedor

    if a.listar_areas:
        for slug, p in areas.listar().items():
            print(f"{slug:30s} [{p['status']:9s}] {p['nome']}")
        return 0

    tty = sys.stdin.isatty() and not a.nao_interativo
    e = {"estados": [x.strip() for x in (a.estado or "").split(",") if x.strip()], "cidade": a.cidade, "uf": a.uf,
         "alcance": a.alcance, "remoto": a.remoto, "nivel": a.nivel, "objetivo": a.objetivo, "curriculo": a.curriculo,
         "manual": a.manual, "areas": a.area or [], "anonimizar": not a.sem_anonimizar,
         "nomes": a.nome or [], "ocultar": a.ocultar or [], "quero": a.quero or [], "nao_quero": a.nao_quero or []}
    if tty:
        print("Vou te fazer algumas perguntas. Enter aceita o valor entre colchetes.\n")
        e["remoto"] = e["remoto"] or _perguntar("Vagas remotas (nao, aceitar, preferir, somente)", "aceitar")
        if e["remoto"] != "somente":
            if not e["estados"]:
                e["estados"] = [x.strip() for x in _perguntar("UF(s) onde busca, separadas por vírgula (ex.: SP)").split(",")]
            e["cidade"] = e["cidade"] or _perguntar("Cidade onde você mora ou quer trabalhar")
            e["alcance"] = e["alcance"] or _perguntar("Alcance (cidade, regiao_imediata, estado)", "regiao_imediata")
        e["nivel"] = e["nivel"] or _perguntar("Nível (estagio, junior, pleno, senior, lideranca)")
        e["objetivo"] = e["objetivo"] or _perguntar("Em uma frase, o que você busca", obrigatorio=False)
        if e["curriculo"] is None and not e["manual"]:
            e["curriculo"] = _perguntar("Caminho do currículo (.txt .md .docx .pdf), ou Enter para escolher as áreas à mão",
                                        obrigatorio=False) or None
    tem_ia = bool(escolher_provedor(avaliacao_cfg(load_config(a.config)) if Path(a.config or "config.yaml").exists() else {}))
    if e["curriculo"] and not e["manual"] and not tem_ia:
        print("Nenhuma chave de IA no ambiente (GEMINI_API_KEY ou ANTHROPIC_API_KEY): seguindo no modo manual.")
        e["manual"] = True
    if (not e["curriculo"] or e["manual"]) and not e["areas"]:
        if not tty:
            print("Informe --area (ex.: --area saude --area educacao:adjacente) ou um currículo. Catálogo: init --listar-areas")
            return 2
        catalogo = list(areas.listar().items())
        for i, (slug, p) in enumerate(catalogo, 1):
            print(f"  {i:2d}. {p['nome']}  [{p['status']}]")
        for papel, ajuda in (("alvo", "o que você QUER ser"), ("adjacente", "vizinhas que também servem"),
                             ("ponte", "o que sua experiência sustenta, mas não é o desejo")):
            nums = _perguntar(f"Números das áreas '{papel}' ({ajuda}), separados por vírgula", obrigatorio=(papel == "alvo"))
            for n in [x for x in nums.replace(" ", "").split(",") if x.isdigit()]:
                if 0 < int(n) <= len(catalogo):
                    e["areas"].append(f"{catalogo[int(n) - 1][0]}:{papel}")
    if tty and not e["quero"] and not e["nao_quero"]:
        print("\nVagas de REFERÊNCIA deixam medir se a configuração acerta. Cole títulos, um por linha (Enter vazio termina).")
        for chave, rotulo in (("quero", "que você QUER receber"), ("nao_quero", "que você NÃO quer")):
            print(f"Títulos {rotulo}:")
            while (t := input("  > ").strip()):
                e[chave].append(t)

    if e["curriculo"] and not e["manual"]:
        texto, achados = assistente.previa_anonimizada(e)
        print("\n--- texto que seria enviado à IA (dados pessoais removidos: " + anonimizar.resumo(achados) + ") ---")
        print(texto[:3000] + ("\n[...]" if len(texto) > 3000 else ""))
        print("--- fim ---")
        if a.sim:
            e["aprovado"] = True
        elif tty:
            e["aprovado"] = input("Enviar este texto à IA? Confira se não restou nenhum dado pessoal. [s/N] ").strip().lower() in ("s", "sim", "y")
        if not e.get("aprovado"):
            print("Envio não aprovado. Nada foi enviado. Rode de novo com --manual ou aprove o texto (--sim).")
            return 1
    try:
        # os arquivos saem ao lado do config informado (padrão: a raiz do projeto)
        r = assistente.executar_init(e, raiz=Path(a.config).resolve().parent if a.config else None)
    except (assistente.InitErro, FileNotFoundError, RuntimeError, ValueError) as err:
        print(f"Erro: {err}")
        return 2
    print(f"\nGravado: {r['config']} e {r['perfil']} (cópias .bak dos anteriores, se existiam).")
    print(f"Nível: {r['nivel']} | termos de busca: {', '.join(r['termos_busca'])}")
    print("Categorias: " + ", ".join(r["categorias"].values()))
    print("Cidades: " + ", ".join(r["cidades"]) + (" ..." if len(r["cidades"]) >= 12 else ""))
    for av in r["avisos"]:
        print(f"  ! {av}")
    if r["pendencias"]:
        print("\nPendências no config:\n" + "\n".join(f"  - {p}" for p in r["pendencias"]))
        return 2
    if r["medicao"]:
        print("\n" + "\n".join(calibracao.relatorio_medicao(r["medicao"])))
    print("\nPróximo passo: python -m vagas_monitor run --force --dry-run --no-notify   e leia reports/LATEST.md")
    return 0


def cmd_calibrar(a) -> int:
    """Mede o config contra vagas de referência (offline) ou sonda o mercado da região (rede)."""
    from . import calibracao
    from .config import ROOT, load_config
    from .validar import validar_config

    cfg = load_config(a.config)
    pend = validar_config(cfg)
    if pend:
        print("config.yaml incompleto:\n" + "\n".join(f"  - {p}" for p in pend))
        return 2
    if a.sondar:
        fontes = tuple(x.strip() for x in a.fontes.split(",") if x.strip())
        print(f"Coletando títulos da região ({', '.join(fontes)}, últimos {a.dias} dias)...")
        titulos, erros = calibracao.coletar_titulos(cfg, a.dias, fontes)
        for k, v in erros.items():
            print(f"  ! {k}: {v}")
        if not titulos:
            print("Nenhum título coletado.")
            return 1
        print("\n".join(calibracao.relatorio_sondagem(calibracao.sondar(cfg, titulos))))
        return 0
    caminho = Path(a.referencia) if a.referencia else ROOT / "calibracao" / "referencia.yaml"
    try:
        ref = calibracao.carregar_referencia(caminho)
    except FileNotFoundError as err:
        print(f"{err}\nCrie o arquivo com `init` (--quero/--nao-quero) ou à mão: listas `quero` e `nao_quero` de títulos.")
        return 2
    m = calibracao.medir(cfg, ref["quero"], ref["nao_quero"], a.meta)
    print("\n".join(calibracao.relatorio_medicao(m)))
    return 0 if m["ok"] else 1


def cmd_doctor(a) -> int:
    """Confere config, perfil, canais, IA, fontes e estado, e diz como corrigir cada problema."""
    from . import diagnostico
    itens, rc = diagnostico.executar(a.config, rede=not a.offline, ia=a.ia)
    print("\n".join(diagnostico.formatar(itens)))
    return rc


def cmd_publicar_secrets(a) -> int:
    """Grava no GitHub os secrets do .env, sem mostrar nenhum valor."""
    from . import segredos
    from .config import ROOT
    env_path = Path(a.env) if a.env else ROOT / ".env"
    if not env_path.exists():
        print(f"{env_path} não existe. Copie .env.example para .env e preencha (guia/02).")
        return 2
    valores, ignorados = segredos.coletar(env_path, ROOT / "perfil.md" if a.perfil else None)
    if not valores:
        print("Nada a publicar: o .env está vazio ou só tem valores de exemplo.")
        return 2
    destino = a.repo or "o repositório desta pasta (gh decide pelo git remote)"
    print(f"Publicando {len(valores)} secret(s) em {destino}. Os valores NÃO são exibidos.\n")
    resultados = segredos.publicar(valores, a.repo, a.dry_run)
    for r in resultados:
        print(f"  {'ok   ' if r.ok else 'FALHOU'} {r.nome}" + (f"  ({r.detalhe})" if r.detalhe else ""))
    if ignorados:
        print("\nIgnorados (vazios ou de exemplo): " + ", ".join(ignorados))
    return 0 if all(r.ok for r in resultados) else 1


def cmd_render(a) -> int:
    """Regera Markdown/HTML a partir do JSON de uma rodada (útil para ajustar o layout sem coletar)."""
    from . import report
    from .config import ROOT, load_config
    cfg = load_config(a.config)
    folder = ROOT / cfg.get("relatorio", {}).get("pasta", "reports")
    path = Path(a.json_path) if a.json_path else max(folder.glob("????-??-??.json"), default=None)
    if not path or not path.exists():
        print("nenhum JSON de rodada encontrado em", folder)
        return 1
    ctx = report.load_context(path)
    paths = report.write_all(ctx, cfg)
    print("regerado:", ", ".join(str(p) for p in paths.values()))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="vagas_monitor", description="Radar de Vagas Laplace — monitor de vagas por região e área de atuação no Brasil")
    p.add_argument("--config", help="caminho alternativo do config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="executa uma rodada (respeita a cadência, salvo --force)")
    r.add_argument("--force", action="store_true", help="roda mesmo antes dos 5 dias")
    r.add_argument("--dry-run", action="store_true", help="gera relatórios mas não salva estado nem notifica")
    r.add_argument("--no-notify", action="store_true", help="não envia Telegram/e-mail")
    r.add_argument("--lookback", type=int, help="janela em dias (padrão: 7; 30 na primeira execução)")
    r.add_argument("--skip", action="append", choices=["linkedin", "indeed", "gupy"], help="pula uma fonte")
    r.set_defaults(fn=cmd_run)

    sub.add_parser("status", help="mostra última execução e próxima rodada").set_defaults(fn=cmd_status)
    sub.add_parser("setup-telegram", help="descobre o chat_id do bot e grava no .env").set_defaults(fn=cmd_setup_telegram)
    sub.add_parser("test-notify", help="envia uma mensagem de teste nos canais configurados").set_defaults(fn=cmd_test_notify)
    sub.add_parser("check-ia", help="valida a chave de IA com uma chamada real").set_defaults(fn=cmd_check_ia)
    cl = sub.add_parser("classificar", help="mostra em que categoria um título cai, e por quê (calibração)")
    cl.add_argument("titulos", nargs="+", help="um ou mais títulos de vaga, entre aspas")
    cl.add_argument("--descricao", help="texto de descrição, se quiser testar a regra de descrição")
    cl.set_defaults(fn=cmd_classificar)
    ini = sub.add_parser("init", help="configura o monitor para você: região, nível, áreas e perfil")
    ini.add_argument("--listar-areas", action="store_true", help="mostra o catálogo de áreas e sai")
    ini.add_argument("--estado", help="UF(s), separadas por vírgula (ex.: SP ou SP,RJ)")
    ini.add_argument("--cidade", help="cidade-base")
    ini.add_argument("--uf", help="UF da cidade-base (se houver mais de um estado)")
    ini.add_argument("--alcance", choices=["cidade", "regiao_imediata", "estado", "lista"], help="padrão: regiao_imediata")
    ini.add_argument("--remoto", choices=["nao", "aceitar", "preferir", "somente"], help="padrão: aceitar")
    ini.add_argument("--nivel", choices=["estagio", "junior", "pleno", "senior", "lideranca"])
    ini.add_argument("--objetivo", help="em uma frase, o que você busca")
    ini.add_argument("--curriculo", help="currículo (.txt .md .docx .pdf) para a IA propor áreas e termos")
    ini.add_argument("--manual", action="store_true", help="sem IA: você escolhe as áreas do catálogo")
    ini.add_argument("--area", action="append", help="slug[:papel] (alvo, adjacente, ponte); repetível")
    ini.add_argument("--quero", action="append", help="título de vaga que você QUER (referência); repetível")
    ini.add_argument("--nao-quero", action="append", help="título de vaga que você NÃO quer; repetível")
    ini.add_argument("--nome", action="append", help="seu nome, para removê-lo do currículo; repetível")
    ini.add_argument("--ocultar", action="append", help="empregador ou escola a ocultar do texto enviado; repetível")
    ini.add_argument("--sem-anonimizar", action="store_true", help="NÃO remove dados pessoais (não recomendado)")
    ini.add_argument("--sim", action="store_true", help="aprova o envio do texto anonimizado à IA, sem perguntar")
    ini.add_argument("--nao-interativo", action="store_true", help="nunca pergunta; falta de dado vira erro")
    ini.set_defaults(fn=cmd_init)
    cal = sub.add_parser("calibrar", help="mede o config contra vagas de referência, ou sonda o mercado (--sondar)")
    cal.add_argument("--referencia", help="arquivo de referência (padrão: calibracao/referencia.yaml)")
    cal.add_argument("--meta", type=float, default=0.8, help="recall e corte mínimos (padrão: 0.8)")
    cal.add_argument("--sondar", action="store_true", help="coleta títulos reais da região e mostra termos e candidatos")
    cal.add_argument("--fontes", default="gupy", help="fontes da sondagem, separadas por vírgula (padrão: gupy)")
    cal.add_argument("--dias", type=int, default=30, help="janela da sondagem em dias (padrão: 30)")
    cal.set_defaults(fn=cmd_calibrar)
    dr = sub.add_parser("doctor", help="diagnostica config, perfil, Telegram, e-mail, IA e fontes (e como corrigir)")
    dr.add_argument("--offline", action="store_true", help="não faz chamadas de rede")
    dr.add_argument("--ia", action="store_true", help="testa a chave de IA com uma chamada real")
    dr.set_defaults(fn=cmd_doctor)
    ps = sub.add_parser("publicar-secrets", help="grava no GitHub os secrets do .env, sem mostrar os valores (usa o gh)")
    ps.add_argument("--repo", help="dono/nome do repositório (padrão: o da pasta atual)")
    ps.add_argument("--env", help="caminho do .env (padrão: .env na raiz)")
    ps.add_argument("--perfil", action="store_true", help="publica também o perfil.md como secret PERFIL_MD")
    ps.add_argument("--dry-run", action="store_true", help="só lista o que seria publicado")
    ps.set_defaults(fn=cmd_publicar_secrets)
    rr = sub.add_parser("render", help="regera Markdown/HTML a partir do JSON da última rodada")
    rr.add_argument("json_path", nargs="?")
    rr.set_defaults(fn=cmd_render)

    a = p.parse_args(argv)
    _setup_logging(a.verbose)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
