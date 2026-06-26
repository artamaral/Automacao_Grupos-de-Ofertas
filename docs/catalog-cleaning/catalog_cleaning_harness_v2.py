#!/usr/bin/env python3
"""
Harness deterministico para limpar catalogo de produtos Shopee e popular subniches.
Usa arquivo-base externo de taxonomia. Nao usa internet. Nao inventa taxonomia. Falha quando o contrato minimo de colunas nao e atendido.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

REQUIRED_COLUMNS = [
    "itemId",
    "shopId",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "commission",
    "price",
    "sales",
    "ratingStar",
    "priceDiscountRate",
    "source_hits",
]

def load_taxonomy(taxonomy_path: Path) -> Dict[str, Any]:
    if not taxonomy_path.exists():
        raise SystemExit(f"Arquivo-base de taxonomia ausente: {taxonomy_path}")
    try:
        data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Arquivo-base de taxonomia inválido: {taxonomy_path}. Erro: {exc}")

    allowed = set(data.get("allowed_subniches") or [])
    keyword_map = data.get("source_keyword_to_subniche") or {}
    generic_hits = set(data.get("generic_source_hits") or [])
    default_subniche = data.get("generic_default_subniche") or "bebe-geral"
    fallback_rules = data.get("fallback_product_name_rules") or []

    if not allowed:
        raise SystemExit("Taxonomia inválida: allowed_subniches vazio ou ausente")
    if default_subniche not in allowed:
        raise SystemExit(f"Taxonomia inválida: generic_default_subniche fora de allowed_subniches: {default_subniche}")

    empty_keywords = [k for k in keyword_map if not as_text(k)]
    if empty_keywords:
        raise SystemExit("Taxonomia inválida: existe palavra-chave vazia em source_keyword_to_subniche")
    bad_keyword_targets = {k: v for k, v in keyword_map.items() if v not in allowed}
    if bad_keyword_targets:
        raise SystemExit(f"Taxonomia inválida: source_keyword_to_subniche aponta para subniche não permitido: {bad_keyword_targets}")

    for rule in fallback_rules:
        if rule.get("subniche") not in allowed:
            raise SystemExit(f"Taxonomia inválida: fallback_product_name_rules aponta para subniche não permitido: {rule}")
        if not rule.get("pattern_regex"):
            raise SystemExit(f"Taxonomia inválida: fallback sem pattern_regex: {rule}")

    return {
        "version": data.get("version", "sem_versao"),
        "allowed_subniches": sorted(allowed),
        "source_keyword_to_subniche": {normalize_name(k): v for k, v in keyword_map.items()},
        "generic_source_hits": {normalize_name(k) for k in generic_hits},
        "generic_default_subniche": default_subniche,
        "fallback_product_name_rules": sorted(fallback_rules, key=lambda r: int(r.get("order", 999999))),
        "raw": data,
    }


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def to_number(series: pd.Series) -> pd.Series:
    # Aceita numeros reais, strings com ponto decimal e strings pt-BR com virgula decimal.
    # Nao remove ponto decimal quando ele e o unico separador.
    def normalize_number(value: Any) -> str:
        text = as_text(value).replace("R$", "").replace(" ", "")
        if not text:
            return ""
        if "," in text and "." in text:
            # Formato pt-BR provavel: 1.234,56
            return text.replace(".", "").replace(",", ".")
        if "," in text:
            # Formato decimal com virgula: 51,90
            return text.replace(",", ".")
        return text

    return pd.to_numeric(series.map(normalize_number), errors="coerce")


def normalize_name(value: Any) -> str:
    text = as_text(value).lower()
    return re.sub(r"\s+", " ", text).strip()


def valid_image(value: Any) -> bool:
    text = as_text(value).lower()
    return bool(text) and text not in {"nan", "none", "null", "[]"} and text.startswith(("http://", "https://"))


def parse_source_hits(value: Any) -> List[str]:
    text = as_text(value)
    if not text or text in {"[]", "nan", "None", "null"}:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [as_text(x) for x in parsed if as_text(x)]
        if isinstance(parsed, str):
            return [parsed]
    except Exception:
        pass
    # Fallback estrito: extrai tokens separados por virgula/ponto-e-virgula sem inventar termos.
    return [as_text(x).strip('"\'[] ') for x in re.split(r"[,;]", text) if as_text(x).strip('"\'[] ')]


def normalize_source_keyword(hit: str) -> str:
    h = normalize_name(hit)
    if h.startswith("keyword:"):
        return h.split(":", 1)[1].strip()
    if h.startswith("matchid:"):
        return h
    return h


def dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def classify_subniches(source_hits: Any, product_name: Any, taxonomy: Dict[str, Any]) -> Tuple[List[str], str, List[str], List[str]]:
    hits = parse_source_hits(source_hits)
    normalized = [normalize_source_keyword(h) for h in hits]
    normalized = [h for h in normalized if h]

    keyword_map = taxonomy["source_keyword_to_subniche"]
    generic_hits = taxonomy["generic_source_hits"]
    default_subniche = taxonomy["generic_default_subniche"]

    # 1) Todo source_hit especifico mapeado no arquivo-base gera um subniche.
    mapped = dedupe_preserve_order(keyword_map[kw] for kw in normalized if kw in keyword_map)
    if mapped:
        return mapped, "source_hits", normalized, []

    unmapped_specific = [kw for kw in normalized if kw not in generic_hits]
    has_generic = any(kw in generic_hits for kw in normalized)
    only_generic_or_empty = (not normalized) or (has_generic and not unmapped_specific)

    # 2) ProductName só pode ser usado quando source_hits é genérico ou vazio.
    if only_generic_or_empty:
        name = normalize_name(product_name)
        for rule in taxonomy["fallback_product_name_rules"]:
            if re.search(rule["pattern_regex"], name):
                basis = "source_hits_generico+productName" if has_generic else "productName"
                return [rule["subniche"]], basis, normalized, []
        return [default_subniche], "source_hits_generico", normalized, []

    # 3) Termo novo/desconhecido: não inventar associação; registrar para revisão.
    return [default_subniche], "sem_regra_taxonomia", normalized, unmapped_specific


def build_removal_reason(row: pd.Series) -> str:
    reasons = []
    if not row["_valid_image"]:
        reasons.append("imagem_faltando_ou_invalida")
    if not row["_valid_price"]:
        reasons.append("preco_faltando_ou_invalido")
    if not row["_valid_commission"]:
        reasons.append("comissao_faltando_ou_invalida")
    if not row["_valid_rating"]:
        reasons.append("nota_menor_que_4_5_ou_invalida")
    if not row["_valid_ids"]:
        reasons.append("shopId_ou_itemId_faltando")
    return "|".join(reasons)


def run(input_path: Path, outdir: Path, taxonomy_path: Path, expected: Dict[str, int] | None = None) -> Dict[str, Any]:
    expected = expected or {}
    taxonomy = load_taxonomy(taxonomy_path)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Arquivo invalido. Colunas obrigatorias ausentes: {missing}")

    original_rows = len(df)
    df = df.copy()
    df["_source_row"] = df.index + 2  # numero da linha no CSV original, considerando cabecalho na linha 1

    df["_price_num"] = to_number(df["price"])
    df["_commission_num"] = to_number(df["commission"])
    df["_rating_num"] = to_number(df["ratingStar"])
    df["_sales_num"] = to_number(df["sales"]).fillna(0)
    df["_discount_num"] = to_number(df["priceDiscountRate"]).fillna(0)

    df["_valid_image"] = df["imageUrl"].map(valid_image)
    df["_valid_price"] = df["_price_num"].notna() & (df["_price_num"] > 0)
    df["_valid_commission"] = df["_commission_num"].notna() & (df["_commission_num"] > 0)
    df["_valid_rating"] = df["_rating_num"].notna() & (df["_rating_num"] >= 4.5)
    df["_valid_ids"] = df["shopId"].map(as_text).ne("") & df["itemId"].map(as_text).ne("")

    valid_mask = df[["_valid_image", "_valid_price", "_valid_commission", "_valid_rating", "_valid_ids"]].all(axis=1)
    removed_quality = df.loc[~valid_mask].copy()
    if len(removed_quality):
        removed_quality["removal_reason"] = removed_quality.apply(build_removal_reason, axis=1)

    clean = df.loc[valid_mask].copy()
    clean["_dedupe_key"] = clean["shopId"].map(as_text) + ":" + clean["itemId"].map(as_text)
    clean["_duplicate_count"] = clean.groupby("_dedupe_key")["_dedupe_key"].transform("size")

    clean = clean.sort_values(
        by=["_commission_num", "_rating_num", "_sales_num", "_discount_num", "_source_row"],
        ascending=[False, False, False, False, True],
        kind="mergesort",
    )
    safe_dup_mask = clean.duplicated("_dedupe_key", keep="first")
    removed_safe_dups = clean.loc[safe_dup_mask].copy()
    if len(removed_safe_dups):
        removed_safe_dups["removal_reason"] = "duplicata_exata_shopId_itemId"
    clean = clean.loc[~safe_dup_mask].copy()
    clean.insert(0, "_quality_rank", range(1, len(clean) + 1))

    # Colunas auxiliares finais devem vir no inicio.
    clean = clean.drop(columns=[c for c in clean.columns if c.startswith("_valid_") or c in {"_price_num", "_commission_num", "_rating_num", "_sales_num", "_discount_num"}], errors="ignore")

    # Marca duplicatas heuristicas por productName + price. Nao remove.
    name_key = clean["productName"].map(normalize_name)
    price_key = clean["price"].astype(str).str.strip()
    np_key = name_key + "|" + price_key
    group_sizes = np_key.map(np_key.value_counts())
    clean["duplicate_name_price_tag"] = ""
    clean["duplicate_name_price_group_id"] = ""
    clean["duplicate_name_price_group_size"] = ""
    clean["duplicate_name_price_keeper"] = ""

    duplicate_group_keys = sorted(np_key[group_sizes > 1].unique())
    group_id_map = {key: f"dup_np_{i:06d}" for i, key in enumerate(duplicate_group_keys, start=1)}
    clean["_name_price_key"] = np_key
    clean["_name_price_position"] = clean.groupby("_name_price_key").cumcount() + 1
    grouped_mask = clean["_name_price_key"].isin(group_id_map)
    clean.loc[grouped_mask, "duplicate_name_price_group_id"] = clean.loc[grouped_mask, "_name_price_key"].map(group_id_map)
    clean.loc[grouped_mask, "duplicate_name_price_group_size"] = group_sizes[grouped_mask].astype(int).astype(str)
    clean.loc[grouped_mask, "duplicate_name_price_keeper"] = (clean.loc[grouped_mask, "_name_price_position"] == 1).map(lambda x: "true" if x else "false")
    candidate_mask = grouped_mask & (clean["_name_price_position"] > 1)
    clean.loc[candidate_mask, "duplicate_name_price_tag"] = "candidato_revisao_duplicata_nome_preco"

    # Popula subniches.
    classifications = clean.apply(lambda row: classify_subniches(row["source_hits"], row["productName"], taxonomy), axis=1)
    clean["subniches"] = classifications.map(lambda x: json.dumps(x[0], ensure_ascii=False))
    clean["subniche_basis"] = classifications.map(lambda x: x[1])
    clean["source_keywords_norm"] = classifications.map(lambda x: json.dumps(x[2], ensure_ascii=False))
    clean["unmapped_source_keywords"] = classifications.map(lambda x: json.dumps(x[3], ensure_ascii=False))

    duplicates = clean.loc[candidate_mask].drop(columns=["_name_price_key", "_name_price_position"], errors="ignore").copy()
    clean = clean.drop(columns=["_name_price_key", "_name_price_position"], errors="ignore")

    removed = pd.concat([removed_quality, removed_safe_dups], ignore_index=True, sort=False)
    removed = removed.drop(columns=[c for c in removed.columns if c.startswith("_valid_") or c in {"_price_num", "_commission_num", "_rating_num", "_sales_num", "_discount_num"}], errors="ignore")

    clean_path = outdir / "shopee_catalogo_limpo_subniches.csv"
    removed_path = outdir / "shopee_catalogo_removidos.csv"
    dup_path = outdir / "shopee_catalogo_duplicados_914.csv"
    summary_path = outdir / "shopee_catalogo_subniches_resumo.json"

    clean.to_csv(clean_path, index=False)
    removed.to_csv(removed_path, index=False)
    duplicates.to_csv(dup_path, index=False)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(input_path),
        "output_files": {
            "clean_with_subniches": str(clean_path),
            "removed": str(removed_path),
            "duplicate_candidates": str(dup_path),
            "summary": str(summary_path),
        },
        "original_rows": int(original_rows),
        "removed_quality_rows": int(len(removed_quality)),
        "removed_safe_duplicate_rows": int(len(removed_safe_dups)),
        "clean_rows": int(len(clean)),
        "duplicate_name_price_rule": "productName normalizado lower/trim/espacos + price literal",
        "duplicate_name_price_groups": int(len(duplicate_group_keys)),
        "duplicate_name_price_rows_in_groups": int(grouped_mask.sum()),
        "duplicate_name_price_candidates_tagged": int(candidate_mask.sum()),
        "subniche_counts": pd.Series([sub for raw in clean["subniches"] for sub in json.loads(raw)]).value_counts().to_dict(),
        "subniche_basis_counts": clean["subniche_basis"].value_counts().to_dict(),
        "quality_filter_counts": {
            "image_invalid": int((~df["_valid_image"]).sum()),
            "price_invalid": int((~df["_valid_price"]).sum()),
            "commission_invalid": int((~df["_valid_commission"]).sum()),
            "rating_below_4_5_or_invalid": int((~df["_valid_rating"]).sum()),
            "missing_shop_or_item_id": int((~df["_valid_ids"]).sum()),
        },
        "taxonomy_file": str(taxonomy_path),
        "taxonomy_version": taxonomy["version"],
        "taxonomy": taxonomy["source_keyword_to_subniche"],
        "unmapped_source_keywords": sorted({kw for kws in clean["unmapped_source_keywords"].map(json.loads) for kw in kws}),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Validacoes opcionais de regressao para o arquivo historico.
    checks = {
        "expected_input_rows": (original_rows, expected.get("input_rows")),
        "expected_clean_rows": (len(clean), expected.get("clean_rows")),
        "expected_duplicate_candidates": (int(candidate_mask.sum()), expected.get("duplicate_candidates")),
    }
    failed = [f"{name}: obtido={got}, esperado={want}" for name, (got, want) in checks.items() if want is not None and got != want]
    if failed:
        raise SystemExit("Falha nas validacoes de regressao:\n" + "\n".join(failed))

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpa catalogo Shopee e popula subniches de forma deterministica.")
    parser.add_argument("--input", required=True, type=Path, help="Caminho do CSV de entrada.")
    parser.add_argument("--outdir", required=True, type=Path, help="Diretorio de saida.")
    parser.add_argument("--taxonomy-file", required=True, type=Path, help="Arquivo JSON base da taxonomia de subnichos.")
    parser.add_argument("--expected-input-rows", type=int, default=None)
    parser.add_argument("--expected-clean-rows", type=int, default=None)
    parser.add_argument("--expected-duplicate-candidates", type=int, default=None)
    args = parser.parse_args()

    summary = run(
        args.input,
        args.outdir,
        args.taxonomy_file,
        expected={
            "input_rows": args.expected_input_rows,
            "clean_rows": args.expected_clean_rows,
            "duplicate_candidates": args.expected_duplicate_candidates,
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
