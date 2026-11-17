"""Classifica textos de fragrância em perfis olfativos filtráveis."""
from __future__ import annotations

import csv
import re
from pathlib import Path


PATH = Path("data/fragrancias_avatim.csv")

# A ordem também é a ordem de apresentação no filtro. Cada regra usa somente
# termos explícitos na descrição da própria fragrância.
PROFILES = {
    "Cítrica": r"cítric|limão|bergamota|mandarina|laranja|lima\b|tangerina|grapefruit",
    "Floral": r"floral|flor\b|rosa\b|jasmim|violeta|muguet|ylang|gerânio|magnólia|orquídea|íris|mimosa|neroli",
    "Frutada": r"frutal|fruta\b|pitanga|maçã|pera\b|damasco|pêssego|cassis|framboesa|coco\b|romã|maracujá|figo\b|carambola|jabuticaba|seriguela",
    "Amadeirada": r"amadeir|cedro|sândalo|madeira|vetiver",
    "Aromática": r"aromát|herb|ervas|alecrim|fougère|lavanda|verbena",
    "Fresca": r"fresc|refresc|leveza|revigorante",
    "Adocicada": r"doce|adocic|baunilha|tonka|caramelo|cremos",
    "Oriental": r"oriental|âmbar|resinos",
    "Especiada": r"especiad|cravo|canela|pimenta|cardamomo|cominho",
    "Verde": r"verde|folhas|galbano|floresta",
    "Terrosa": r"terros|patchouli|musgo",
    "Aquática": r"aquát|marinh|água\b",
    "Almiscarada": r"musk|almiscar",
    "Gourmand": r"gourmand|chocolate|cacau|açúcar",
}


def profiles(text: str) -> str:
    return "; ".join(name for name, pattern in PROFILES.items() if re.search(pattern, text, re.IGNORECASE))


def main() -> None:
    with PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
        fields = list(rows[0])
    for row in rows:
        row["perfis_olfativos"] = profiles(row["sobre_a_fragancia"])
    if "perfis_olfativos" not in fields:
        fields.append("perfis_olfativos")
    with PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print({"linhas": len(rows), "com_perfil": sum(bool(row["perfis_olfativos"]) for row in rows)})


if __name__ == "__main__":
    main()
