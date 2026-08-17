# Catalog, showcase и templates

## Три разные системы

| Система | Цель | Не использовать для |
|---|---|---|
| Catalog | Изолированно показать component/foundation с вариантами | Полный product flow |
| Showcase | Проверить связанный mobile flow: auth, data, communication, account | Массовое зеркало всех web routes |
| Templates | Дать reachable native preview каждой dashboard page family | Backend-ready production screen |

Выберите одну систему до начала реализации. Не дублируйте один пример сразу во
всех трёх без отдельной UX-причины.

## Catalog architecture

```text
features/catalog/
├── data/catalog-data.ts             # descriptors, sections, search
├── data/catalog-icon-registry.ts    # stable ID -> local artwork
├── types/catalog.types.ts           # closed ID unions
├── components/catalog-primitives.tsx
├── components/catalog-example-preview.tsx  # top-level renderer dispatch
├── components/catalog-control-preview.tsx  # control/overlay parity
└── components/catalog-parity-preview.tsx   # advanced parity
```

Inventory: 5 foundations + 29 MUI parity + 20 Extra = 54 entries.

### Renderer layers

Dispatch order в `CatalogExamplePreview`:

1. `CONTROL_PARITY_EXAMPLES` — controls, feedback и overlays с точными states;
2. `PARITY_EXAMPLES` — media, document, navigation и structured components;
3. focused base/foundation previews в top-level switch.

ID является публичным route contract. Renderer reuse допустим только когда
реально совпадает interaction contract, а не потому что два компонента визуально
похожи.

## Как перенести web component в catalog

1. Откройте соответствующий route в `frontend/uikit`.
2. Зафиксируйте anatomy: trigger, content, labels, helper text, icons.
3. Составьте variant/state matrix: default, selected, disabled, loading, empty,
   error, destructive, overflow, long text.
4. Определите нативный interaction contract вместо копирования web DOM.
5. Добавьте stable literal ID в union `CatalogExampleId`.
6. Добавьте descriptor и search keywords в `catalog-data.ts`.
7. Добавьте локальный Spacewhy artwork и mapping в icon registry.
8. Реализуйте preview в правильном renderer layer.
9. Обеспечьте реальное управление: tap, input, drag, dismiss, retry и reset.
10. Проверьте route reachability из нужной tab-section.
11. Добавьте data/renderer tests.
12. Сравните web и native side by side по matrix, а не только screenshot.

### Definition of parity

Parity означает сохранение:

- назначения;
- информационной иерархии;
- вариантов;
- состояний;
- доступных действий;
- feedback;
- ошибок и recovery;
- accessibility semantics.

Pixel-identical geometry между desktop web и phone не требуется и часто
вредна. Native control, gesture и platform convention имеют приоритет.

## Artwork rules

Catalog artwork хранится локально в `src/assets/component-icons` и выбирается
через `CATALOG_ICON_REGISTRY`.

- Имя файла связано со stable ID.
- Все IDs обязаны иметь mapping.
- Не использовать remote URL для catalog icon.
- Не возвращать старые Minimals logos/brand marks.
- Не подменять artwork emoji.
- Проверять scale на @2x/@3x simulator и обеих themes.

## Showcase architecture

`features/showcase` владеет data, descriptors и validation. `screens/showcase`
владеет route-level UI. `app/navigation/showcase-route-adapters.tsx` передаёт
navigation callbacks, поэтому raw screen registry нельзя регистрировать без
adapter, если screen ожидает `onOpenRecord` или другое действие.

Текущие 10 routes:

| Group | Routes |
|---|---|
| Auth | Login, Register |
| Dashboard | Dashboard |
| Management | Records, Record detail, Record form |
| Communication | Mail, Chat, Calendar |
| Account | Profile/Settings |

Showcase честно обозначает local demo. Не заявляйте создание account, remote
save или backend sync, если действие остаётся локальным.

### Preview states

Data-oriented showcase должен поддерживать typed state:

```ts
type ShowcasePreviewState = 'success' | 'loading' | 'empty' | 'error';
```

Loading, empty и error должны быть selectable/reachable для QA, а не мёртвым
conditional code.

## Template architecture

```text
features/templates/
├── data/dashboard-template-data.ts       # 41 descriptors
├── types/dashboard-template.types.ts     # ID/group/kind contracts
└── components/dashboard-template-preview.tsx

screens/templates/
├── template-library-screen.tsx
└── template-preview-screen.tsx
```

41 stable descriptors сгруппированы в:

- `overview`;
- `management`;
- `workspace`;
- `system`.

Они рендерятся через 14 native layout kinds:

```text
overview, profile, cards, list, detail, form, account,
file-manager, mail, chat, calendar, kanban, permission, blank
```

CRUD families могут использовать общий structural renderer, но обязаны
передавать family-specific fields, metrics, row content и actions. Одинаковый
generic list с разным title не считается переносом страницы.

## Как добавить template

1. Добавьте literal ID в `DashboardTemplateId`.
2. Выберите существующий `DashboardTemplateKind` только если anatomy совпадает.
3. Добавьте descriptor с `webPath`, group, family, description и keywords.
4. Добавьте family-specific preview data/behavior.
5. Если anatomy принципиально новая, добавьте новый kind и renderer.
6. Убедитесь, что library search находит template.
7. Проверьте `spacewhyuikit://templates/:templateId`.
8. Добавьте data test и interaction test.

## Что переносить следующим

Перед созданием нового invented screen сравните запрос с текущими open parity
gaps. Приоритет — отсутствующие public marketing, auth variants,
checkout/payment, errors и utility pages, затем variant audit foundation/base
previews.

## Catalog/template review checklist

- [ ] Stable ID добавлен в type union.
- [ ] Descriptor и keywords добавлены.
- [ ] Local artwork существует и mapped.
- [ ] Entry reachable из UI и deep link при необходимости.
- [ ] Web anatomy и variant matrix записаны до реализации.
- [ ] Native behavior не заменён статичным screenshot.
- [ ] Loading/empty/error/disabled состояния доступны.
- [ ] Long text и Dynamic Type не ломают layout.
- [ ] Light/dark и glass settings проверены.
- [ ] Test подтверждает inventory и routing contract.
