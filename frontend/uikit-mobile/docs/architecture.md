# Архитектура

## Runtime entry chain

```text
index.js
  -> App.tsx
    -> src/app/app-root.tsx
      -> src/app/providers/app-providers.tsx
        -> src/app/navigation/root-navigator.tsx
```

`index.js` обязан первым подключать `react-native-gesture-handler`.
`react-native-worklets/plugin` обязан оставаться последним Babel plugin.

Root providers монтируются один раз и в таком порядке:

1. `GestureHandlerRootView`;
2. `SafeAreaProvider`;
3. `I18nextProvider`;
4. `AppThemeProvider`;
5. status bar и locale synchronization;
6. `RootNavigator`.

Не создавайте второй theme, navigation, safe-area или settings provider внутри
feature. Это приводит к разным состояниям темы, двойной hydration и неверным
insets.

## Слои и направление зависимостей

```text
app -> screens -> widgets -> features -> shared
 |       |          |          |          |
 composition   large UI    domain UI   primitives
 navigation    regions     and data    and platform boundaries
```

Разрешены зависимости вниз и на том же уровне без циклов. Обратные зависимости
запрещены.

| Слой | Ответственность | Может импортировать | Не должен импортировать |
|---|---|---|---|
| `src/app` | Providers, root composition, navigation registry | `screens`, `widgets`, `features`, `shared` | Feature internals по глубокому path без причины |
| `src/screens` | Route-level layout, safe area, orchestration | `widgets`, public `features`, `shared` | Другие screens как reusable UI, native SDK напрямую |
| `src/widgets` | Крупные самостоятельные области: dock, mini-player | public `features`, `shared` | `screens`, `app` |
| `src/features` | Catalog, player, showcase, template domain | `shared`; другой feature только через public barrel при явной связи | `screens`, `app` |
| `src/shared` | Theme, settings, i18n, accessibility, low-level UI | Другой `shared` module | `features`, `widgets`, `screens`, `app` |

## Структура пакета

```text
frontend/uikit-mobile/
├── android/                       # Android native project
├── ios/                           # iOS native project and pods
├── docs/                          # This agent contract
├── src/
│   ├── app/
│   │   ├── navigation/            # Typed stacks, tabs, links, dock integration
│   │   └── providers/             # One-time global providers
│   ├── assets/component-icons/    # Local catalog artwork by stable ID
│   ├── features/
│   │   ├── catalog/               # 54 component descriptors and previews
│   │   ├── player/                # Audio engine, controller, store and content
│   │   ├── showcase/              # End-to-end demo data and behavior
│   │   └── templates/             # 41 dashboard descriptors and 14 contracts
│   ├── screens/
│   │   ├── catalog/               # Five tabs, preview and dock settings screens
│   │   ├── player/                # Expanded player route
│   │   ├── showcase/              # Integrated demo routes
│   │   └── templates/             # Library and template preview routes
│   ├── shared/
│   │   ├── accessibility/         # Platform accessibility state
│   │   ├── i18n/                  # i18next instance
│   │   ├── settings/              # Versioned persisted Zustand settings
│   │   ├── theme/                 # Semantic tokens and theme context
│   │   └── ui/                    # GlassView and GlassSlider boundaries
│   └── widgets/
│       ├── contextual-dock/
│       ├── dock/
│       └── mini-player/
├── App.tsx
├── index.js
├── babel.config.js
├── metro.config.js
├── tsconfig.json
└── package.json
```

## Public API и imports

Используйте alias `@/` и public barrel ближайшего самостоятельного модуля:

```tsx
import { useAppTheme } from '@/shared/theme';
import { GlassSlider, GlassView } from '@/shared/ui';
import { CatalogExamplePreview } from '@/features/catalog';
import { ContextualDock } from '@/widgets/contextual-dock';
```

Глубокий import допустим внутри самого feature, но consumer снаружи должен
использовать `index.ts`. Если новый API нужен снаружи, явно экспортируйте его в
barrel. Не экспортируйте private implementation только ради удобства теста.

## Где создавать новый код

| Если код… | Разместить |
|---|---|
| Ничего не знает о бизнес-сценарии и нужен в нескольких features | `shared` |
| Представляет законченную крупную область интерфейса | `widgets/<name>` |
| Владеет данными/поведением одной функции | `features/<name>` |
| Является route и собирает несколько частей | `screens/<area>` |
| Регистрирует provider, route или root integration | `app` |
| Нужен только одному component | Рядом с component, не поднимать преждевременно |

## State ownership

| State | Владелец |
|---|---|
| Theme mode, locale, global glass, dock customization | `useAppSettingsStore` |
| Navigation history and route params | React Navigation |
| Player queue, status, progress and errors | Player store/controller |
| Search text, selected tab, open dialog in one screen | Local React state |
| Derived layout geometry | Pure helper + local measured state |

Не записывайте transient UI state в global store. Не дублируйте route params в
Zustand. Persisted settings должны проходить через `normalizeAppSettings()` и
версионироваться через `APP_SETTINGS_VERSION`.

## Native boundaries

Native dependencies изолированы намеренно:

| Dependency | Единственная ответственность |
|---|---|
| `@callstack/liquid-glass` | Внутренняя реализация `GlassView` |
| `@react-native-community/blur` | Fallback внутри `GlassView` |
| `@react-native-community/slider` | Внутренняя реализация `GlassSlider` |
| `react-native-audio-api` | Player engine adapter |
| `react-native-gesture-handler` | Root gestures и draggable dock blob |

Перед добавлением native package проверьте, нельзя ли закрыть задачу текущей
boundary. Если dependency всё же нужна, требуется iOS/Android configuration,
autolink verification, permissions audit и сборка обеих платформ.
