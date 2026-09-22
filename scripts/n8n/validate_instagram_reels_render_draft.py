from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_WORKFLOW = Path("n8n/workflows/ofertas-instagram-reels-render-draft.json")
REQUIRED_NODES = {
    "Selecionar Template Reels",
    "Buscar Template ASS Reels",
    "Escolher Template ASS Reels",
    "Baixar Template ASS Reels",
    "Montar Payload Render Reels",
    "Criar Job Render Reels",
    "Normalizar Job Render Reels",
    "Job Render Aceito?",
    "Checar Status Render Reels",
    "Restaurar Contexto Render Reels",
    "Render Pronto?",
    "Pode Repetir Render Reels?",
    "Aguardar Render Reels",
    "Falhar Render Reels",
}


class DraftValidationError(ValueError):
    pass


def node_map(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node.get("name")): node for node in workflow.get("nodes", [])}


def targets(workflow: dict[str, Any], name: str) -> list[set[str]]:
    branches = workflow.get("connections", {}).get(name, {}).get("main", [])
    return [
        {str(target.get("node")) for target in branch if isinstance(target, dict)}
        for branch in branches
        if isinstance(branch, list)
    ]


def validate(workflow: dict[str, Any]) -> None:
    nodes = node_map(workflow)
    errors: list[str] = []
    if workflow.get("id") != "OfertasInstagramReelsRenderDraft":
        errors.append("id do draft invalido")
    if workflow.get("active") is not False:
        errors.append("draft deve permanecer inativo")
    missing = sorted(REQUIRED_NODES - nodes.keys())
    if missing:
        errors.append("nos ausentes: " + ", ".join(missing))

    expected = {
        "Revalidar Midia": [{"Selecionar Template Reels"}],
        "Normalizar Job Render Reels": [{"Job Render Aceito?"}],
        "Job Render Aceito?": [{"Checar Status Render Reels"}, {"Falhar Render Reels"}],
        "Render Pronto?": [{"Dry Run Instagram?"}, {"Pode Repetir Render Reels?"}],
        "Pode Repetir Render Reels?": [{"Aguardar Render Reels"}, {"Falhar Render Reels"}],
        "Aguardar Render Reels": [{"Checar Status Render Reels"}],
        "Falhar Render Reels": [{"Dry Run Instagram?"}],
    }
    for name, expected_targets in expected.items():
        if targets(workflow, name) != expected_targets:
            errors.append(f"conexao invalida: {name}")

    create = nodes.get("Criar Job Render Reels", {})
    create_parameters = create.get("parameters", {})
    if create_parameters.get("url") != "http://reels-renderer:8080/v1/render/jobs":
        errors.append("endpoint de criacao do renderer invalido")
    renderer_credential = create.get("credentials", {}).get("httpHeaderAuth", {})
    if renderer_credential.get("name") != "Reels Renderer Bearer":
        errors.append("credencial do renderer ausente")
    for name in ("Criar Job Render Reels", "Checar Status Render Reels"):
        if nodes[name].get("continueOnFail") is not True:
            errors.append(f"{name} deve continuar em erro para permitir fallback")

    drive_nodes = ("Buscar Template ASS Reels", "Baixar Template ASS Reels")
    for name in drive_nodes:
        credential = nodes[name].get("credentials", {}).get("googleDriveOAuth2Api", {})
        if credential.get("name") != "Google Drive account":
            errors.append(f"credencial Drive ausente: {name}")

    publish = nodes.get("Criar Container Reels", {})
    publish_text = json.dumps(publish, ensure_ascii=False)
    if "published_video_url || $json.video_url" not in publish_text:
        errors.append("publicacao nao usa fallback/render artifact")

    copy_code = str(
        nodes.get("Montar Copy Instagram", {})
        .get("parameters", {})
        .get("jsCode", "")
    )
    if "const rawSubniche" not in copy_code or "const subniche" not in copy_code:
        errors.append("copy sem normalizacao de primary_subniche")
    if r"\nconst subniche" in copy_code or r"\nconst hashtag" in copy_code:
        errors.append("copy contem quebra de linha literal no JavaScript")

    query = str(
        nodes.get("Registrar Resultado Supabase", {})
        .get("parameters", {})
        .get("query", "")
    )
    for field in ("template_id", "render_status", "render_error_log", "published_video_source"):
        if field not in query:
            errors.append(f"registro sem campo de render: {field}")

    if errors:
        raise DraftValidationError("; ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", nargs="?", type=Path, default=DEFAULT_WORKFLOW)
    args = parser.parse_args()
    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    validate(workflow)
    print(f"OK: draft n8n valido: {args.workflow}")


if __name__ == "__main__":
    main()
