#!/usr/bin/env python3
# preencher_malhas.py
# Python 3.10+
# Lê malhas.json, permite preencher status/observação/fim_de_jogo e gera relatório WhatsApp.

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

ARQUIVO_JSON = "malhas.json"

ORDEM_CATEGORIAS = [
    "Rotativos",
    "Parcelados",
    "Modelos",
    "Gestão PJ e Alto Risco",
    "Semanal",
]

ORDEM_MALHAS = {
    "Rotativos": [
        "ORIGENS",
        "ADMISSAO",
        "TETO V2",
        "CMA",
        "GESTAO",
        "CHEQUE",
        "CONCESSAO CARTAO",
        "CONCESSAO CHEQUE",
        "SUPER CREDITO",
        "RENOVACAO LIMITES SEMANAL",
        "OVERLIMIT CLOUD",
        "ATUALIZACAO OVERLIMIT ONLINE MF",
        "OVERLIMIT CARTAO",
    ],
    "Parcelados": [
        "CONSIGNADO",
        "CONSORCIO",
        "CP INVESTIDOR",
        "MICROCREDITO",
        "RX",
        "TH3 - OY",
        "IMOBILIARIO",
    ],
    "Modelos": [
        "BULKLOAD PF ROTATIVOS",
        "CMA PF",
        "DNA",
        "FATURAMENTO",
        "MODELOS PF PARCELADOS",
        "MODELOS PF ROTATIVOS",
        "THR",
        "RENDAS",
    ],
    "Gestão PJ e Alto Risco": [
        "BULKLOAD PRAT CPF_CNPJ",
        "PREVENTIVO PF",
        "LISTA PREV PJ SEMANAL",
        "REDUCAO SEMANAL",
        "REDUCAO MENSAL",
    ],
    "Semanal": [
        "THD SEMANAL",
        "THJ SEMANAL",
        "SUPER CREDITO SEMANAL",
        "OVERLIMIT CHEQUE SEMANAL",
        "RENOVADOR CHEQUE SEMANAL",
        "RX SEMANAL",
        "IMOBILIARIO PREVENTIVO - SEMANAL",
        "STATUS MQ",
    ],
}

# Status -> (chave no JSON, emoji WhatsApp)
STATUS_MAP = {
    "1": ("exec", "🟡"),            # Em execução
    "2": ("ok", "🟢"),              # Finalizado
    "3": ("contingencia", "🔵"),    # Contingência
    "4": ("abend", "🔴"),           # Abend
    "5": ("nao_comecou", "⚪"),     # Não começou
    "6": ("aguardando", "⚫"),      # Aguardando condição
    "7": ("sem_exec", "⚪"),        # Sem execução no Odate (mantive ⚪ para ficar igual uso comum)
    "0": (None, None),             # manter atual / pular
}

STATUS_LABEL = {
    "exec": "Em execução",
    "ok": "Finalizado",
    "contingencia": "Contingência",
    "abend": "Abend",
    "nao_comecou": "Não começou",
    "aguardando": "Aguardando condição",
    "sem_exec": "Sem execução no Odate",
}

def br_date(ymd: str) -> str:
    y, m, d = ymd.split("-")
    return f"{d}/{m}/{y}"

