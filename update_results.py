#!/usr/bin/env python3
"""
Atualiza automaticamente os resultados oficiais da Copa do Mundo 2026
no arquivo index.html (Bolão do Ronaldão), buscando dados na
football-data.org API.

Requer a variável de ambiente FOOTBALL_DATA_TOKEN com o token de
API gratuito de https://www.football-data.org/client/register
"""

import os
import re
import json
import sys
from datetime import datetime, timezone, timedelta
import urllib.request

API_URL = "https://api.football-data.org/v4/competitions/WC/matches"
HTML_FILE = "index.html"

# ─── MAPEAMENTO: nomes da API -> nomes usados na planilha/HTML ────────────────
# A API retorna nomes em inglês; o HTML usa nomes em português (maiúsculas,
# acentuados, conforme a tabela original da planilha).
TEAM_NAME_MAP = {
    "Mexico": "MÉXICO",
    "South Africa": "ÁFRICA DO SUL",
    "Korea Republic": "REP. CORÉIA",
    "Czech Republic": "REP. TCHECA",
    "Canada": "CANADÁ",
    "Bosnia and Herzegovina": "BÓSNIA",
    "United States": "ESTADOS UNIDOS",
    "Paraguay": "PARAGUAI",
    "Qatar": "CATAR",
    "Switzerland": "SUÍÇA",
    "Brazil": "BRASIL",
    "Morocco": "MARROCOS",
    "Haiti": "HAITI",
    "Scotland": "ESCÓCIA",
    "Australia": "AUSTRÁLIA",
    "Turkey": "TURQUIA",
    "Germany": "ALEMANHA",
    "Curacao": "CURAÇAU",
    "Curaçao": "CURAÇAU",
    "Curação": "CURAÇAU",
    "CURAçAO": "CURAÇAU",
    "Netherlands": "HOLANDA",
    "Japan": "JAPÃO",
    "Ivory Coast": "COSTA DO MARFIM",
    "Cote d'Ivoire": "COSTA DO MARFIM",
    "Ecuador": "EQUADOR",
    "Sweden": "SUÉCIA",
    "Tunisia": "TUNÍSIA",
    "Spain": "ESPANHA",
    "Cape Verde": "CABO VERDE",
    "Belgium": "BÉLGICA",
    "Egypt": "EGITO",
    "Saudi Arabia": "ARÁBIA SAUDITA",
    "Uruguay": "URUGUAI",
    "Iran": "IRÃ",
    "New Zealand": "NOVA ZELANDIA",
    "France": "FRANÇA",
    "Senegal": "SENEGAL",
    "Iraq": "IRAQUE",
    "Norway": "NORUEGA",
    "Argentina": "ARGENTINA",
    "Algeria": "ARGÉLIA",
    "Austria": "ÁUSTRIA",
    "Jordan": "JORDÂNIA",
    "Portugal": "PORTUGAL",
    "DR Congo": "REP. D. CONGO",
    "England": "INGLATERRA",
    "Croatia": "CROÁCIA",
    "Ghana": "GANA",
    "Panama": "PANAMÁ",
    "Uzbekistan": "UZBEQUISTÃO",
    "Colombia": "COLÔMBIA",
}

