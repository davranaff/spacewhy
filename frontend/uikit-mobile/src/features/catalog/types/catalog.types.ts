export type CatalogGroup = 'foundations' | 'mui' | 'extra';

export type FoundationExampleId =
  | 'colors'
  | 'typography'
  | 'shadows'
  | 'grid'
  | 'icons';

export type MuiExampleId =
  | 'accordion'
  | 'alert'
  | 'autocomplete'
  | 'avatar'
  | 'badge'
  | 'breadcrumbs'
  | 'buttons'
  | 'checkbox'
  | 'chip'
  | 'dialog'
  | 'list'
  | 'menu'
  | 'pagination'
  | 'pickers'
  | 'popover'
  | 'progress'
  | 'radio-button'
  | 'rating'
  | 'slider'
  | 'stepper'
  | 'switch'
  | 'table'
  | 'tabs'
  | 'textfield'
  | 'timeline'
  | 'tooltip'
  | 'transfer-list'
  | 'tree-view'
  | 'data-grid';

export type ExtraExampleId =
  | 'chart'
  | 'map'
  | 'editor'
  | 'copy-to-clipboard'
  | 'upload'
  | 'carousel'
  | 'multi-language'
  | 'animate'
  | 'mega-menu'
  | 'form-validation'
  | 'lightbox'
  | 'image'
  | 'label'
  | 'scroll'
  | 'scroll-progress'
  | 'snackbar'
  | 'text-max-line'
  | 'navigation-bar'
  | 'organization-chart'
  | 'markdown';

export type CatalogExampleId =
  | FoundationExampleId
  | MuiExampleId
  | ExtraExampleId;

export type CatalogExample = Readonly<{
  id: CatalogExampleId;
  group: CatalogGroup;
  title: string;
  description: string;
  keywords: readonly string[];
}>;

export type CatalogSection = Readonly<{
  id: CatalogGroup;
  title: string;
  description: string;
  examples: readonly CatalogExample[];
}>;

export type CatalogPreviewProps = Readonly<{
  compact?: boolean;
}>;
