# Документация Spacewhy UI Kit Mobile для coding-агентов

Эта папка — рабочий контракт для агентов, которые изменяют
`frontend/uikit-mobile`. Она описывает не только расположение файлов, но и
правила выбора компонентов, допустимые зависимости, перенос web UI kit в
React Native и обязательную проверку результата.

## Что считать источником правды

При конфликте информации используйте такой порядок:

1. TypeScript-типы и публичные exports текущей mobile-сборки.
2. Эта документация.
3. Реальное поведение соответствующей страницы в `frontend/uikit`.
4. Скриншоты и старые commit-состояния как визуальная справка.

Web UI kit определяет состав, смысл, варианты и состояния компонента. Mobile
UI kit определяет нативную реализацию, жесты, safe area, accessibility и
platform fallback. Переносить DOM или MUI API один к одному нельзя.

## Карта документации

| Документ | Когда читать |
|---|---|
| [architecture.md](architecture.md) | Перед добавлением файлов, слоя, store, route или native dependency |
| [components.md](components.md) | Перед выбором или созданием UI-компонента |
| [glass-theme-settings.md](glass-theme-settings.md) | Для glass surface, slider, темы, токенов и настроек материала |
| [navigation-and-dock.md](navigation-and-dock.md) | Для экранов, stack/tab routes, deep links, dock и player UI |
| [catalog-showcase-templates.md](catalog-showcase-templates.md) | Для переноса web-компонента, страницы или dashboard template |
| [agent-workflow.md](agent-workflow.md) | Для пошаговой реализации и review checklist |
| [testing-and-qa.md](testing-and-qa.md) | Перед handoff, commit и push |

## Текущий состав

| Область | Состав |
|---|---:|
| Foundations | 5 catalog entries |
| MUI parity catalog | 29 native counterparts |
| Extra catalog | 20 advanced components |
| Dashboard templates | 41 stable web-path descriptors |
| Native template contracts | 14 renderer kinds |
| Showcase routes | 10 end-to-end demo screens |
| Primary dock destinations | 5 stable tabs |

Название `MUI` сохраняется только как taxonomy для соответствия web UI kit.
Пакет `@mui/*` в React Native не используется.

## Быстрый выбор

| Задача | Использовать |
|---|---|
| Обычная информационная стеклянная плашка | `GlassView variant="surface"` |
| Стеклянный control или selection blob | `GlassView variant="control"` |
| Dock, popover, modal-like floating layer | `GlassView variant="floating"` |
| Ползунок | Только `GlassSlider`, без custom thumb overlay |
| Семантический цвет, spacing, radius, type | `useAppTheme()` |
| Глобальная тема, locale, glass или dock settings | `useAppSettingsStore()` |
| Карточка внутри catalog preview | `DemoSurface` |
| Кнопка внутри catalog preview | `DemoButton` |
| Product screen button | Собственный feature-component на `Pressable`, а не `DemoButton` |
| Основная навигация | `TabDock`, только через React Navigation tab bar |
| 1–4 контекстных действия | `ContextualDock` |
| Активный media queue | `MiniPlayerDock` через player-aware integration |
| Новый web component counterpart | `features/catalog` + typed `CatalogExampleId` |
| Новая dashboard page family | `features/templates` + `screens/templates` |
| End-to-end product flow | `features/showcase` + `screens/showcase` |

## Неприкосновенные правила

1. Не импортировать `@callstack/liquid-glass` или
   `@react-native-community/blur` вне `src/shared/ui/glass-view.tsx`.
2. Не рисовать собственный thumb поверх `GlassSlider`: нативный `UISlider`
   владеет размером, idle-состоянием и liquid-glass transition при нажатии.
3. Не использовать случайные hex-цвета, spacing и radius в product UI, если
   существует semantic token.
4. Не добавлять новый tab в primary dock для отдельного demo. Использовать
   typed stack route, catalog preview, template или showcase route.
5. Не объявлять parity только по совпавшему названию. Должны быть перенесены
   варианты, состояния, действия, ошибки, loading/empty и accessibility.
6. Не добавлять Expo. Это Bare React Native package.
7. Не оставлять screen/component недостижимым: каждый public example должен
   открываться из catalog, template library или typed route.

## Что сейчас ещё не завершено

В repository memory остаются две P1 parity-задачи: перенос 37
non-dashboard/non-component web pages и полный per-variant аудит foundation/base
previews. Новые изменения не должны скрывать эти gaps общими словами вроде
«полная parity», пока audit реально не закрыт.
