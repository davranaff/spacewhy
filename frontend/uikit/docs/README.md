# Документация Spacewhy Web UI Kit для coding-агентов

Рабочий контракт для `frontend/uikit`: Next.js App Router, React, TypeScript,
MUI и Spacewhy Liquid Glass.

## Карта документации

| Документ | Когда читать |
|---|---|
| [architecture.md](architecture.md) | Перед добавлением route, provider, state или новой папки |
| [components-and-patterns.md](components-and-patterns.md) | Перед выбором MUI/custom component, формы, таблицы или feedback pattern |
| [glass-theme-settings.md](glass-theme-settings.md) | Для темы, CSS variables, glass depth и settings drawer |
| [routes-layouts-data.md](routes-layouts-data.md) | Для App Router, layouts, auth, Redux и mock/API режима |
| [agent-workflow.md](agent-workflow.md) | Для реализации web component/page и переноса в mobile |
| [testing-and-qa.md](testing-and-qa.md) | Перед handoff, commit и push |
| [Общий web/mobile контракт](../../docs/README.md) | Для cross-platform parity |

## Текущий scope

- 133 `page.tsx` routes;
- 5 foundation component routes;
- 29 MUI component routes;
- 20 Extra component routes;
- public marketing, auth variants, product/post/payment pages;
- full dashboard families: overview, management, workspace и system;
- vertical, mini и horizontal dashboard navigation;
- light/dark, LTR/RTL, contrast, presets, stretch и liquid-glass settings.

## Быстрый выбор

| Задача | Использовать |
|---|---|
| Layout и responsive composition | MUI `Box`, `Stack`, `Grid`, `Container` |
| Content card | MUI `Card`/`Paper`; global glass override уже применён |
| Специальная glass surface | `liquidGlass()` из `src/theme/css.ts` |
| Form state и validation | React Hook Form + Yup + `src/components/hook-form` |
| Data table | `src/components/table` + MUI Table; DataGrid для virtualized grid |
| Menu/popover | `CustomPopover` + `usePopover` |
| Confirmation | `ConfirmDialog` |
| Toast feedback | Notistack через shared Snackbar provider |
| Upload | `src/components/upload` |
| Image | `src/components/image` |
| Icon | `Iconify` или существующая typed/local asset family |
| Route path | Только `src/routes/paths.ts` |
| Dashboard page | `src/app/dashboard/**/page.tsx` + `src/sections/<domain>` |
| Component demo | `src/app/components/**/page.tsx` + `src/sections/_examples` |

## Неприкосновенные правила

1. Не удалять или сокращать route inventory ради redesign/refactor.
2. Не менять UX/concept существующего component/page без явного запроса.
3. Не дублировать MUI theme styling локально, если он уже задан override.
4. Не писать raw glass values вместо `liquidGlass()` или CSS variables.
5. Не монтировать Redux во всём root: он ограничен dashboard/storefront scope.
6. Не заставлять public/component routes ждать auth splash или persistence.
7. Не использовать remote Minimals assets/branding. Только Spacewhy/local assets.
8. Не делать внутреннюю ссылку `target="_blank"` с external icon.
9. Не использовать mouse-only `Box onClick`; action должен иметь native button/
   link semantics и keyboard behavior.
10. Не оставлять component catalog example статичной картинкой вместо реального
    варианта и interaction.
