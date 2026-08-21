# Routes, layouts, auth и data

## App Router ownership

`src/app` содержит route entry files. Центральные URL constants находятся в
`src/routes/paths.ts` и должны использоваться для links/navigation.

```tsx
import { paths } from 'src/routes/paths';

<Link component={RouterLink} href={paths.dashboard.product.root}>
  Products
</Link>
```

Не дублируйте `/dashboard/...` string в десятках components. Dynamic URL
создавайте через существующий path function.

## Route families

| Family | Layout/behavior |
|---|---|
| `/` и public marketing | Main/simple/compact layout без Redux/auth wait |
| `/components/**` | `MainLayout`, interactive catalog |
| `/auth/**` | Provider-specific auth routes |
| `/auth-demo/**` | Visual auth variants без backend promise |
| `/dashboard/**` | ReduxProvider + AuthGuard + DashboardLayout |
| `/product/**`, `/post/**`, `/payment` | Public/storefront flows по route layout |
| Error/utility routes | Focused simple/compact layouts |

Route inventory — продуктовый контракт. После массового move/rename сравните
количество и paths до/после.

## Page/section pattern

Рекомендуемый `page.tsx`:

```tsx
import ProductListView from 'src/sections/product/view/product-list-view';

export const metadata = { title: 'Products' };

export default function Page() {
  return <ProductListView />;
}
```

Page не должен содержать 500 строк form/table logic. Section view владеет page
composition, domain subcomponents лежат рядом.

## Layout selection

| Layout | Когда использовать |
|---|---|
| `MainLayout` | Public site и component catalog с public header/footer |
| `DashboardLayout` | Authenticated dashboard/tool surface |
| `AuthLayout` | Реальная auth family |
| `SimpleLayout` | Error/maintenance/single-purpose page |
| `CompactLayout` | Centered constrained page |

Dashboard layout уже поддерживает vertical/horizontal/mini и responsive mobile
drawer. Не создавайте ещё один sidebar shell в feature.

## Dashboard navigation

Navigation config и UI должны оставаться раздельными. Item route берётся из
`paths`. Active state сравнивает нормализованные pathname, без искусственного
trailing slash.

При изменении nav проверьте:

- desktop vertical;
- desktop mini;
- desktop horizontal;
- mobile drawer;
- keyboard disclosure;
- Escape/focus return;
- RTL viewport placement;
- body scroll restore после route.

## Auth

Root использует JWT provider. Dashboard защищён `AuthGuard`.

Standalone demo должен оставаться работоспособным без remote backend:

- demo login принимает documented credentials;
- local registration создаёт local demo session;
- remote mode включается явно;
- forgot-password link не может быть no-op;
- protected route не висит бесконечно на loading при failed endpoint.

Другие provider families (Auth0/Amplify/Firebase) существуют как варианты, но
одновременно root монтирует только один `AuthProvider`.

## Redux

Redux provider размещён в dashboard segment, а не root. Добавляйте slice только
для состояния, которое действительно разделяется несколькими dashboard views
или требует domain actions/selectors.

Не использовать Redux для:

- open/close одного dialog;
- field state формы;
- local table page;
- theme/settings;
- auth context copy;
- server route params.

Selector должен быть узким. Async thunk должен иметь loading/error lifecycle.

## Mock и demo API

`src/_mock` предоставляет deterministic local data и local-first adapter.

Правила:

- component/demo route не зависит от внешнего network;
- unknown endpoint возвращает явную ошибку;
- list/details/search/dashboard responses соответствуют реальному shape;
- fake mutation не заявляется как remote persistence;
- local asset существует до ссылки на него;
- credentials/secret не хранятся в mock.

## Assets

Runtime assets находятся в `public/assets`. Code reference должен быть
root-relative: `/assets/...`.

- Marketing hero использует Spacewhy content.
- Logos/favicon используют Spacewhy identity.
- UI evidence лучше рендерить code-native, чем fake screenshot с нечитаемым
  generated text.
- Remote Cloudinary/Minimals URL не является допустимым production dependency.
- После удаления asset сначала подтвердите zero references, включая dynamic
  families.

## Loading и route transitions

Не создавайте искусственный full-page loading на каждый client transition.

При задержке различайте:

1. dev compile нового route;
2. server response;
3. auth/persistence wait;
4. client hydration/render;
5. asset/network wait;
6. paint cost glass/animation.

Global `ProgressBar` остаётся маленьким visual indicator и изолирован в Suspense.
Он не должен блокировать content.

## Добавление route

1. Выберите route family/layout.
2. Добавьте path constant/function.
3. Создайте тонкий `page.tsx`.
4. Реализуйте section view.
5. Добавьте nav/CTA entry при необходимости.
6. Проверьте metadata и document title.
7. Добавьте auth/Redux provider только если family требует.
8. Проверьте direct URL, internal transition, refresh и not-found path.
9. Проверьте mobile/desktop и три dashboard layouts.
10. Убедитесь, что route count изменился ожидаемо.
