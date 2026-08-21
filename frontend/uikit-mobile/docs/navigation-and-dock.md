# Навигация и dock

## Navigation model

Root navigation типизирована в `src/app/navigation/types.ts`.

```text
RootStack
├── Catalog
│   ├── OverviewTab -> OverviewStack
│   ├── FoundationsTab -> FoundationsStack
│   ├── ComponentsTab -> ComponentsStack
│   ├── PatternsTab -> PatternsStack
│   └── SettingsTab -> SettingsStack
├── CatalogPreview (modal)
├── ExpandedPlayer (full-screen modal)
└── 10 Showcase routes
```

Каждый tab имеет независимый native stack. `backBehavior="history"` сохраняет
ожидаемую историю между tabs, а `popToTopOnBlur=false` не сбрасывает вложенный
контекст пользователя.

## Пять primary destinations

Source: `src/app/navigation/navigation-contracts.ts`

| Route | Label | Содержимое |
|---|---|---|
| `OverviewTab` | Overview | Entry, showcase launcher, template library |
| `FoundationsTab` | Foundations | Tokens и visual foundations |
| `ComponentsTab` | Components | 29 MUI parity entries |
| `PatternsTab` | Extra | 20 advanced components |
| `SettingsTab` | Settings | Theme, glass, locale и dock settings |

Это стабильная information architecture. Не добавляйте шестой tab для нового
demo, profile или одной feature. Добавьте stack route в логически подходящий tab
либо root modal/showcase route.

## Как добавить route

1. Добавьте params в соответствующий `*ParamList`.
2. Создайте screen в `src/screens/<area>`.
3. Экспортируйте screen из локального `index.ts`.
4. Зарегистрируйте его в конкретном navigator.
5. Если route публично открывается извне, добавьте path в linking config.
6. Добавьте entry point из видимого UI.
7. Проверьте back gesture, Android back, safe area и cold deep link.

Пример typed navigation:

```tsx
type Props = NativeStackScreenProps<OverviewStackParamList, 'TemplatePreview'>;

export function TemplatePreviewScreen({ route }: Props) {
  return <DashboardTemplatePreview templateId={route.params.templateId} />;
}
```

Не используйте `useRoute()` + `as any`. Если shared screen обслуживает несколько
stacks, создайте узкий union/adapter и валидируйте params на boundary.

## Deep links

Поддерживаемый prefix: `spacewhyuikit://`.

Основные links:

```text
spacewhyuikit://components
spacewhyuikit://extra
spacewhyuikit://settings
spacewhyuikit://templates
spacewhyuikit://templates/:templateId
spacewhyuikit://preview/:exampleId
spacewhyuikit://player
spacewhyuikit://showcase/...
```

Не добавляйте `https://` prefix без полной iOS Associated Domains и Android App
Links configuration. Наличие path только в JavaScript не делает universal link
рабочим.

## Dock composition

```text
PlayerAwareTabDock
├── MiniPlayerDock (only when an active track exists)
└── TabDock
    └── DockSurface
        ├── GlassView variant="floating"
        └── DockSelectionBlob
            └── GlassView variant="control"
```

`DockSurface` резервирует собственную высоту и safe-area space. Его constants и
geometry находятся в `src/widgets/dock/dock-layout.ts`.

| Mode | Назначение |
|---|---|
| `navigation` | Основные пять tabs |
| `compact` | Компактная navigation surface |
| `contextual` | Selection/edit actions |
| `mini-player` | Один ряд media control |
| `expanded-player` | Расширенный dock player layout |

Для вручную позиционируемого content используйте `getDockContentInset()`,
`getPlayerAwareDockContentInset()` или `useDockContentInset()`. Не копируйте
числа высоты dock в screen styles.

## Draggable selection blob

`DockSelectionBlob` — одна общая glass-капля, которая:

- вычисляет slot geometry чистыми helpers;
- следует active tab;
- перетаскивается между destinations;
- выбирает ближайший index после отпускания;
- увеличивается во время gesture;
- уважает Reduce Motion;
- использует отдельные persisted blob settings.

Не создавайте отдельную pill внутри каждого `DockItem`. Это уничтожает эффект
одного морфирующего индикатора и приводит к несовпадающим размерам.

Навигационная капля занимает почти всю высоту 64 pt dock: top/bottom inset по
1 pt. Ширину регулирует `blobSize`, но minimum touch geometry сохраняется.

## Dock customization

`DockSettingsScreen` изменяет:

- adaptive/light/dark tone;
- material optical intensity;
- transparency;
- surface liquidity;
- background opacity;
- blob intensity/transparency/liquidity/size.

Preview и реальный dock должны читать один `settings.dock` contract. Не храните
отдельный несинхронизированный preview config.

## Contextual dock

Используйте только для действий, зависящих от текущего selection или mode.
Количество действий — `0...4`, enforced TypeScript tuple union.

Рекомендованный порядок:

1. наиболее вероятное действие;
2. вторичное действие;
3. share/move;
4. destructive действие последним.

При `actions=[]` лучше скрыть contextual dock на уровне owner, если пустая
surface не сообщает полезное состояние.

## Player dock

Player lifecycle монтируется один раз в `RootNavigator`. UI получает готовую
view model через `usePlayerDockModel`. Presentation components не должны
обращаться к native audio engine напрямую.

Close обязан остановить/очистить queue и закрыть expanded modal. Pause/next/
close commands защищены от stale async completion в controller.

## Navigation accessibility

- Tab item: `accessibilityRole="tab"`, selected state и понятный hint.
- Dock surface: `tablist` для navigation, `toolbar` для actions/player.
- Icon alone не заменяет label.
- Focus order должен совпадать с визуальным порядком.
- Tab labels нельзя обрезать до непонятного состояния на стандартном font size.
- Dynamic Type проверяется минимум до `maxFontSizeMultiplier`, заданного
  component contract.

## Runtime checklist

- [ ] Route открывается через видимый entry point.
- [ ] Back gesture и Android back возвращают в правильное место.
- [ ] Switching tabs не сбрасывает вложенный stack.
- [ ] Content не перекрывается dock и home indicator.
- [ ] Keyboard скрывает tab bar там, где нужно.
- [ ] Deep link работает при cold launch.
- [ ] Blob tap и drag выбирают одну и ту же destination.
- [ ] Light/dark/adaptive dock корректны.
- [ ] Mini-player не создаёт layout jump.
