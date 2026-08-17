"""Vendor-neutral OpenTelemetry lifecycle and trace-context integration."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, SpanKind, Tracer

from app.core.config.settings import Settings


class Telemetry:
    """Own an optional per-application tracer provider without global mutation."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.observability.enabled
        self._service_name = settings.observability.service_name
        self._environment = settings.app.environment.value
        self._provider: TracerProvider | None = None
        self._tracer: Tracer | None = None
        self._meter_provider: MeterProvider | None = None
        self._bot_updates_total: Counter | None = None
        self._bot_update_duration_seconds: Histogram | None = None
        self._bot_outbound_messages_total: Counter | None = None
        self._bot_translation_fallback_total: Counter | None = None
        self._bot_translation_missing_total: Counter | None = None
        self._booking_outbox_lag_seconds: Histogram | None = None

    def initialize(self) -> None:
        """Create a local provider only when telemetry has been explicitly enabled."""

        if not self._enabled or self._provider is not None:
            return
        resource = Resource.create(
            {
                "service.name": self._service_name,
                "deployment.environment.name": self._environment,
            }
        )
        provider = TracerProvider(resource=resource)
        self._provider = provider
        self._tracer = provider.get_tracer("spacewhy.http")
        meter_provider = MeterProvider(resource=resource)
        meter = meter_provider.get_meter("spacewhy.bots")
        self._meter_provider = meter_provider
        self._bot_updates_total = meter.create_counter("bot_updates_total")
        self._bot_update_duration_seconds = meter.create_histogram(
            "bot_update_duration_seconds",
            unit="s",
        )
        self._bot_outbound_messages_total = meter.create_counter("bot_outbound_messages_total")
        self._bot_translation_fallback_total = meter.create_counter(
            "bot_translation_fallback_total"
        )
        self._bot_translation_missing_total = meter.create_counter("bot_translation_missing_total")
        self._booking_outbox_lag_seconds = meter.create_histogram(
            "booking_notification_outbox_lag_seconds",
            unit="s",
        )

    @contextmanager
    def start_server_span(self, *, method: str, request_id: str | None) -> Generator[Span | None]:
        """Keep a local server span current for logging and future instrumentation."""

        tracer = self._tracer
        if tracer is None:
            yield None
            return
        with tracer.start_as_current_span(f"HTTP {method}", kind=SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", method)
            if request_id is not None:
                span.set_attribute("http.request.header.x_request_id", request_id)
            yield span

    @contextmanager
    def start_bot_update_span(
        self,
        *,
        bot_app_id: str,
        owner_module: str,
        provider: str,
        request_id: str,
    ) -> Generator[Span | None]:
        """Create a low-cardinality consumer span for one already-selected bot runtime."""

        tracer = self._tracer
        if tracer is None:
            yield None
            return
        with tracer.start_as_current_span("bot.update", kind=SpanKind.CONSUMER) as span:
            span.set_attribute("bot.app_id", bot_app_id)
            span.set_attribute("bot.owner_module", owner_module)
            span.set_attribute("bot.provider", provider)
            span.set_attribute("request.id", request_id)
            yield span

    def record_bot_update(
        self,
        *,
        bot_app_id: str,
        provider: str,
        result: str,
        duration_seconds: float,
    ) -> None:
        """Record bounded-cardinality update outcome and duration metrics when enabled."""

        attributes = {
            "bot_app_id": bot_app_id,
            "provider": provider,
            "result": result,
        }
        if self._bot_updates_total is not None:
            self._bot_updates_total.add(1, attributes)
        if self._bot_update_duration_seconds is not None:
            self._bot_update_duration_seconds.record(duration_seconds, attributes)

    def record_bot_outbound_message(self, *, bot_app_id: str, provider: str, result: str) -> None:
        """Record a safe outbound send outcome with no recipient or message-content labels."""

        if self._bot_outbound_messages_total is not None:
            self._bot_outbound_messages_total.add(
                1,
                {
                    "bot_app_id": bot_app_id,
                    "provider": provider,
                    "result": result,
                },
            )

    def record_bot_translation_fallback(
        self,
        *,
        bot_app_id: str,
        owner_module: str,
        locale: str,
    ) -> None:
        """Record an owned translation fallback without using message keys as labels."""

        if self._bot_translation_fallback_total is not None:
            self._bot_translation_fallback_total.add(
                1,
                {
                    "bot_app_id": bot_app_id,
                    "owner_module": owner_module,
                    "locale": locale,
                },
            )

    def record_bot_translation_missing(
        self,
        *,
        bot_app_id: str,
        owner_module: str,
        locale: str,
    ) -> None:
        """Record an owned missing translation without unbounded key labels."""

        if self._bot_translation_missing_total is not None:
            self._bot_translation_missing_total.add(
                1,
                {
                    "bot_app_id": bot_app_id,
                    "owner_module": owner_module,
                    "locale": locale,
                },
            )

    def record_booking_outbox_lag(self, *, lag_seconds: float) -> None:
        """Record the schedule-to-claim delay without exposing notification metadata."""

        if self._booking_outbox_lag_seconds is not None:
            self._booking_outbox_lag_seconds.record(max(lag_seconds, 0.0))

    async def shutdown(self) -> None:
        """Flush and close the local provider without requiring an external collector."""

        provider = self._provider
        meter_provider = self._meter_provider
        self._tracer = None
        self._provider = None
        self._meter_provider = None
        self._bot_updates_total = None
        self._bot_update_duration_seconds = None
        self._bot_outbound_messages_total = None
        self._bot_translation_fallback_total = None
        self._bot_translation_missing_total = None
        self._booking_outbox_lag_seconds = None
        if provider is not None:
            provider.shutdown()
        if meter_provider is not None:
            meter_provider.shutdown()


def current_trace_id() -> str | None:
    """Return the current OpenTelemetry trace ID when a valid span is active."""

    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return f"{span_context.trace_id:032x}"