# ─── TABELA DE JOGOS (numero -> times, na ordem da planilha/HTML) ─────────────
# Mantemos esta lista para mapear (timeA, timeB) -> numero do jogo (1-72)
JOGOS = [
    (1,"MÉXICO","ÁFRICA DO SUL"),(2,"REP. CORÉIA","REP. TCHECA"),(3,"CANADÁ","BÓSNIA"),
    (4,"ESTADOS UNIDOS","PARAGUAI"),(5,"CATAR","SUÍÇA"),(6,"BRASIL","MARROCOS"),
    (7,"HAITI","ESCÓCIA"),(8,"AUSTRÁLIA","TURQUIA"),(9,"ALEMANHA","CURAÇAU"),
    (10,"HOLANDA","JAPÃO"),(11,"COSTA DO MARFIM","EQUADOR"),(12,"SUÉCIA","TUNÍSIA"),
    (13,"ESPANHA","CABO VERDE"),(14,"BÉLGICA","EGITO"),(15,"ARÁBIA SAUDITA","URUGUAI"),
    (16,"IRÃ","NOVA ZELANDIA"),(17,"FRANÇA","SENEGAL"),(18,"IRAQUE","NORUEGA"),
    (19,"ARGENTINA","ARGÉLIA"),(20,"ÁUSTRIA","JORDÂNIA"),(21,"PORTUGAL","REP. D. CONGO"),
    (22,"INGLATERRA","CROÁCIA"),(23,"GANA","PANAMÁ"),(24,"UZBEQUISTÃO","COLÔMBIA"),
    (25,"REP. TCHECA","ÁFRICA DO SUL"),(26,"SUÍÇA","BÓSNIA"),(27,"CANADÁ","CATAR"),
    (28,"MÉXICO","REP. CORÉIA"),(29,"ESTADOS UNIDOS","AUSTRÁLIA"),(30,"ESCÓCIA","MARROCOS"),
    (31,"BRASIL","HAITI"),(32,"TURQUIA","PARAGUAI"),(33,"HOLANDA","SUÉCIA"),
    (34,"ALEMANHA","COSTA DO MARFIM"),(35,"EQUADOR","CURAÇAU"),(36,"TUNÍSIA","JAPÃO"),
    (37,"ESPANHA","ARÁBIA SAUDITA"),(38,"BÉLGICA","IRÃ"),(39,"URUGUAI","CABO VERDE"),
    (40,"NOVA ZELÂNDIA","EGITO"),(41,"ARGENTINA","ÁUSTRIA"),(42,"FRANÇA","IRAQUE"),
    (43,"NORUEGA","SENEGAL"),(44,"JORDÂNIA","ARGÉLIA"),(45,"PORTUGAL","UZBEQUISTÃO"),
    (46,"INGLATERRA","GANA"),(47,"PANAMÁ","CROÁCIA"),(48,"COLÔMBIA","REP. D. CONGO"),
    (49,"SUÍÇA","CANADA"),(50,"BÓSNIA","CATAR"),(51,"ESCÓCIA","BRASIL"),
    (52,"MARROCOS","HAITI"),(53,"REP. TCHECA","MÉXICO"),(54,"ÁFRICA DO SUL","REP. CORÉIA"),
    (55,"EQUADOR","ALEMANHA"),(56,"CURAÇAU","COSTA DO MARFIM"),(57,"JAPÃO","SUÉCIA"),
    (58,"TUNÍSIA","HOLANDA"),(59,"TURQUIA","ESTADOS UNIDOS"),(60,"PARAGUAI","AUSTRÁLIA"),
    (61,"NORUEGA","FRANÇA"),(62,"SENEGAL","IRAQUE"),(63,"CABO VERDE","ARÁBIA SAUDITA"),
    (64,"URUGUAI","ESPANHA"),(65,"EGITO","IRÃ"),(66,"NOVA ZELÂNDIA","BÉLGICA"),
    (67,"PANAMÁ","INGLATERRA"),(68,"CROÁCIA","GANA"),(69,"COLÔMBIA","PORTUGAL"),
    (70,"REP. D. CONGO","UZBEQUISTÃO"),(71,"ARGÉLIA","ÁUSTRIA"),(72,"JORDÂNIA","ARGENTINA"),
]

# Index by (teamA, teamB) for quick lookup
JOGOS_IDX = {(a, b): num for num, a, b in JOGOS}


def map_team(name):
    """Map API team name to the local naming convention."""
    return TEAM_NAME_MAP.get(name, name.upper())


def fetch_matches(token):
    req = urllib.request.Request(
        API_URL,
        headers={"X-Auth-Token": token}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("matches", [])


def build_resultados(matches):
    """Build {jogo_num: {a: score, b: score}} dict from FINISHED matches."""
    resultados = {}
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        home = map_team(m["homeTeam"]["name"])
        away = map_team(m["awayTeam"]["name"])
        score = m.get("score", {}).get("fullTime", {})
        ha, aa = score.get("home"), score.get("away")
        if ha is None or aa is None:
            continue

        num = JOGOS_IDX.get((home, away))
        if num is None:
            # try reversed (API might swap home/away vs our table)
            num_rev = JOGOS_IDX.get((away, home))
            if num_rev is not None:
                num = num_rev
                ha, aa = aa, ha
            else:
                print(f"⚠️  Jogo não mapeado: [{repr(home)}] x [{repr(away)}] (API original: [{repr(m["homeTeam"]["name"])}] x [{repr(m["awayTeam"]["name"])}])")
                continue

        resultados[str(num)] = {"a": ha, "b": aa}
    return resultados


def update_html(resultados):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Merge with existing results (in case API misses an older game)
    m = re.search(r'const RESULTADOS_OFICIAIS=(\{.*?\});', html)
    existing = json.loads(m.group(1)) if m else {}
    merged = {**existing, **resultados}

    # Sort by game number for readability
    merged_sorted = {k: merged[k] for k in sorted(merged, key=lambda x: int(x))}
    new_json = json.dumps(merged_sorted, ensure_ascii=False, separators=(",", ":"))

    results_changed = merged_sorted != existing

    if results_changed:
        html = re.sub(
            r'const RESULTADOS_OFICIAIS=\{.*?\};',
            f'const RESULTADOS_OFICIAIS={new_json};',
            html
        )

    # Sempre atualiza o timestamp (reflete a última vez que o robô checou),
    # mesmo que não haja resultado novo.
    sp_time = datetime.now(timezone.utc) - timedelta(hours=3)
    ts = sp_time.strftime("%d/%m/%Y %H:%M")
    html = re.sub(
        r'const ULTIMA_ATUALIZACAO="[^"]*";',
        f'const ULTIMA_ATUALIZACAO="{ts}";',
        html
    )

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    if results_changed:
        print(f"✅ Atualizado: {len(merged_sorted)} resultados | timestamp {ts}")
    else:
        print(f"ℹ️  Sem novos resultados. Timestamp atualizado para {ts}")
    return True


def main():
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        print("ERRO: variável FOOTBALL_DATA_TOKEN não definida.", file=sys.stderr)
        sys.exit(1)

    matches = fetch_matches(token)
    resultados = build_resultados(matches)
    changed = update_html(resultados)

    # Exit code 0 always (workflow decides whether to commit based on git diff)
    sys.exit(0)


if __name__ == "__main__":
    main()
