from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from time import time
from typing import Any

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.agents.compliance import ComplianceAgent
from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.agents.publisher import DryRunPublisher
from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.discovery_profiles import (
    DiscoveryProfile,
    DiscoveryProfileError,
    load_discovery_profile_catalog,
)
from ofertas_bot.models import Marketplace, MessageDraft
from ofertas_bot.providers.amazon import AmazonConfigurationError, AmazonProvider
from ofertas_bot.providers.amazon_gateway import AmazonPayloadError
from ofertas_bot.providers.gateway import ProviderLimitError
from ofertas_bot.providers.http import ProviderHttpError
from ofertas_bot.providers.real_http_guard import RealHttpValidationError
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider
from ofertas_bot.providers.shopee_gateway import ShopeePayloadError
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.providers.transport import HttpTransportError
from ofertas_bot.settings import Settings, get_settings
from ofertas_bot.storage.json_collection_inspection_store import (
    CollectionInspectionStoreWriteError,
    JsonCollectionInspectionStore,
)
from ofertas_bot.storage.json_message_draft_store import (
    JsonMessageDraftStore,
    MessageDraftStoreWriteError,
    format_message_drafts_for_review,
)
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreWriteError,
    create_pending_review_queue,
)
from ofertas_bot.storage.json_offer_store import (
    JsonOfferStore,
    OfferStoreWriteError,
    offer_to_json,
)

