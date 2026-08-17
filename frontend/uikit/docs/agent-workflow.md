# Workflow coding-агента для web UI kit

## 1. Зафиксировать scope

Определите, что меняется:

- reusable component;
- theme/glass system;
- component catalog example;
- domain section;
- route/layout;
- auth/data behavior;
- asset/identity;
- cross-platform parity.

Не превращайте исправление одного component в redesign всего template без
явного запроса.

## 2. Найти существующий contract

Перед созданием нового кода ищите в таком порядке:

```sh
rg "ComponentName|route-fragment|visible copy" src
rg --files src/components src/sections src/app
```

Проверьте:

- MUI primitive;
- Spacewhy wrapper в `src/components`;
- example в `src/sections/_examples`;
- похожий domain pattern;
- global theme override;
- path constant;
- mobile counterpart, если требуется parity.

## 3. Сохранить anatomy и UX

Для redesign/branding task сохраняйте:

- структуру component;
- hierarchy;
- действия;
- states;
- route map;
- data density;
- responsive behavior.

Меняются Spacewhy visual tokens, assets и copy, но не исчезают важные variants
или страницы.

## 4. Выбрать правильный слой

| Код | Путь |
|---|---|
| Generic reusable UI | `src/components/<name>` |
| Domain-specific UI | `src/sections/<domain>` |
| Page entry | `src/app/<route>/page.tsx` |
| Shell | `src/layouts` |
| Global styling | `src/theme` |
| URL | `src/routes/paths.ts` |
| Demo data | `src/_mock` |
| Shared client domain state | `src/redux` |

## 5. Реализовать states до polish

Минимальная matrix для data UI:

- loading;
- success;
- empty;
- filtered no results;
- error;
- retry/recovery;
- disabled/pending mutation.

Для control: default, hover, focus-visible, active, selected, disabled, error и
long label. Для overlay: open, keyboard navigation, Escape, outside click,
focus restore.

## 6. Использовать theme и glass system

- Layout через MUI `sx` и theme spacing/breakpoints.
- Palette через semantic theme roles.
- Repeated component styling через override.
- Special glass через `liquidGlass()`.
- Raw CSS variables только из documented glass token family.
- No decorative colored accent вне semantic role.

## 7. Responsive и accessibility

Проверяйте минимум 390, 768, 1280 и wide desktop widths.

- Нет horizontal overflow.
- Sidebar/header не обрезают content.
- Mobile drawer закрывается и возвращает body scroll.
- Keyboard может открыть/закрыть disclosure.
- Focus visible.
- Dialog/menus имеют корректную semantic model.
- Controls имеют names и target size.
- RTL не выходит за viewport.
- Reduced motion отключает perpetual/decorative loops.

## 8. Cross-platform перенос

Если задача касается mobile counterpart:

1. составьте web anatomy/variant matrix;
2. сохраните stable ID и visible naming;
3. выберите native primitive;
4. перенесите states/actions, не DOM;
5. сопоставьте glass role;
6. обновите web и mobile docs/tests при изменении общего contract.

Подробности: [общий web/mobile контракт](../../docs/README.md).

## 9. Проверка

```sh
npm test
npm run lint -- --no-cache
npx tsc --noEmit --incremental false
npm run build
git diff --check
```

`npm run build` обязателен после route/layout/provider/dynamic import/theme
изменений. Для focused leaf change допускается сначала targeted gate, но перед
publish нужен полный.

## Запрещённые shortcuts

- Удалить route/component, потому что он не нужен текущему screenshot.
- Переписать MUI component вручную без причины.
- Добавить `'use client'` в root ради leaf hook.
- Монтировать Redux/Auth provider глобально ради одной страницы.
- Дублировать glass formulas в feature.
- Mouse-only click target.
- No-op link/button.
- Remote legacy asset.
- Static fake UI image вместо реального component preview.
- Скрыть build/lint warning без анализа причины.
- Коммитить `.next`, cache, secret или `.env`.

## Definition of done

- [ ] Route/component inventory сохранён либо изменён намеренно.
- [ ] Existing UX/anatomy не потеряны.
- [ ] Spacewhy identity и local assets использованы.
- [ ] Правильный архитектурный слой.
- [ ] Server/client boundary минимальна.
- [ ] States и recovery реализованы.
- [ ] Light/dark, responsive, RTL и keyboard проверены.
- [ ] Glass не создаёт repaint regression.
- [ ] Tests, lint, TypeScript, build и diff check зелёные.
- [ ] Mobile counterpart/documentation обновлены, если общий contract изменён.
