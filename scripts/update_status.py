import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MALHAS_JSON = ROOT / "malhas.json"
UPDATES_DIR = ROOT / "updates"

ORDEM_CATEGORIAS = [
    "Rotativos",
    "Parcelados",
    "Modelos",
    "Gestão PJ e Alto Risco",
    "Semanal"
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
        "OVERLIMIT CARTAO"
    ],
    "Parcelados": [
        "CONSIGNADO",
        "CONSORCIO",
        "CP INVESTIDOR",
        "MICROCREDITO",
        "RX",
        "TH3 - OY",
        "IMOBILIARIO"
    ],
    "Modelos": [
        "BULKLOAD PF ROTATIVOS",
        "CMA PF",
        "DNA",
        "FATURAMENTO",
        "MODELOS PF PARCELADOS",
        "MODELOS PF ROTATIVOS",
        "THR",
        "RENDAS"
    ],
    "Gestão PJ e Alto Risco": [
        "BULKLOAD PRAT CPF_CNPJ",
        "PREVENTIVO PF",
        "LISTA PREV PJ SEMANAL",
        "REDUCAO SEMANAL",
        "REDUCAO MENSAL"
    ],
    "Semanal": [
        "THD SEMANAL",
        "THJ SEMANAL",
        "SUPER CREDITO SEMANAL",
        "OVERLIMIT CHEQUE SEMANAL",
        "RENOVADOR CHEQUE SEMANAL",
        "RX SEMANAL",
        "IMOBILIARIO PREVENTIVO - SEMANAL",
        "STATUS MQ"
    ]
}

VALID_STATUS = {
    "exec", "ok", "contingencia", "abend", "nao_comecou", "aguardando", "sem_exec"
}

def norm(s: str) -> str:
    s = (s or "").strip().upper()
    s = " ".join(s.split())
    s = s.replace("TH3 – OY", "TH3 - OY")
    return s

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def build_catalog_index(data):
    by_id = {}
    by_name = {}
    for c in data.get("catalogo_malhas", []):
        cid = c.get("id")
        nome = norm(c.get("nome", ""))
        by_id[cid] = c
        by_name[nome] = c
    return by_id, by_name

def sort_catalogo(catalogo):
    def cat_order(cat):
        try:
            return ORDEM_CATEGORIAS.index(cat)
        except ValueError:
            return 999

    def malha_order(cat, nome):
        nome = norm(nome)
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
            norm(c.get("nome", "")),
        ),
    )

def ensure_day(data, day):
    data.setdefault("dias", {})
    if day not in data["dias"]:
        data["dias"][day] = {"updatedAt": "", "itens": []}

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/update_status.py updates/AAAA-MM-DD.json")
        sys.exit(1)

    update_path = ROOT / sys.argv[1]
    if not update_path.exists():
        print(f"Arquivo não encontrado: {update_path}")
        sys.exit(1)

    data = load_json(MALHAS_JSON)

    by_id, by_name = build_catalog_index(data)

    payload = load_json(update_path)
    day = payload.get("date")
    if not day:
        print("O arquivo de update precisa ter o campo 'date' em YYYY-MM-DD")
        sys.exit(1)

    ensure_day(data, day)
    dia_obj = data["dias"][day]

    updatedAt = payload.get("updatedAt") or datetime.now().isoformat(timespec="seconds")
    dia_obj["updatedAt"] = updatedAt

    # Monta mapa do que veio no update: nome -> item preenchido
    raw_itens = payload.get("itens", [])
    incoming = {}
    for it in raw_itens:
        nome = norm(it.get("nome", ""))
        if not nome:
            continue
        st = it.get("status", "sem_exec")
        if st not in VALID_STATUS:
            st = "sem_exec"
        incoming[nome] = {
            "status": st,
            "ultimo_job": it.get("ultimo_job", "-") or "-",
            "termino_real": it.get("termino_real", "-") or "-",
            "fim_de_jogo": bool(it.get("fim_de_jogo", False)),
            "nota": (it.get("nota", "") or "").strip()
        }

    # Garante 100% das malhas do catálogo no dia
    itens_final = []
    catalogo_sorted = sort_catalogo(data.get("catalogo_malhas", []))

    for c in catalogo_sorted:
        cid = c["id"]
        nome = norm(c.get("nome", cid))
        fill = incoming.get(nome)

        if fill:
            itens_final.append({
                "id": cid,
                "status": fill["status"],
                "ultimo_job": fill["ultimo_job"],
                "termino_real": fill["termino_real"],
                "fim_de_jogo": fill["fim_de_jogo"],
                "nota": fill["nota"]
            })
        else:
            itens_final.append({
                "id": cid,
                "status": "sem_exec",
                "ultimo_job": "-",
                "termino_real": "-",
                "fim_de_jogo": False,
                "nota": ""
            })

    dia_obj["itens"] = itens_final
    save_json(MALHAS_JSON, data)

    print(f"OK: atualizado malhas.json para o dia {day} usando {update_path.name}")

if __name__ == "__main__":
    main()