SHOPEE_MASKED_REQUEST_PARAMS = {"partner_id", "sign"}
SHOPEE_MASKED_REQUEST_HEADERS = {"authorization"}
REVIEW_TEXT_ENCODING = "utf-8-sig"
DEFAULT_DISCOVERY_PROFILES_PATH = Path("config/discovery_profiles.toml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness dry-run do bot de ofertas")
    parser.add_argument(
        "--niche",
        default=None,
        help="Nicho do grupo, ex: maquiagem, pesca, casa",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Slug do perfil de descoberta salvo em arquivo versionado",
    )
    parser.add_argument(
        "--subgroup",
        default=None,
        help="Slug opcional de subgroup dentro do profile selecionado",
    )
    parser.add_argument(
        "--profiles-file",
        default=str(DEFAULT_DISCOVERY_PROFILES_PATH),
        help="Arquivo TOML com perfis de descoberta",
    )
    parser.add_argument(
        "--marketplace",
        choices=[item.value for item in Marketplace],
        default=None,
        help="Marketplace para simular/buscar",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade máxima de ofertas",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Destino lógico da publicação",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simula publicação",
    )
    parser.add_argument(
        "--save-json",
        default=None,
        help="Caminho local para salvar ofertas normalizadas em JSON",
    )
    parser.add_argument(
        "--save-inspection-json",
        default=None,
        help="Caminho local para salvar artefato estruturado de inspeção da coleta",
    )
    parser.add_argument(
        "--save-messages-json",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em JSON",
    )
    parser.add_argument(
        "--save-messages-text",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em texto",
    )
    parser.add_argument(
        "--save-review-queue-json",
        default=None,
        help="Caminho local para salvar fila de revisão pendente em JSON",
    )
    parser.add_argument(
        "--diagnose-real-http",
        action="store_true",
        default=False,
        help="Valida pré-requisitos de HTTP real sem executar chamada externa",
    )
    parser.add_argument(
        "--execute-real-http-once",
        action="store_true",
        default=False,
        help="Executa uma coleta HTTP real controlada sem publicar e sem salvar JSON",
    )
    parser.add_argument(
        "--print-provider-request",
        action="store_true",
        default=False,
        help="Mostra o request da Shopee com campos sensíveis mascarados e sem enviar",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    args = build_parser().parse_args(argv)

    profile: DiscoveryProfile | None = None
    if args.profile:
        try:
            profile = load_discovery_profile_catalog(Path(args.profiles_file)).get(args.profile)
        except DiscoveryProfileError as error:
            return _print_discovery_profile_error(error)
        if profile is None:
            return _print_missing_discovery_profile_error(
                slug=args.profile,
                path=Path(args.profiles_file),
            )
        if args.subgroup:
            try:
                profile = profile.scoped_to_subgroup(args.subgroup)
            except DiscoveryProfileError as error:
                return _print_discovery_profile_error(error)
    elif args.subgroup:
        return _print_discovery_profile_error(
            DiscoveryProfileError("use --profile junto com --subgroup")
        )

    try:
        input_context = _resolve_input_context(
            niche_arg=args.niche,
            marketplace_arg=args.marketplace,
            limit_arg=args.limit,
            target_arg=args.target,
            settings=settings,
            profile=profile,
        )
    except DiscoveryProfileError as error:
        return _print_discovery_profile_error(error)

    marketplace = input_context.marketplace
    limit = input_context.limit
    niche = input_context.niche
    target = input_context.target
    search_term = profile.search_term() if profile is not None else niche
    if limit <= 0:
        return _print_limit_error(limit=limit)

    selected_real_http_modes = (
        args.diagnose_real_http,
        args.execute_real_http_once,
        args.print_provider_request,
    )
    if sum(bool(mode) for mode in selected_real_http_modes) > 1:
        return _print_real_http_mode_conflict()

    if args.diagnose_real_http:
        return _run_real_http_diagnostic(marketplace=marketplace, settings=settings)

    if args.print_provider_request:
        return _print_provider_request_preview(
            marketplace=marketplace,
            settings=settings,
            niche=search_term,
            limit=limit,
        )

    if args.execute_real_http_once:
        return _run_real_http_once(
            marketplace=marketplace,
            settings=settings,
            niche=niche,
            limit=limit,
            profile=profile,
        )

    dry_run = bool(args.dry_run or settings.default_dry_run)

    collector = CollectorAgent(settings=settings)
    scorer = ScorerAgent()
    copywriter = CopywriterAgent()
    compliance = ComplianceAgent(settings=settings)
    publisher = DryRunPublisher()
    raw_response: dict[str, object] | None = None

    try:
        if args.save_inspection_json:
            if profile is None:
                batch = collector.collect_with_inspection(
                    marketplace=marketplace,
                    niche=niche,
                    limit=limit,
                    query=search_term,
                )
            else:
                batch = collector.collect_from_profile_with_inspection(profile=profile, limit=limit)
            offers = batch.offers
            raw_response = batch.raw_response
        else:
            if profile is None:
                offers = collector.collect(marketplace=marketplace, niche=niche, limit=limit)
            else:
                offers = collector.collect_from_profile(profile=profile, limit=limit)
    except ShopeeConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.AMAZON, error=error)
    except RealHttpValidationError as error:
        return _print_real_http_guard_error(error=error)
    except ProviderLimitError as error:
        return _print_provider_limit_error(error=error)
    except ShopeePayloadError as error:
        return _print_payload_error(marketplace=Marketplace.SHOPEE, error=error)
    except ShopeeGraphqlPayloadError as error:
        return _print_payload_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonPayloadError as error:
        return _print_payload_error(marketplace=Marketplace.AMAZON, error=error)
    except ProviderHttpError as error:
        return _print_provider_http_error(marketplace=marketplace, error=error)
    except HttpTransportError as error:
        return _print_transport_error(marketplace=marketplace, error=error)

    if args.save_inspection_json:
        save_path = Path(args.save_inspection_json)
        if _is_root_output_path(save_path):
            _print_save_json_root_warning(save_path)
        try:
            JsonCollectionInspectionStore(path=save_path).save(
                _build_collection_inspection_payload(
                    marketplace=marketplace,
                    niche=niche,
                    limit=limit,
                    search_term=search_term,
                    target=target,
                    profile=profile,
                    subgroup_slug=args.subgroup,
                    offers=offers,
                    raw_response=raw_response,
                )
            )
        except CollectionInspectionStoreWriteError as error:
            return _print_save_inspection_json_error(error=error)
        print(f"INFO | Inspeção estruturada da coleta salva em {save_path}")

    if args.save_json:
        save_path = Path(args.save_json)
        if _is_root_output_path(save_path):
            _print_save_json_root_warning(save_path)
        try:
            JsonOfferStore(path=save_path).save(offers)
        except OfferStoreWriteError as error:
            return _print_save_json_error(error=error)
        print(f"INFO | Ofertas normalizadas salvas em {save_path}")

    scored_offers = scorer.score(offers)
    approved_drafts: list[MessageDraft] = []

    print(
        f"INFO | Encontradas {len(scored_offers)} ofertas "
        f"para nicho={niche} marketplace={marketplace}"
    )
    if profile is not None:
        print(
            f"INFO | Perfil de descoberta={profile.slug} "
            f"query=\"{profile.search_term()}\" target={target}"
        )
        if profile.discovery_method:
            print(f"INFO | discovery_method={profile.discovery_method}")
        if profile.shopee_offer_names:
            print(
                "INFO | shopee_offer_names="
                + ",".join(profile.shopee_offer_names)
            )
        if profile.shopee_product_match_ids:
            print(
                "INFO | shopee_product_match_ids="
                + ",".join(str(item) for item in profile.shopee_product_match_ids)
            )

    for index, scored in enumerate(scored_offers, start=1):
        draft = copywriter.create_message(scored)
        result = compliance.validate(draft=draft, dry_run=dry_run)

        print("-" * 80)
        print(f"INFO | Oferta #{index} score={scored.score} aprovado={result.approved}")
        if result.reasons:
            print("WARN | Bloqueios:", "; ".join(result.reasons))
            continue

        approved_drafts.append(draft)
        publish_result = publisher.publish(draft=draft, target=target)
        _print_stdout_safe(publish_result.message)
        print(
            f"INFO | dry_run={publish_result.dry_run} "
            f"sent={publish_result.sent} target={publish_result.target}"
        )

    approved_drafts_tuple = tuple(approved_drafts)

    if args.save_messages_json:
        save_path = Path(args.save_messages_json)
        if _is_root_output_path(save_path):
            _print_save_json_root_warning(save_path)
        try:
            JsonMessageDraftStore(path=save_path).save(approved_drafts_tuple)
        except MessageDraftStoreWriteError as error:
            return _print_save_messages_json_error(error=error)
        print(f"INFO | Mensagens aprovadas salvas em {save_path}")

    if args.save_messages_text:
        save_path = Path(args.save_messages_text)
        if _is_root_output_path(save_path):
            _print_save_json_root_warning(save_path)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                format_message_drafts_for_review(approved_drafts_tuple),
                encoding=REVIEW_TEXT_ENCODING,
            )
        except OSError as error:
            return _print_save_messages_text_error(error=error)
        print(f"INFO | Revisão de mensagens salva em {save_path}")

    if args.save_review_queue_json:
        save_path = Path(args.save_review_queue_json)
        if _is_root_output_path(save_path):
            _print_save_json_root_warning(save_path)
        try:
            JsonMessageReviewQueueStore(path=save_path).save(
                create_pending_review_queue(approved_drafts_tuple)
            )
        except MessageReviewQueueStoreWriteError as error:
            return _print_save_review_queue_json_error(error=error)
        print(f"INFO | Fila de revisão salva em {save_path}")

    return 0


