# Компоненты: что и когда использовать

## Public reusable components

Mobile UI kit сейчас предоставляет небольшой набор настоящих reusable
contracts и большой интерактивный catalog. Не путайте эти две вещи:

- `shared/ui` и `widgets` можно использовать в product screens;
- `features/catalog/components/*` служит для демонстрации UI kit;
- catalog preview не становится production component автоматически.

## `GlassView`

Source: `src/shared/ui/glass-view.tsx`.

Import: `import { GlassView } from '@/shared/ui';`

`GlassView` — единственная разрешённая boundary для жидкого стекла.

```tsx
<GlassView variant="surface" style={styles.card}>
  <Text>Account summary</Text>
</GlassView>
```

### Props

| Prop | Значение | Когда использовать |
|---|---|---|
| `variant` | `surface`, `control`, `floating` | Выбирает depth/material role |
| `tone` | `theme`, `light`, `dark` | Обычно `theme`; fixed tone только для контрастного media backdrop |
| `interactive` | `boolean` | Для pressable/drag-aware glass; значение фиксируется на mount |
| `effect` | `clear`, `regular` | Редкий явный native override; обычно выводится из intensity |
| `tintColor` | `ColorValue` | Семантический overlay для специального состояния |
| `reducedTransparency` | `boolean` | QA или явный accessibility override |
| `materialSettings` | `Partial<GlassSettings>` | Локальная настройка конкретной surface поверх global settings |
| `style` | `ViewStyle` | Layout, radius и surface styling |

`GlassView` разделяет shadow host и masked material surface. Не добавляйте
`overflow: 'hidden'` на внешний wrapper и не переносите shadow внутрь: на iOS
это обрежет внешнюю тень.

### Выбор variant

| Variant | Использовать для | Не использовать для |
|---|---|---|
| `surface` | Cards, panels, grouped information, form sections | Floating navigation и modal overlay |
| `control` | Segmented selection, glass buttons, draggable blob | Большие content containers |
| `floating` | Dock, popover, floating toolbar, transient overlay | Каждая карточка списка |

## `GlassSlider`

Source: `src/shared/ui/glass-slider.tsx`.

Import: `import { GlassSlider } from '@/shared/ui';`

Используйте для любого single-value range: glass settings, dock settings,
player seek, rating precision и feature preferences.

```tsx
<GlassSlider
  accessibilityLabel="Surface transparency"
  accessibilityText={`${transparency} percent transparent`}
  value={transparency}
  onValueChange={value => setGlassSettings({ transparency: value })}
/>
```

Обязательные правила:

- передавайте понятный `accessibilityLabel`;
- для шкалы не в процентах задавайте `minimumValue`, `maximumValue`, `step` и
  корректный `accessibilityText`;
- не создавайте overlay thumb, отдельный `GestureDetector` или абсолютную
  glass-каплю;
- не задавайте фиксированные thumb width/height;
- не заменяйте native slider на JS-рисование ради внешнего сходства.

На iOS 26 нативный `UISlider` сам показывает компактный светлый idle thumb и
увеличенный liquid-glass thumb во время press/drag. Это утверждённый контракт из
reference commit `88886b0`.

## Theme и settings hooks

### `useAppTheme()`

Используйте для любого визуального решения:

```tsx
const theme = useAppTheme();

const styles = StyleSheet.create({
  title: {
    ...theme.typography.title,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
});
```

Предпочтительные semantic roles:

| Role | Назначение |
|---|---|
| `canvas`, `canvasElevated` | Screen background и elevated background |
| `surface`, `surfaceElevated` | Content containers |
| `text`, `textMuted` | Primary и secondary text |
| `border` | Hairlines, outlines, inactive tracks |
| `accent`, `accentContrast` | Primary action и текст на нём |
| `positive`, `warning`, `negative` | Только соответствующий semantic status |

### `useAppSettingsStore()`

Подписывайтесь на минимальный slice:

```tsx
const glass = useAppSettingsStore(state => state.settings.glass);
const setGlassSettings = useAppSettingsStore(state => state.setGlassSettings);
```

Не используйте `const store = useAppSettingsStore()` без selector: это создаёт
лишние re-render при любом изменении settings.

## Catalog-only primitives

Source: `src/features/catalog/components/catalog-primitives.tsx`

| Component | Назначение | Ограничение |
|---|---|---|
| `CatalogBackdrop` | Единый визуальный фон catalog screen | Не product shell |
| `CatalogScreenHeader` | Header catalog example | Не заменяет navigation header |
| `CatalogSearch` | Поиск по component inventory | Текст и a11y привязаны к catalog |
| `CatalogExampleCard` | Reachable card для descriptor | Принимает `CatalogExample` |
| `CatalogSectionHeading` | Заголовок catalog section | Только presentation |
| `DemoSurface` | Стеклянная/матовая demo-плашка | Не считать production Card API |
| `DemoButton` | Быстрая демонстрация hierarchy | Не считать production Button API |

