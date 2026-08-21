# Web architecture

## Runtime chain

```text
src/app/layout.tsx
├── AuthProvider (JWT demo/remote boundary)
├── LocalizationProvider
├── SettingsProvider
├── ThemeProvider
│   ├── MUI theme
│   ├── RTL
│   ├── CssBaseline
│   └── Spacewhy glass CSS variables
├── MotionLazy
├── SnackbarProvider
├── LazySettingsDrawer
├── ProgressBar inside Suspense
└── route segment layout -> page -> section
```

Root providers монтируются один раз. Feature/page не должен создавать второй
MUI theme, settings или auth provider.

## Слои

| Путь | Ответственность |
|---|---|
| `src/app` | App Router entry files: `layout`, `page`, route params |
| `src/sections` | Page-level feature views и domain composition |
| `src/components` | Reusable cross-domain UI и wrappers |
| `src/layouts` | Main, dashboard, auth, compact, simple shells |
| `src/theme` | Palette, typography, shadows, component overrides, glass tokens |
| `src/routes` | Central paths, link components/hooks |
| `src/auth` | Auth providers, hooks, guards |
| `src/redux` | Dashboard/storefront domain state only |
| `src/_mock` | Local deterministic demo data/API adapter |
| `src/hooks` | Reusable behavior hooks |
| `src/utils` | Pure format/transform helpers |
| `src/types` | Cross-domain shared types |
| `public/assets` | Local runtime imagery, icons and illustrations |

## Dependency direction

```text
app -> layouts/sections -> components -> theme/hooks/utils/types
                 |              |
                 +-> domain state/auth/mock
```

- `page.tsx` должен быть тонким: metadata/params + import section view.
- Domain-specific code остаётся в `sections/<domain>`.
- Generic component не импортирует section или route page.
- Theme override не импортирует feature state.
- Utility не рендерит React и остаётся pure.

## Server и client boundaries

App Router file остаётся server component, пока ему не нужны hooks, browser API
или client-only library. Добавляйте `'use client'` на минимально возможной
boundary, обычно section view или leaf component.

Не помечайте общий layout/page client-only только ради одного control. Это
увеличивает client bundle и может вернуть задержки между страницами.

Client-only тяжёлые modules загружайте dynamic import при необходимости:

- maps;
- organizational chart;
- editor;
- browser-only chart/media adapters;
- settings drawer до первого открытия.

## Folder/file conventions

- Один component/view на файл, если он имеет самостоятельную ответственность.
- `index.ts` — публичный barrel конкретного component module.
- Page views обычно называются `*-view.tsx` и экспортируются через локальный
  `view/index.ts` при наличии нескольких variants.
- Form делится на form component, schema/types и focused subcomponents.
- Table/list family делит toolbar, row, filters, utils и view.
- Не создавайте `helpers.ts` как свалку: pure domain helper называть по смыслу.

## Public component imports

Предпочитайте module barrel:

```tsx
import CustomPopover, { usePopover } from 'src/components/custom-popover';
import FormProvider, { RHFTextField } from 'src/components/hook-form';
import { TableHeadCustom, useTable } from 'src/components/table';
```

Глубокий import допустим внутри самого module или когда barrel намеренно не
экспортирует private implementation.

## State ownership

| State | Владелец |
|---|---|
| Theme/layout/glass preferences | Settings context + localStorage |
| Form values/errors | React Hook Form |
| Table pagination/sort/selection | `useTable` + view state |
| Server/remote domain data | Domain API/state layer |
| Dashboard shared client state | Redux slice where justified |
| Dialog/menu toggle | Local state or focused hook |
| Route identity | App Router params/pathname |

Не переносите локальный popover/dialog state в Redux. Не храните один form в
двух state systems.

## Performance boundaries

- Root progress bar изолирован `Suspense`, чтобы `useSearchParams` не deopt всех
  routes.
- Redux не монтируется на public/component routes.
- Settings drawer code-split.
- Glass settings обновляют CSS variables, а не пересоздают MUI theme на каждый
  slider tick.
- Большие route families не должны импортироваться в root barrel.
- Remote image failure не должен блокировать layout: runtime assets локальны.