def _run_real_http_diagnostic(marketplace: Marketplace, settings: Settings) -> int:
    if marketplace == Marketplace.MOCK:
        print("WARN | Diagnóstico de HTTP real não se aplica ao marketplace mock.")
        print("AÇÃO | Use --marketplace shopee ou --marketplace amazon.")
        return 0

    try:
        _validate_real_http_ready(marketplace=marketplace, settings=settings)
    except RealHttpValidationError as error:
        return _print_real_http_guard_error(error=error)

    print(f"INFO | Diagnóstico de HTTP real aprovado para marketplace={marketplace.value}")
    print("INFO | Nenhuma chamada HTTP foi executada.")
    print("INFO | Nenhuma publicação foi executada.")
    print("INFO | Nenhum JSON foi salvo automaticamente.")
    return 0


class _InputContext(argparse.Namespace):
    niche: str
    marketplace: Marketplace
    limit: int
    target: str


def _resolve_input_context(
    *,
    niche_arg: str | None,
    marketplace_arg: str | None,
    limit_arg: int | None,
    target_arg: str | None,
    settings: Settings,
    profile: DiscoveryProfile | None,
) -> _InputContext:
    if profile is None and not niche_arg:
        raise DiscoveryProfileError("use --niche ou --profile para definir a busca")

    niche = profile.niche if profile is not None else str(niche_arg).strip().lower()
    if not niche:
        raise DiscoveryProfileError("niche vazio: revise --niche ou o profile configurado")

    if marketplace_arg:
        marketplace = Marketplace(marketplace_arg)
    elif profile is not None:
        marketplace = profile.marketplace
    else:
        marketplace = Marketplace.MOCK

    if limit_arg is not None:
        limit = limit_arg
    elif profile is not None and profile.limit is not None:
        limit = profile.limit
    else:
        limit = settings.max_offers_per_run

    target = target_arg or (profile.target if profile is not None else None) or "grupo-vip-dry-run"
    return _InputContext(niche=niche, marketplace=marketplace, limit=limit, target=target)


