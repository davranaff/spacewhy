"""Finance runtime assembly."""

from dataclasses import dataclass

from app.core.db.database import Database
from app.modules.finance.application.service import FinanceService


@dataclass(frozen=True, slots=True)
class FinanceModuleRuntime:
    service: FinanceService


def create_finance_runtime(*, database: Database) -> FinanceModuleRuntime:
    return FinanceModuleRuntime(service=FinanceService(database=database))
