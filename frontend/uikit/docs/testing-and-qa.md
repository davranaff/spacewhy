# Web testing и QA

## Полный quality gate

Из `frontend/uikit`:

```sh
npm test
npm run lint -- --no-cache
npx tsc --noEmit --incremental false
npm run build
git diff --check
```

Build должен сохранять ожидаемый route inventory. Сейчас baseline — 133
`page.tsx` source entries; optimized Next output может группировать routes иначе.

## Запуск

```sh
npm run dev
```

Dev server использует `http://localhost:8081`.

Production-like check:

```sh
npm run build
npm run preview
```

Не оценивайте route latency только по первому dev transition: он может включать
on-demand compilation. Повторите переход и сравните с production preview.

## Automated test scope

Текущие Node tests покрывают pure settings/glass/brand/local-demo contracts.
Добавляйте tests для:

- clamp/interpolation и независимости glass axes;
- settings normalization и corrupted persisted value;
- local demo API routes/search/details;
- route/path helpers;
- pure table/filter/format logic;
- identity config;
- regression, которая уже ломала UI.

Component behavior, который зависит от DOM, проверяйте подходящим browser/
component test при добавлении infrastructure; до этого требуется ручной runtime
QA и максимально pure extracted logic.

## Route smoke

Проверьте минимум:

```text
/
/components
/dashboard
/dashboard/mail
/dashboard/calendar
/auth/jwt/login
/auth/jwt/register
/product
/post
/404
```

Для каждого: HTTP success/expected status, direct load, client transition,
refresh, back/forward, visible shell.

## Responsive matrix

| Width | Проверить |
|---:|---|
| 390 px | Mobile header/drawer, forms, tables/cards, no overflow |
| 768 px | Tablet transitions и grids |
| 1280 px | Standard desktop dashboard |
| 1600+ px | Stretch/max-width и wide charts |

Dashboard отдельно проверить в vertical, mini и horizontal layouts.

## Theme/settings matrix

- dark/light;
- default/bold contrast;
- LTR/RTL;
- vertical/mini/horizontal;
- stretch on/off;
- все supported presets;
- glass sliders на `0`, defaults и `100`;
- Reset;
- reload/persistence.

## Accessibility QA

- Keyboard tab order.
- Visible focus.
- Dropdown ArrowDown/Escape/focus return.
- Dialog focus trap/Escape/title association.
- Icon button names.
- Form label/helper/error association.
- Row checkbox label.
- No invalid nested interactive elements.
- Reduced motion.
- Semantic headings.
- Zoom 200% без потери действий.

## Performance QA

Разделите измерение:

1. server response;
2. JS chunk download/compile;
3. auth/settings hydration;
4. React render;
5. image/font/network;
6. layout/paint/composite.

Проверьте Chrome Performance и Network:

- нет 10–15 секунд повторной задержки;
- нет failed remote asset requests;
- нет provider remount при route transition;
- нет full-page client render deopt из root hook;
- нет long task от unvirtualized data;
- нет continuous glass repaint;
- bundle не получил крупную библиотеку на every route.

## Visual regression checklist

- Navbar/sidebar полностью видимы и не обрезаны.
- Header width соответствует content viewport.
- Cards не перекрываются и не выходят за grid.
- Popover arrow не clipped.
- Charts resize после layout mode change.
- Light glass видим, но не opaque.
- Dark glass имеет depth без лишних бликов.
- Spacewhy logo/assets правильные.
- Ни одного visible Minimals mention/asset, кроме legal provenance в license.

## Handoff evidence

В результате агент сообщает:

- изменённые areas;
- route count до/после;
- test/lint/typecheck/build result;
- runtime routes и viewports;
- measured repeated transition, если задача performance;
- screenshots только как дополнительное evidence;
- известные gaps и warnings.

Нельзя писать «готово» только потому, что TypeScript скомпилировался.