def _print_provider_request_preview(
    marketplace: Marketplace,
    settings: Settings,
    niche: str,
    limit: int,
) -> int:
    if marketplace != Marketplace.SHOPEE:
        print("ERRO | Preview de request disponível apenas para Shopee", file=sys.stderr)
        print("AÇÃO | Use --marketplace shopee.", file=sys.stderr)
        return 3

    try:
        _validate_real_http_ready(marketplace=marketplace, settings=settings)
        request = ShopeeProvider(settings=settings).build_search_request(
            keyword=niche,
            limit=limit,
            timestamp=int(time()),
        )
    except ShopeeConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.SHOPEE, error=error)
    except RealHttpValidationError as error:
        return _print_real_http_guard_error(error=error)

    print("INFO | Preview seguro do request da Shopee")
    print(f"INFO | method={request.method}")
    print(f"INFO | url={request.url}")
    for key, value in sorted(_mask_shopee_request_params(request.params).items()):
        print(f"INFO | param.{key}={value}")
    for key, value in sorted(_mask_shopee_request_headers(request.headers).items()):
        print(f"INFO | header.{key}={value}")
    if request.body:
        operation_name = request.body.get("operationName")
        if operation_name:
            print(f"INFO | body.operationName={operation_name}")
        variables = request.body.get("variables")
        if isinstance(variables, dict):
            for key, value in sorted(variables.items()):
                print(f"INFO | body.variables.{key}={value}")
    print("INFO | Nenhuma chamada HTTP foi executada.")
    print("INFO | Nenhuma publicação foi executada.")
    print("INFO | Nenhum JSON foi salvo automaticamente.")
    return 0


def _run_real_http_once(
    marketplace: Marketplace,
    settings: Settings,
    niche: str,
    limit: int,
    profile: DiscoveryProfile | None = None,
) -> int:
    if marketplace == Marketplace.MOCK:
        print("ERRO | Chamada HTTP real não se aplica ao marketplace mock", file=sys.stderr)
        print("AÇÃO | Use --marketplace shopee ou --marketplace amazon.", file=sys.stderr)
        return 3

    try:
        _validate_real_http_ready(marketplace=marketplace, settings=settings)
        collector = CollectorAgent(settings=settings)
        if profile is None:
            offers = collector.collect(
                marketplace=marketplace,
                niche=niche,
                limit=limit,
            )
        else:
            offers = collector.collect_from_profile(profile=profile, limit=limit)
    except ShopeeConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.AMAZON, error=error)
    except RealHttpValidationError as error:
        return _print_real_http_guard_error(error=error)
    except ProviderLimitError as error:
        return _print_provider_limit_error(error=error)
    except ShopeePayloadError as error:
        return _print_payload_error(marketplace=Marketplace.SHOPEE, error=error)
    except ShopeeGraphqlPayloadError as error:
        return _print_payload_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonPayloadError as error:
        return _print_payload_error(marketplace=Marketplace.AMAZON, error=error)
    except ProviderHttpError as error:
        return _print_provider_http_error(marketplace=marketplace, error=error)
    except HttpTransportError as error:
        return _print_transport_error(marketplace=marketplace, error=error)

    print(f"INFO | Chamada HTTP real controlada concluída para marketplace={marketplace.value}")
    print(f"INFO | Ofertas normalizadas recebidas: {len(offers)}")
    print("INFO | Nenhuma publicação foi executada.")
    print("INFO | Nenhum JSON foi salvo automaticamente.")
    return 0


