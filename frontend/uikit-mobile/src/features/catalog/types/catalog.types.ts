export type CatalogGroup =
  | 'foundations'
  | 'controls'
  | 'forms'
  | 'feedback'
  | 'data-display'
  | 'surfaces'
  | 'patterns';

export type CatalogExampleId =
  | 'colors'
  | 'typography'
  | 'spacing'
  | 'icons'
  | 'glass-material'
  | 'buttons'
  | 'selection-controls'
  | 'chips-badges'
  | 'text-fields'
  | 'slider-progress'
  | 'alerts'
  | 'loading-states'
  | 'avatars-lists'
  | 'metrics'
  | 'cards'
  | 'dialogs'
  | 'dock-indicators'
  | 'contextual-dock'
  | 'tabs-segments'
  | 'empty-error'
  | 'virtualized-list'
  | 'form-flow';

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
