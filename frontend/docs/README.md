# Spacewhy UI Kit: общий контракт для web и mobile

В repository существуют два самостоятельных UI kit:

| Platform | Package | Documentation |
|---|---|---|
| Web | `frontend/uikit` | [Web guide](../uikit/docs/README.md) |
| iOS/Android | `frontend/uikit-mobile` | [Mobile guide](../uikit-mobile/docs/README.md) |

Они разделяют Spacewhy identity, semantic hierarchy и component/page inventory,
но не implementation API. Web использует Next.js, React и MUI. Mobile использует
Bare React Native и native platform controls.

## Что должно совпадать между платформами

- назначение component/page;
- naming и stable catalog identity;
- information hierarchy;
- варианты и состояния;
- semantic colors;
- loading, empty, error и recovery;
- доступные пользовательские действия;
- accessibility intent;
- Spacewhy content и branding.

## Что не должно копироваться буквально

| Web | Mobile adaptation |
|---|---|
| Hover | Press/long press или видимое действие |
| Desktop mega-menu | Sheet, disclosure или stack navigation |
| MUI component props | Typed native component API |
| CSS backdrop filter | `GlassView` platform boundary |
| Dense data table | Virtualized list/cards/detail flow |
| Browser URL | Typed route + optional custom-scheme deep link |
| Fixed desktop grid | Safe-area aware responsive phone layout |
| DOM focus model | Native accessibility focus model |

## Правило переноса

Web UI kit — источник состава, variants и page anatomy. Mobile UI kit — источник
нативного interaction contract. Агент сначала проводит audit web implementation,
затем переносит смысл и состояния на native primitives, не создавая новый дизайн
и не имитируя web через screenshots.

## Общий checklist

- [ ] Найден существующий component/page на обеих платформах.
- [ ] Составлена variant/state matrix.
- [ ] Использованы platform-owned primitives.
- [ ] Spacewhy glass role выбран одинаково по смыслу: surface/control/floating.
- [ ] Theme и status semantics совпадают.
- [ ] Light/dark проверены на обеих платформах.
- [ ] Entry reachable из catalog/navigation.
- [ ] Tests подтверждают ID/inventory/behavior.
- [ ] Не заявлена parity для ещё не перенесённых вариантов.