def _validate_real_http_ready(marketplace: Marketplace, settings: Settings) -> None:
    if marketplace == Marketplace.SHOPEE:
        ShopeeProvider(settings=settings).validate_real_http_ready()
        return
    if marketplace == Marketplace.AMAZON:
        AmazonProvider(settings=settings).validate_real_http_ready()
        return


def _mask_shopee_request_params(params: dict[str, Any]) -> dict[str, str]:
    safe_params: dict[str, str] = {}
    for key, value in params.items():
        if key in SHOPEE_MASKED_REQUEST_PARAMS:
            safe_params[key] = _mask_value(value)
        else:
            safe_params[key] = str(value)
    return safe_params


def _mask_shopee_request_headers(headers: dict[str, str]) -> dict[str, str]:
    safe_headers: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SHOPEE_MASKED_REQUEST_HEADERS:
            safe_headers[key] = _mask_value(value)
        else:
            safe_headers[key] = str(value)
    return safe_headers


def _mask_value(value: Any) -> str:
    text = str(value)
    if not text:
        return "<masked>"
    return f"<masked:{len(text)} chars>"


def _is_root_output_path(path: Path) -> bool:
    return not path.is_absolute() and path.parent == Path(".")


def _print_configuration_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Configuração da {marketplace_name} incompleta", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Configure o arquivo .env local ou rode com --marketplace mock.",
        file=sys.stderr,
    )
    return 2


def _print_limit_error(limit: int) -> int:
    print("ERRO | Limite de ofertas inválido", file=sys.stderr)
    print(
        f"DETALHE | --limit deve ser maior que zero. Valor recebido: {limit}",
        file=sys.stderr,
    )
    print(
        "AÇÃO | Informe um valor positivo, por exemplo --limit 5.",
        file=sys.stderr,
    )
    return 3


def _print_discovery_profile_error(error: Exception) -> int:
    print("ERRO | Perfil de descoberta inválido", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Revise o arquivo de perfis ou rode com --niche manual.",
        file=sys.stderr,
    )
    return 3


def _print_missing_discovery_profile_error(slug: str, path: Path) -> int:
    print("ERRO | Perfil de descoberta não encontrado", file=sys.stderr)
    print(f"DETALHE | slug={slug} arquivo={path}", file=sys.stderr)
    print(
        "AÇÃO | Verifique o nome do perfil ou o caminho do arquivo configurado.",
        file=sys.stderr,
    )
    return 3


def _print_provider_limit_error(error: Exception) -> int:
    print("ERRO | Limite interno de provider inválido", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Revise a origem do limite antes de executar novamente.",
        file=sys.stderr,
    )
    return 3


def _print_payload_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Resposta da {marketplace_name} em formato inesperado", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Valide o payload retornado pelo provider antes de publicar ofertas.",
        file=sys.stderr,
    )
    return 3


def _print_provider_http_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Falha na resposta HTTP da {marketplace_name}", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique status, rate limit e disponibilidade antes de nova tentativa.",
        file=sys.stderr,
    )
    return 3


def _print_transport_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Falha de transporte HTTP da {marketplace_name}", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique conexão, timeout e configuração antes de nova tentativa.",
        file=sys.stderr,
    )
    return 3


def _print_real_http_guard_error(error: Exception) -> int:
    print("ERRO | HTTP real bloqueado por configuração insegura", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Revise o checklist de produção antes de habilitar chamadas reais.",
        file=sys.stderr,
    )
    return 3