Для production feature создайте узкий component рядом с feature и выразите его
состояния типами. Не импортируйте `DemoButton` в auth, commerce или account flow.

## Dock widgets

### `TabDock`

Используется только как custom `tabBar` React Navigation. Он зависит от
`BottomTabBarProps`, пяти `DOCK_DESTINATIONS` и draggable selection blob.
Нельзя вручную вставлять его в обычный screen.

### `ContextualDock`

Используйте, когда текущий selection/edit mode требует от нуля до четырёх
действий.

```tsx
const actions = [
  {
    id: 'archive',
    label: 'Archive',
    icon: 'archive',
    onPress: archiveSelection,
  },
] as const satisfies ContextualDockActions;

<ContextualDock actions={actions} />;
```

Не передавайте больше четырёх действий. Редкие действия перемещайте в menu или
detail screen. Для destructive action задавайте `destructive: true`.

### `MiniPlayerDock`

Presentation component для активного media item. В root app он уже подключён
через `PlayerAwareTabDock` и `usePlayerDockModel()`. Не создавайте второй player
store или второй lifecycle mount.

### `DockIndicatorExamples`

Catalog-only демонстрация `dot`, `pill`, `segmented`, `progress`. Для product
carousel или onboarding можно повторно использовать только после проверки, что
его публичный API соответствует реальному feature contract.

## Иконки

- Общие action icons: `lucide-react-native` с semantic theme color.
- Dock icons: typed registry в `src/widgets/dock/dock-icon.tsx`.
- Catalog artwork: только `src/assets/component-icons/*` через
  `CATALOG_ICON_REGISTRY`.
- Не используйте emoji как product icon.
- Не смешивайте Lucide, SF Symbols и случайные SVG в одной control family.
- Interactive icon обязан иметь label на родительском `Pressable`.

## Выбор native primitive

| UX-задача | Базовый primitive |
|---|---|
| Tap action | `Pressable` |
| Long scrollable form/article | `ScrollView` |
| Dynamic/large collection | `FlatList` или другая virtualized list |
| Modal semantics и focus containment | `Modal` / native stack modal |
| Boolean setting | `Switch` |
| Text value | `TextInput` |
| Date/time | `@react-native-community/datetimepicker` boundary |
| Numeric continuous range | `GlassSlider` |
| Decorative chart | `react-native-svg`, hidden from accessibility when appropriate |

Любая интерактивная цель должна быть минимум 44 pt на iOS и 48 dp на Android,
либо иметь достаточный `hitSlop` без перекрытия соседней цели.

## Catalog inventory и назначение

### Foundations

| ID | Использовать как reference для |
|---|---|
| `colors` | Semantic palette и status roles |
| `typography` | Type ramp, scaling и line-height |
| `shadows` | Glass depth и elevation |
| `grid` | Spacing, radius, gutters, touch targets |
| `icons` | Размер, stroke и icon family |

### MUI parity entries

| Группа | IDs | Когда использовать |
|---|---|---|
| Disclosure | `accordion`, `tree-view` | Progressive reveal и hierarchy |
| Feedback | `alert`, `dialog`, `progress`, `snackbar`, `tooltip` | Status, confirmation, loading и contextual help |
| Input | `autocomplete`, `checkbox`, `pickers`, `radio-button`, `rating`, `slider`, `switch`, `textfield` | Form controls по нативному interaction contract |
| Identity/status | `avatar`, `badge`, `chip` | Person/entity identity и compact state |
| Actions/navigation | `breadcrumbs`, `buttons`, `menu`, `pagination`, `popover`, `stepper`, `tabs` | Action hierarchy и local navigation |
| Data | `data-grid`, `list`, `table`, `timeline`, `transfer-list` | Virtualized data, history и selection workflows |

### Extra entries

| Группа | IDs | Когда использовать |
|---|---|---|
| Media/data | `chart`, `map`, `carousel`, `image`, `lightbox` | Visual data и media exploration |
| Authoring/files | `editor`, `markdown`, `upload`, `copy-to-clipboard` | Content creation и file actions |
| Navigation/layout | `mega-menu`, `navigation-bar`, `organization-chart`, `scroll`, `scroll-progress` | Complex hierarchy и position-aware UI |
| Presentation | `animate`, `label`, `text-max-line` | Motion, semantic labels и truncation |
| App behavior | `form-validation`, `multi-language`, `snackbar` | Validation, locale и transient feedback |

Catalog entry показывает контракт и parity. Перед использованием в product flow
откройте preview и проверьте, что конкретный state действительно реализован, а
не только упомянут в description.
