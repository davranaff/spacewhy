# Web components и patterns

## Сначала MUI, затем Spacewhy wrapper

Выбирайте MUI primitive, если он уже выражает нужную семантику. Создавайте
Spacewhy wrapper, когда нужно хотя бы одно из следующего:

- единый повторяющийся API проекта;
- интеграция нескольких MUI primitives;
- accessibility behavior, которое легко реализовать неверно;
- third-party library boundary;
- повторяющийся domain-independent pattern.

Не создавайте `SpacewhyBox`, `SpacewhyStack` или `SpacewhyButton` только ради
переименования MUI.

## Layout primitives

| Задача | Component |
|---|---|
| Одномерный flow | `Stack` |
| Responsive container/positioning | `Box` |
| Page max-width | `Container` |
| Двумерная responsive сетка | `Grid` |
| Content grouping | `Card` / `Paper` |
| Repeated semantic rows | `List` / table primitives |

Используйте breakpoint values из theme. Не фиксируйте desktop width без mobile/
tablet fallback. Проверяйте `minWidth: 0` у flex children с длинным текстом.

## Buttons и links

- Primary action: `Button variant="contained"`.
- Secondary glass action: `outlined` или project `soft` variant.
- Low-priority action: text button.
- Icon-only action: `IconButton` с `aria-label`.
- Internal navigation: Next/route link integration, без `target="_blank"`.
- External destination: `target="_blank"`, `rel="noopener"` и понятный external
  affordance.

Disabled action не должен выглядеть как error. Loading action должен сохранять
ширину и сообщать состояние assistive technology.

## Forms

Стандарт: React Hook Form + Yup + wrappers из `src/components/hook-form`.

```tsx
const methods = useForm<FormValues>({
  resolver: yupResolver(schema),
  defaultValues,
});

return (
  <FormProvider methods={methods} onSubmit={methods.handleSubmit(onSubmit)}>
    <RHFTextField name="email" label="Email" />
  </FormProvider>
);
```

### Выбор field wrapper

| Data | Component |
|---|---|
| Text, email, password, multiline | `RHFTextField` |
| Boolean | `RHFSwitch` / RHF checkbox |
| Exclusive choice | `RHFRadioGroup` |
| Single/multi select | RHF select exports |
| Searchable choice | `RHFAutocomplete` |
| Numeric range | `RHFSlider` |
| Rich text | `RHFEditor` |
| File/avatar | RHF upload exports |
| Verification code | `RHFCode` |

Rules:

- schema — источник validation rules;
- label/helper/error связаны через field semantics;
- password toggle имеет label и pressed/expanded state;
- submit error видим текстом, не только snackbar;
- async submit защищён от double submit;
- edit form получает normalized default values;
- после reset controlled third-party fields синхронизируются.

## Tables и data grids

Используйте `src/components/table` для standard CRUD table:

- `useTable` — pagination, dense, sort, selection;
- `TableHeadCustom` — typed headers и sort;
- `TableSelectedAction` — bulk actions;
- `TableEmptyRows` — стабильная высота страницы;
- `TableNoData` — empty/filter no-results;
- `TableSkeleton` — loading;
- `TablePaginationCustom` — pagination/density.

`@mui/x-data-grid` использовать для virtualized grid, column model и большой
интерактивной dataset. Не смешивать два table state managers в одном view.

Обязательные состояния: loading, rows, empty dataset, no filter results, error,
selected rows. Checkbox имеет row-specific accessible label.

## Feedback и overlays

| Pattern | Использовать |
|---|---|
| Короткий transient result | Snackbar/notistack |
| Persistent contextual status | MUI Alert |
| Destructive/important decision | `ConfirmDialog` |
| Small anchored actions | `CustomPopover` + `usePopover` |
| Menu selection | `MenuItem` внутри popover/menu semantics |
| Complex task requiring focus containment | MUI Dialog |
| Empty content region | `EmptyContent` |
| Full route wait | `LoadingScreen`; редко |

Popover `sx` может быть object, function или array; не object-spread `SxProps`.
`CustomPopover` уже нормализует эти варианты и отключает paint containment,
чтобы arrow не обрезался.

Dialog должен иметь title/description association, focus trap, Escape close и
focus restoration. Не объявляйте `role="dialog"` на обычном `Paper` без modal
behavior.

## Media и content components

| Component | Использовать для |
|---|---|
| `Image` | Lazy image, ratio, placeholder/fallback |
| `Lightbox` | Fullscreen gallery |
| `Carousel` | Bounded swipe/arrow media sequence |
| `FileThumbnail` | File identity, preview/download/remove |
| `Upload*` | Dropzone, validation, preview, progress/error |
| `Editor` | Rich text editing boundary |
| `Markdown` | Render trusted/filtered structured markdown |
| `Chart` + `useChart` | ApexCharts configuration boundary |
| `Map*` | Mapbox markers, popups, controls |

Heavy browser-only component грузить только на route, где он нужен. Для media
задавайте dimensions/aspect ratio, чтобы избежать layout shift.

## Navigation components

- `NavSectionVertical` — full dashboard/sidebar navigation.
- `NavSectionMini` — compact desktop navigation.
- `NavSectionHorizontal` — desktop horizontal mode.
- `MegaMenuMobile/Desktop*` — public complex navigation.
- `CustomBreadcrumbs` — route hierarchy, а не история браузера.

Item с children должен иметь один реальный disclosure trigger. Не вкладывайте
`button` внутрь `a` и не прикрепляйте `aria-expanded` к нефокусируемому child.
Если используется `role="menu"`, descendants и keyboard model обязаны
соответствовать menu semantics; иначе используйте navigation/disclosure region.

## Icons, labels и identity

- `Iconify` — существующие icon IDs и consistent size.
- `SvgColor` — local monochrome SVG, которому нужен theme color.
- `Label` — compact semantic status.
- `Logo` — только Spacewhy logo assets.
- Catalog hero icons берутся из local Spacewhy assets.

Не использовать emoji как control icon. Не вводить новую icon family в одной
feature без design reason.

## Component catalog как reference

Routes находятся в:

```text
src/app/components/foundation/*
src/app/components/mui/*
src/app/components/extra/*
```

Interactive implementations находятся в `src/sections/_examples`. Перед
использованием component откройте его route и проверьте все представленные
variants. Catalog route нельзя сокращать до одного состояния при refactor.

## Accessibility baseline

- Native `button`, `a`, input semantics прежде custom roles.
- Visible focus для keyboard.
- Icon button всегда имеет accessible name.
- Form error связан с field.
- Table selection названо по row.
- Disclosure сообщает `expanded` и controls target.
- Modal управляет focus.
- Motion уважает `prefers-reduced-motion`.
- Цвет не единственный indicator.
- Touch target подходит для touch-capable browser.