def _print_real_http_mode_conflict() -> int:
    print("ERRO | Modo de HTTP real inválido", file=sys.stderr)
    print(
        "DETALHE | Use apenas um modo: --diagnose-real-http ou "
        "--execute-real-http-once ou --print-provider-request.",
        file=sys.stderr,
    )
    print("AÇÃO | Rode primeiro o diagnóstico e depois a execução controlada.", file=sys.stderr)
    return 3


def _print_save_json_root_warning(path: Path) -> None:
    print(
        f"WARN | O arquivo {path} será salvo no diretório atual. "
        "Prefira .data/, tmp/ ou exports/ para evitar commit acidental."
    )


def _print_save_json_error(error: Exception) -> int:
    print("ERRO | Não foi possível salvar o JSON de ofertas", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.",
        file=sys.stderr,
    )
    return 3


def _print_save_messages_json_error(error: Exception) -> int:
    print("ERRO | Não foi possível salvar o JSON de mensagens", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.",
        file=sys.stderr,
    )
    return 3


def _print_save_messages_text_error(error: Exception) -> int:
    print("ERRO | Não foi possível salvar o texto de revisão", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.",
        file=sys.stderr,
    )
    return 3


def _print_save_review_queue_json_error(error: Exception) -> int:
    print("ERRO | Não foi possível salvar a fila de revisão", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.",
        file=sys.stderr,
    )
    return 3


def _print_save_inspection_json_error(error: Exception) -> int:
    print("ERRO | Não foi possível salvar a inspeção estruturada da coleta", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.",
        file=sys.stderr,
    )
    return 3


def _build_collection_inspection_payload(
    *,
    marketplace: Marketplace,
    niche: str,
    limit: int,
    search_term: str,
    target: str,
    profile: DiscoveryProfile | None,
    subgroup_slug: str | None,
    offers: list[Any],
    raw_response: dict[str, object] | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "marketplace": marketplace.value,
        "niche": niche,
        "search_term": search_term,
        "target": target,
        "limit": limit,
        "collected_offer_count": len(offers),
        "profile_slug": profile.slug if profile is not None else None,
        "subgroup_slug": subgroup_slug,
        "discovery_method": profile.discovery_method if profile is not None else None,
        "shopee_offer_names": list(profile.shopee_offer_names) if profile is not None else [],
        "shopee_category_urls": list(profile.shopee_category_urls) if profile is not None else [],
        "shopee_product_match_ids": list(profile.shopee_product_match_ids) if profile is not None else [],
        "shopee_product_category_ids": list(profile.shopee_product_category_ids) if profile is not None else [],
    }
    provider_snapshot = _build_provider_snapshot(marketplace=marketplace, raw_response=raw_response)
    return {
        "metadata": metadata,
        "offers": [offer_to_json(offer) for offer in offers],
        "provider_snapshot": provider_snapshot,
    }


def _build_provider_snapshot(
    *,
    marketplace: Marketplace,
    raw_response: dict[str, object] | None,
) -> dict[str, Any]:
    if raw_response is None:
        return {
            "marketplace": marketplace.value,
            "supports_raw_response": False,
        }

    snapshot: dict[str, Any] = {
        "marketplace": marketplace.value,
        "supports_raw_response": True,
        "raw_response": raw_response,
    }
    if marketplace in {Marketplace.MOCK, Marketplace.SHOPEE}:
        connection = _extract_shopee_connection(raw_response)
        if connection is not None:
            nodes = connection.get("nodes")
            page_info = connection.get("pageInfo")
            snapshot["offer_node_count"] = len(nodes) if isinstance(nodes, list) else 0
            snapshot["page_info"] = page_info if isinstance(page_info, dict) else None
    return snapshot


def _extract_shopee_connection(raw_response: dict[str, object]) -> dict[str, Any] | None:
    data = raw_response.get("data")
    if not isinstance(data, dict):
        return None
    connection = data.get("shopeeOfferV2")
    if not isinstance(connection, dict):
        return None
    return connection


def _print_stdout_safe(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding)
        print(safe_text)
def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
