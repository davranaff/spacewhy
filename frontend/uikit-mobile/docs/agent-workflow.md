# Workflow для coding-агента

## 1. Определить точный тип задачи

До изменения кода классифицируйте запрос:

| Запрос | Основной путь |
|---|---|
| Новый reusable primitive | `shared/ui` |
| Новая feature behavior | `features/<feature>` |
| Крупная reusable UI region | `widgets/<widget>` |
| Новый route | `screens` + `app/navigation` |
| Перенос web component | `features/catalog` |
| Перенос dashboard page | `features/templates` |
| Связанный demo flow | `features/showcase` + `screens/showcase` |
| Theme/glass/dock preference | `shared/settings` + соответствующий consumer |

Если задача уже покрывается текущим component contract, расширьте его
вариантом. Не создавайте рядом почти идентичный component с другим именем.

## 2. Изучить source of truth

Перед переносом web UI:

1. найдите route/component в `frontend/uikit`;
2. найдите существующий mobile ID, descriptor и preview;
3. проверьте старый approved commit только если пользователь на него указал;
4. сравните behavior, а не один screenshot;
5. составьте список states и platform adaptations.

Для slider approved reference — `88886b0`: native thumb, без overlay.

## 3. Сохранить архитектурные границы

- Используйте `@/` imports.
- Снаружи feature импортируйте public barrel.
- Screen собирает feature/widget, но не содержит domain store целиком.
- Shared не знает о catalog/showcase/templates.
- Native package скрывается за boundary.
- Один owner на persisted state.
- Не меняйте primary dock taxonomy ради одной задачи.

## 4. Реализовать complete state model

До JSX определите типы:

```ts
type RequestState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: readonly Item[] }
  | { status: 'empty' }
  | { status: 'error'; message: string };
```

Не храните несовместимые booleans вроде `isLoading`, `hasError`, `isEmpty`,
которые могут одновременно стать `true`.

Для demo все promised interactions должны работать локально. Disabled button,
no-op CTA или fake network claim без явной подписи запрещены.

## 5. Собрать UI из правильных contracts

Правильный порядок:

1. `CatalogBackdrop` или semantic screen background;
2. safe-area aware screen container;
3. semantic header;
4. `GlassView` по depth role;
5. native controls (`GlassSlider`, `Switch`, `TextInput`, `Pressable`);
6. virtualized collection для больших данных;
7. dock/navigation только через owner integration.

Не переносите desktop widths, hover-only действия или mega-menu literally на
phone. Сохраните смысл через sheet, stack route, disclosure или contextual dock.

## 6. Accessibility сразу, не после визуальной части

Для каждого interactive element:

- role;
- label;
- hint только когда действие неочевидно;
- selected/disabled/checked/expanded state;
- minimum target;
- focus/dismiss behavior;
- Dynamic Type;
- Reduce Motion/Transparency.

Errors должны быть текстовыми и доступны screen reader. Цвет не может быть
единственным сигналом состояния.

## 7. Performance discipline

- Selector для Zustand должен быть узким.
- Большие списки — `FlatList` с stable key.
- Не создавать theme/store/provider в row.
- Не запускать perpetual animation.
- Не пересоздавать expensive SVG/data на каждый render; используйте module data
  или осмысленный `useMemo`.
- Не помещать blur на каждую строку длинного списка.
- Async command должен игнорировать stale completion после next/close/unmount.

## 8. Изменение native code

Native change требует большего scope проверки:

1. не добавлены лишние permissions;
2. autolinking корректен;
3. Pod install/Gradle sync проходят;
4. iOS target и bundle ID не изменились случайно;
5. Android application ID и manifest filters корректны;
6. Metro release bundle собирается;
7. native build выполнен хотя бы на затронутой платформе, в идеале на обеих.

Нельзя добавлять Expo ради одного API.

## 9. Обновить public contract

Если API должен использоваться снаружи модуля:

- экспортировать из `index.ts`;
- не раскрывать implementation details;
- обновить документацию;
- добавить пример;
- добавить test публичного behavior.

Breaking rename требует обновления всех imports и route/deep-link contracts.

## 10. Проверить результат

Минимум:

```sh
npm run typecheck
npm run lint
npm test -- --runInBand
git diff --check
```

После UI change также провести manual matrix из
[testing-and-qa.md](testing-and-qa.md).

## Запрещённые shortcuts

- Static screenshot вместо interactive native preview.
- `as any` для route params или component state.
- Deep import native glass package в feature.
- Hardcoded black dock в adaptive mode.
- Custom slider thumb overlay.
- Новая feature без visible entry point.
- Утверждение «полная parity» без variant audit.
- Один generic renderer для разных page families только со сменой title.
- Remote image/API как обязательное условие открытия catalog demo.
- Секреты, tokens или `.env` в commit.

## Definition of done

- [ ] Задача реализована, а не только спланирована.
- [ ] Архитектурный слой выбран правильно.
- [ ] Public API минимален и типизирован.
- [ ] Все promised states интерактивны и reachable.
- [ ] UI проверен в light/dark.
- [ ] Glass проверен с default/extreme settings и Reduce Transparency.
- [ ] Safe areas и dock inset корректны.
- [ ] iOS/Android platform behavior учтено.
- [ ] Accessibility contract выполнен.
- [ ] Typecheck, lint, tests и diff check зелёные.
- [ ] При native change выполнена native build verification.
- [ ] Документация обновлена, если contract изменился.
- [ ] Commit не содержит unrelated или generated мусор.
