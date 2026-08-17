# Testing и QA

## Быстрый gate для любого изменения

Из `frontend/uikit-mobile`:

```sh
npm run typecheck
npm run lint
npm test -- --runInBand
git diff --check
```

Node.js должен быть `22.11` или новее.

## Запуск приложения

Metro закреплён за портом `8082`:

```sh
npm start
```

Если cache действительно повреждён:

```sh
npm run start:reset-cache
```

Не используйте reset cache как постоянное «исправление» медленной навигации.
Сначала ищите повторный mount provider, тяжёлую synchronous работу, remote
request, oversized asset, unvirtualized list или render loop.

Запуск platform:

```sh
npm run ios
npm run android
```

## Что покрывать unit-тестами

| Область | Обязательные проверки |
|---|---|
| Settings | Clamp, defaults, invalid values, migration, legacy shape |
| Catalog data | Unique IDs, counts, sections, search, icon mapping |
| Template data | Unique IDs, web paths, groups, kinds, search |
| Navigation helpers | Geometry, nearest blob index, link paths |
| Player | Reducer/store, stale async commands, format/progress clamp |
| Validation | Required fields, formats, valid submit |
| Pure formatter/helper | Boundary values и invalid input |

Не тестируйте implementation detail, если пользовательское поведение можно
проверить через accessibility label, text, state или callback.

## Manual UI matrix

### Theme и material

- system light;
- system dark;
- forced light;
- forced dark;
- glass settings `0`, defaults и `100`;
- dock tone adaptive/light/dark;
- Reduce Transparency on/off;
- Reduce Motion on/off.

### Layout

- iPhone с Dynamic Island;
- небольшой iPhone/simulator;
- Android phone;
- portrait и доступная поддерживаемая orientation;
- keyboard open;
- long localized copy;
- larger text/Dynamic Type.

### Interaction

- tap;
- long press, если объявлен;
- slider press и drag;
- dock blob drag между всеми пятью destinations;
- scroll одновременно с nested controls;
- modal open/dismiss;
- back gesture и Android back;
- retry/reset;
- rapid repeated action для async command.

## Catalog QA

Для каждого нового/изменённого entry:

1. открыть из catalog list;
2. открыть прямым deep link;
3. проверить default state;
4. пройти все variants;
5. проверить disabled/loading/empty/error, если применимо;
6. выполнить primary interaction;
7. проверить recovery/reset;
8. сравнить с web source of truth;
9. проверить светлую и тёмную тему;
10. проверить screen reader labels и target sizes.

## Glass QA

- Backdrop действительно виден через прозрачность.
- В light theme glass остаётся различимым по border/depth, но не превращается в
  серую непрозрачную карточку.
- В dark theme surface не сливается с canvas.
- `surface`, `control`, `floating` визуально различаются.
- Shadow не обрезан.
- Ползунок idle компактный; при press/drag становится native liquid glass.
- Optical intensity, transparency и liquidity изменяют разные свойства.
- На Android fallback остаётся читаемым без обещания iOS-only optics.

## Performance QA

Проверяйте в development и, для спорной производительности, в release build.
Development Metro compile не равен runtime lag.

Ищите:

- долгий первый compile только один раз;
- одинаковую задержку при каждом переходе;
- repeated network requests;
- root provider remount;
- settings hydration loop;
- `ScrollView` с сотнями rows;
- large raster decode;
- nested blur layers;
- animation на JS thread во время gesture;
- broad Zustand subscription.

Для navigation regression измеряйте отдельно:

1. cold launch;
2. первый переход на ещё не compiled screen в dev;
3. повторный переход;
4. production/release transition.

Если повторный production transition быстрый, а первый dev transition ждёт
bundle compile, это tooling latency. Если каждый переход занимает секунды,
ищите runtime regression.

## Native verification

После native dependency/config change:

### Android

```sh
cd android
./gradlew :app:assembleDebug
cd ..
```

Дополнительно проверьте merged manifest: не должны появиться неожиданные camera,
microphone, location или storage permissions.

### iOS

```sh
cd ios
pod install
cd ..
npm run ios
```

Для release-critical change выполните signing-disabled simulator build через
Xcode/xcodebuild и проверьте built `Info.plist`.

## Handoff evidence

В handoff укажите:

- что изменено;
- какие contracts затронуты;
- точные команды и их результат;
- какие platform/screens проверены вручную;
- что не проверено и почему;
- путь к artifact, если собирался APK/app/bundle;
- оставшиеся реальные gaps без маскировки.

Фразы «должно работать» и «визуально нормально» не являются QA evidence.
