# Liquid glass, тема и настройки

## Цель материала

Spacewhy glass — это система depth roles, а не blur на каждом элементе. Стекло
должно оставаться читаемым, реагировать на светлую/тёмную тему, уважать Reduce
Transparency и не создавать несколько тяжёлых blur layers в одной области.

## Platform behavior

| Platform/state | Реализация |
|---|---|
| iOS 26 с поддержкой Liquid Glass | `LiquidGlassView` |
| iOS ниже 26 | `BlurView` fallback |
| Android | Theme-aware matte translucent surface |
| Reduce Transparency | Opaque semantic surface |

Feature code не должен определять версию iOS или повторять эту таблицу в
условиях. Это полностью ответственность `GlassView`.

## Три оси материала

| Setting | Что меняет | Что не должно менять |
|---|---|---|
| `opticalIntensity` | Blur depth, tint depth; на native iOS выбирает `clear`/`regular` threshold | Transparency и geometry |
| `transparency` | Насколько виден backdrop через material | Radius и shadow spread |
| `surfaceLiquidity` | Radius, edge softness и shadow spread | Background reveal |

Значения всегда нормализуются в диапазон `0...100`. Не храните рядом
альтернативные `0...1` копии этих settings.

На iOS 26 native optics имеют дискретные `clear` и `regular`. Непрерывная часть
optical intensity переносится через tint strength; это ограничение platform API,
а не повод рисовать fake blur поверх native glass.

## Material roles

```tsx
<GlassView variant="surface">...</GlassView>
<GlassView variant="control" interactive>...</GlassView>
<GlassView variant="floating">...</GlassView>
```

Обычно на одном screen достаточно:

- backdrop без blur;
- нескольких `surface` containers;
- одного `floating` layer;
- `control` только на выбранных/interactive элементах.

Не вкладывайте `floating` glass в другой `floating` glass без визуальной
необходимости. Для обычного списка одна glass section вокруг rows дешевле и
чище, чем отдельный blur на каждой строке.

## Tone

`tone="theme"` — default и правильный выбор почти всегда.

Fixed `light` или `dark` допустим, когда surface лежит над media и должна иметь
предсказуемую contrast scheme независимо от app theme. В этом случае вручную
проверьте текст, icons и border в обеих app themes.

Dock использует persisted `tone: adaptive | light | dark`; его нельзя
привязывать к одному чёрному фону.

## Global и local settings

Global settings применяются автоматически:

```tsx
const glass = useAppSettingsStore(state => state.settings.glass);
```

Для локального special surface передавайте только отличающиеся поля:

```tsx
<GlassView
  materialSettings={{ transparency: 72 }}
  variant="floating"
>
  {children}
</GlassView>
```

Не копируйте весь global object в local component state. Для live-preview
settings screen разрешён controlled draft, но Apply должен записывать его через
store action, а Reset — использовать нормализованные defaults.

## Settings model

Source: `src/shared/settings/settings-model.ts`

```ts
type AppSettings = {
  schemaVersion: 2;
  themeMode: 'system' | 'light' | 'dark';
  locale: 'en' | 'ru' | 'uz';
  glass: GlassSettings;
  dock: DockSettings;
};
```

`DockSettings` отдельно управляет:

- dock tone;
- dock material intensity/transparency/liquidity;
- background opacity;
- active blob intensity/transparency/liquidity;
- blob width через `blobSize`.

При добавлении persisted setting агент обязан:

1. изменить interface;
2. увеличить `APP_SETTINGS_VERSION`;
3. добавить default;
4. обновить `normalizeAppSettings()` и migration behavior;
5. добавить/update store action;
6. покрыть invalid, missing и legacy value тестами;
7. проверить cold hydration.

## Theme tokens

Source: `src/shared/theme/tokens.ts`

Используйте только semantic roles. `accent` намеренно монохромный: в dark theme
он светлый, в light theme — почти чёрный. Status colors остаются цветными только
для реального positive/warning/negative смысла.

Не использовать:

- orange/red как decoration без semantic причины;
- `#fff`/`#000` для текста вместо `text`/`accentContrast`;
- произвольные margins вроде `13`, если подходит spacing scale;
- radius, не связанный с `theme.radius` или material geometry;
- отдельную theme object внутри feature.

## Slider contract

`GlassSlider` выглядит по-разному в idle и active состояниях, потому что это
нативное поведение `UISlider`:

```text
idle:    compact light thumb
pressed: larger liquid-glass thumb owned by iOS
```

Любая попытка постоянно рисовать большую glass capsule поверх slider ломает
этот transition, hit testing и accessibility. Поэтому wrapper настраивает только
track colors, value, range, callbacks и accessibility metadata.

## Performance budget

- Не анимируйте blur amount каждый frame.
- Не обновляйте global settings на scroll.
- Для drag используйте native gesture/animation path и минимальный JS state.
- Не создавайте perpetual shimmer/highlight.
- Используйте `pointerEvents="none"` для декоративных overlays.
- Virtualize длинные collections; glass не отменяет `FlatList`.
- Проверяйте screen на реальном device/simulator, а не только screenshot.

## Accessibility

- Reduce Transparency всегда должен давать читаемую opaque surface.
- Reduce Motion отключает декоративные dock transitions.
- Contrast проверяется в light/dark и fixed tone combinations.
- Glass не является смыслом: accessibility label описывает действие или
  содержимое, а не «стеклянную кнопку».
- Не помещайте decorative material layer в accessibility tree.

## Review checklist для glass change

- [ ] Использован `GlassView`, native package не импортирован напрямую.
- [ ] Выбран правильный `variant`.
- [ ] Surface читаема в light и dark themes.
- [ ] Проверен Reduce Transparency.
- [ ] Нет clipped shadow.
- [ ] Нет nested blur без причины.
- [ ] Slider остаётся нативным.
- [ ] Settings axes визуально независимы.
- [ ] Drag/scroll остаются плавными.