def normalize_name(s: str) -> str:
    s = (s or "").strip().upper()
    s = " ".join(s.split())
    # normaliza traço do TH3
    s = s.replace("TH3 – OY", "TH3 - OY")
    return s

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def index_catalogo(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    idx = {}
    for c in data.get("catalogo_malhas", []):
        idx[c["id"]] = c
    return idx

def ensure_day(data: Dict[str, Any], dia: str) -> None:
    dias = data.setdefault("dias", {})
    if dia not in dias:
        dias[dia] = {"updatedAt": "", "itens": []}

def itens_map(dia_obj: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    m = {}
    for it in dia_obj.get("itens", []):
        m[it["id"]] = it
    return m

def sort_catalogo(catalogo: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def cat_order(cat: str) -> int:
        try:
            return ORDEM_CATEGORIAS.index(cat)
        except ValueError:
            return 999

    def malha_order(cat: str, nome: str) -> int:
        nome = normalize_name(nome)
        lst = ORDEM_MALHAS.get(cat, [])
        try:
            return lst.index(nome)
        except ValueError:
            return 9999

    return sorted(
        catalogo,
        key=lambda c: (
            cat_order(c.get("categoria", "")),
            malha_order(c.get("categoria", ""), c.get("nome", "")),
            normalize_name(c.get("nome", "")),
        ),
    )

def prompt_date(default: str) -> str:
    while True:
        s = input(f"Data (YYYY-MM-DD) [{default}]: ").strip()
        if not s:
            return default
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            print("Data inválida. Ex: 2026-01-10")

def prompt_status(current_key: str) -> str:
    print("Status:")
    print("  1) 🟡 Em execução")
    print("  2) 🟢 Finalizado")
    print("  3) 🔵 Contingência")
    print("  4) 🔴 Abend")
    print("  5) ⚪ Não começou")
    print("  6) ⚫ Aguardando condição")
    print("  7) ⚪ Sem execução no Odate")
    print("  0) (manter / pular)")
    while True:
        s = input(f"Escolha [atual: {STATUS_LABEL.get(current_key, current_key)}]: ").strip()
        if s in STATUS_MAP:
            key, _ = STATUS_MAP[s]
            return current_key if key is None else key
        print("Opção inválida. Digite 0..7.")

def prompt_yesno(msg: str, default: bool) -> bool:
    d = "s" if default else "n"
    while True:
        s = input(f"{msg} (s/n) [{d}]: ").strip().lower()
        if not s:
            return default
        if s in ("s", "sim"):
            return True
        if s in ("n", "nao", "não"):
            return False
        print("Digite s ou n.")

def build_whatsapp_report(dia: str, rows: List[Tuple[str, str, str, bool, str]]) -> str:
    # rows: (categoria, nome, status_key, fim_de_jogo, obs)
    groups: Dict[str, List[str]] = {c: [] for c in ORDEM_CATEGORIAS}
    for cat, nome, st, fim, obs in rows:
        emoji = None
        for _, (k, e) in STATUS_MAP.items():
            if k == st:
                emoji = e
                break
        if not emoji:
            emoji = "⚪"
        # fim_de_jogo: ⚪ não validado / 🔵 validado
        fim_emoji = "🔵" if fim else "⚪"

        line = f"{emoji} {nome}"
        # se quiser incluir fim de jogo no texto, descomente:
        # line += f"  {fim_emoji}"
        if obs:
            line += f"  ({obs})"
        groups[cat].append(line)

    out = []
    out.append("Boa noite.\n")
    out.append("Acompanhamento Malhas\n")
    out.append(f"Odate: {br_date(dia)}\n")

    for cat in ORDEM_CATEGORIAS:
        out.append(f"{cat}:\n")
        if groups[cat]:
            out.extend([f"- {x}" for x in groups[cat]])
        else:
            out.append("- (sem itens)")
        out.append("")  # linha em branco

    out.append("Legenda:")
    out.append("🟡 Em execução | 🟢 Finalizado | 🔵 Contingência | 🔴 Abend | ⚪ Não começou/Sem execução | ⚫ Aguardando condição")
    out.append("⚪/🔵 em “Fim de jogo” = não validado / validado")
    return "\n".join(out)

def main():
    if not os.path.exists(ARQUIVO_JSON):
        print(f"Não achei {ARQUIVO_JSON} na pasta atual.")
        print("Coloque este script na mesma pasta do malhas.json e rode novamente.")
        return

    data = load_json(ARQUIVO_JSON)

    # pega última data existente como default
    dias_exist = sorted((data.get("dias") or {}).keys())
    default_day = dias_exist[-1] if dias_exist else "2026-01-10"
    dia = prompt_date(default_day)

    ensure_day(data, dia)
    dia_obj = data["dias"][dia]
    dia_obj["updatedAt"] = datetime.now().isoformat(timespec="seconds")

    catalogo = data.get("catalogo_malhas", [])
    catalogo_sorted = sort_catalogo(catalogo)

    itmap = itens_map(dia_obj)

    print("\nPreenchimento iniciado.")
    print("Dica: digite 0 para manter o status atual e ir para a próxima.\n")

    # vamos montar lista final para relatório
    report_rows: List[Tuple[str, str, str, bool, str]] = []

    for c in catalogo_sorted:
        mid = c["id"]
        cat = c.get("categoria", "-")
        nome = normalize_name(c.get("nome", mid))

        it = itmap.get(mid)
        if not it:
            it = {
                "id": mid,
                "status": "sem_exec",
                "ultimo_job": "-",
                "termino_real": "-",
                "fim_de_jogo": False,
                "nota": "",
            }
            dia_obj.setdefault("itens", []).append(it)
            itmap[mid] = it

        print(f"Categoria: {cat}")
        print(f"Malha: {nome}")

        current_status = it.get("status", "sem_exec")
        new_status = prompt_status(current_status)
        it["status"] = new_status

        # fim de jogo (validado)
        cur_fim = bool(it.get("fim_de_jogo", False))
        new_fim = prompt_yesno("Fim de jogo validado", cur_fim)
        it["fim_de_jogo"] = new_fim

        # observação
        cur_obs = (it.get("nota") or "").strip()
        obs = input(f"Observação (enter mantém) [{cur_obs if cur_obs else '-'}]: ").strip()
        if obs != "":
            it["nota"] = obs

        print("-" * 48)

    # garante que itens do dia estejam organizados igual catálogo (pra ficar bonito no JSON)
    dia_obj["itens"] = sorted(
        dia_obj["itens"],
        key=lambda it: (
            ORDEM_CATEGORIAS.index(index_catalogo(data)[it["id"]]["categoria"])
            if it["id"] in index_catalogo(data) and index_catalogo(data)[it["id"]]["categoria"] in ORDEM_CATEGORIAS
            else 999,
            ORDEM_MALHAS.get(index_catalogo(data)[it["id"]]["categoria"], []).index(normalize_name(index_catalogo(data)[it["id"]]["nome"]))
            if it["id"] in index_catalogo(data)
            and normalize_name(index_catalogo(data)[it["id"]]["nome"]) in ORDEM_MALHAS.get(index_catalogo(data)[it["id"]]["categoria"], [])
            else 9999,
            normalize_name(index_catalogo(data)[it["id"]]["nome"]) if it["id"] in index_catalogo(data) else it["id"],
        ),
    )

    # monta linhas do relatório
    cat_by_id = index_catalogo(data)
    for it in dia_obj["itens"]:
        c = cat_by_id.get(it["id"], {})
        cat = c.get("categoria", "-")
        nome = normalize_name(c.get("nome", it["id"]))
        st = it.get("status", "sem_exec")
        fim = bool(it.get("fim_de_jogo", False))
        obs = (it.get("nota") or "").strip()
        report_rows.append((cat, nome, st, fim, obs))

    # salva JSON
    save_json(ARQUIVO_JSON, data)

    # relatório
    rel = build_whatsapp_report(dia, report_rows)

    print("\n\n========== RELATÓRIO WHATSAPP (COPIAR E COLAR) ==========\n")
    print(rel)
    print("\n========================================================\n")
    print(f"Salvo em: {ARQUIVO_JSON} (dia {dia})")

if __name__ == "__main__":
    main()
