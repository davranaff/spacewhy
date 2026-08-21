# Web liquid glass, theme и settings

## Architecture

```text
SettingsProvider
  -> glassIntensity / glassTransparency / glassLiquidity
    -> ThemeProvider
      -> getGlassCssVars()
        -> :root --spacewhy-glass-*
          -> MUI overrides + liquidGlass() + layout surfaces
```

Live slider preview вызывает `applyGlassCssVars()` напрямую. Commit сохраняет
setting через Settings context. Поэтому drag не должен пересоздавать MUI theme
на каждый pointer event.

## Три depth roles

Web использует те же semantic roles, что и mobile:

| Role | `blurStrength` | Примеры |
|---|---|---|
| Floating | `full` | Header, nav, popover, settings drawer |
| Surface | `surface` | Card, Paper, content panel |
| Control | `control` | Outlined/soft button, chip, field, toggle |

```tsx
<Box
  sx={theme => ({
    ...liquidGlass({
      theme,
      blurred: true,
      blurStrength: 'surface',
    }),
  })}
>
  {children}
</Box>
```

Не вызывайте `liquidGlass()` поверх `Card` только потому, что нужна карточка:
global Card override уже применяет surface material.

## `liquidGlass()` options

| Option | Default | Значение |
|---|---:|---|
| `elevated` | `true` | Material shadow |
| `interactive` | `false` | Hover/active/focus-visible states |
| `blurred` | `false` | Реальный backdrop filter |
| `blurStrength` | `full` | Floating/surface/control token family |
| `positioned` | `true` | Добавляет `position: relative` |

`blurred: false` полезен для глобального Paper, где непрерывный blur каждого
nested surface слишком дорог. Включайте blur на bounded layer с реальным
backdrop, а не автоматически везде.

## Axes и CSS variables

### Optical intensity

Меняет только optical stack:

- floating/surface/control blur;
- saturation;
- depth perception.

### Transparency

Меняет alpha surface и background reveal. Текст, border и children не получают
общую opacity.

### Surface liquidity

Меняет:

- floating/surface/control radius;
- shadow blur/offset/spread;
- edge alpha;
- material motion duration.

Не связывайте три slider в один «strength» и не меняйте geometry через
transparency.

## Использование CSS variables

Для custom component используйте существующие variables:

```tsx
sx={{
  borderRadius: 'var(--spacewhy-glass-control-radius)',
  backdropFilter:
    'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
}}
```

Не копируйте вычисленные `18px`, alpha и shadow в feature. Если системе нужен
новый token, добавьте его централизованно в `getGlassCssVars()` и тесты.

## Theme settings

`SettingsValueProps` содержит:

- `themeMode`: light/dark;
- `themeDirection`: LTR/RTL;
- `themeContrast`: default/bold;
- `themeLayout`: vertical/horizontal/mini;
- `themeColorPresets`;
- `themeStretch`;
- три glass values.

Новый persisted field требует default, normalization, reset behavior и tests.
Не читайте localStorage напрямую из feature.

## MUI overrides

Global behavior находится в `src/theme/overrides/components`.

| Override | Material role |
|---|---|
| `Card` | Blurred surface |
| `Paper` | Bounded surface, no automatic nested blur |
| `AppBar` | Floating glass |
| Outlined/soft `Button` | Control glass |
| `Chip`, `ToggleButton`, `TextField` | Control glass |

Если один component выглядит неверно на всём продукте, исправляйте override.
Локальный `sx` использовать для layout/one-off semantic state, не для массового
копирования темы.

## Light theme

В light theme стекло различается за счёт:

- light alpha family;
- тёмного edge alpha;
- restrained shadow;
- видимого backdrop;
- semantic dark text.

Не делайте все glass surfaces чисто белыми opaque cards. Также не снижайте alpha
настолько, чтобы исчезали form boundaries и table rows.

## Performance

- Максимум один full blur на floating region.
- Surface blur только у bounded cards, которые реально показывают backdrop.
- Controls используют меньший blur.
- Не добавлять animated gleam/highlight на каждый element.
- Не анимировать `backdrop-filter` в continuous loop.
- Не применять blur к full-page scrolling ancestor.
- Проверять Chrome Performance paint cost и route transition.
- `prefers-reduced-motion` отключает decorative motion.

## Glass review checklist

- [ ] Использованы helper/variables, не raw duplicated formula.
- [ ] Правильный depth role.
- [ ] Light/dark/contrast проверены.
- [ ] LTR/RTL layout не сломан.
- [ ] Нет nested full blur.
- [ ] Focus-visible остаётся видимым.
- [ ] Settings sliders меняют независимые свойства.
- [ ] Route transition не получает постоянный heavy repaint.
