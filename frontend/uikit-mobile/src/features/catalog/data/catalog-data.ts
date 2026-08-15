import type {
  CatalogExample,
  CatalogExampleId,
  CatalogGroup,
  CatalogSection,
} from '@/features/catalog/types/catalog.types';

const examples = [
  {
    id: 'colors',
    group: 'foundations',
    title: 'Color system',
    description: 'Semantic color roles for light and dark interfaces.',
    keywords: ['palette', 'semantic', 'contrast', 'theme'],
  },
  {
    id: 'typography',
    group: 'foundations',
    title: 'Typography',
    description: 'Native type ramp with predictable rhythm and scaling.',
    keywords: ['text', 'font', 'dynamic type', 'hierarchy'],
  },
  {
    id: 'spacing',
    group: 'foundations',
    title: 'Spacing & shape',
    description: 'Spacing, radius and touch-target primitives.',
    keywords: ['grid', 'radius', 'layout', 'touch'],
  },
  {
    id: 'icons',
    group: 'foundations',
    title: 'Iconography',
    description: 'Consistent Lucide icons aligned to native controls.',
    keywords: ['icons', 'symbols', 'glyph'],
  },
  {
    id: 'glass-material',
    group: 'foundations',
    title: 'Liquid glass',
    description: 'Native material with intentional, bounded fallbacks.',
    keywords: ['glass', 'blur', 'material', 'surface'],
  },
  {
    id: 'buttons',
    group: 'controls',
    title: 'Buttons',
    description: 'Primary, secondary, quiet and icon actions.',
    keywords: ['button', 'action', 'pressable', 'cta'],
  },
  {
    id: 'selection-controls',
    group: 'controls',
    title: 'Selection controls',
    description: 'Switch, checkbox and radio behavior.',
    keywords: ['switch', 'checkbox', 'radio', 'toggle'],
  },
  {
    id: 'chips-badges',
    group: 'controls',
    title: 'Chips & badges',
    description: 'Compact status, filter and count controls.',
    keywords: ['chip', 'badge', 'filter', 'status'],
  },
  {
    id: 'dock-indicators',
    group: 'controls',
    title: 'Dock indicators',
    description: 'Dot, glass pill, segmented and progress page markers.',
    keywords: ['dock', 'indicator', 'pagination', 'progress', 'glass pill'],
  },
  {
    id: 'text-fields',
    group: 'forms',
    title: 'Text fields',
    description: 'Labels, hints, validation and secure entry.',
    keywords: ['input', 'field', 'validation', 'form'],
  },
  {
    id: 'slider-progress',
    group: 'forms',
    title: 'Slider & progress',
    description: 'Continuous input with clear current-value feedback.',
    keywords: ['slider', 'range', 'progress', 'value'],
  },
  {
    id: 'form-flow',
    group: 'forms',
    title: 'Form flow',
    description: 'A complete validation and submission example.',
    keywords: ['form', 'submit', 'validation', 'keyboard'],
  },
  {
    id: 'alerts',
    group: 'feedback',
    title: 'Alerts & notices',
    description: 'Success, information, warning and error feedback.',
    keywords: ['alert', 'notice', 'success', 'error'],
  },
  {
    id: 'loading-states',
    group: 'feedback',
    title: 'Loading states',
    description: 'Progress, skeleton and non-blocking loading patterns.',
    keywords: ['loading', 'skeleton', 'spinner', 'progress'],
  },
  {
    id: 'empty-error',
    group: 'feedback',
    title: 'Empty & error states',
    description: 'Actionable recovery states with human copy.',
    keywords: ['empty', 'error', 'retry', 'offline'],
  },
  {
    id: 'avatars-lists',
    group: 'data-display',
    title: 'Avatars & lists',
    description: 'Dense and comfortable rows with metadata.',
    keywords: ['avatar', 'list', 'row', 'metadata'],
  },
  {
    id: 'metrics',
    group: 'data-display',
    title: 'Metrics',
    description: 'Compact dashboard values and trend semantics.',
    keywords: ['metric', 'stats', 'dashboard', 'trend'],
  },
  {
    id: 'virtualized-list',
    group: 'data-display',
    title: 'Virtualized list',
    description: 'Large native collections with stable rendering.',
    keywords: ['flatlist', 'performance', 'pagination', 'list'],
  },
  {
    id: 'cards',
    group: 'surfaces',
    title: 'Cards & surfaces',
    description: 'Matte, elevated and glass information containers.',
    keywords: ['card', 'surface', 'paper', 'glass'],
  },
  {
    id: 'dialogs',
    group: 'surfaces',
    title: 'Dialogs',
    description: 'Focused confirmation without losing context.',
    keywords: ['dialog', 'modal', 'confirm', 'focus'],
  },
  {
    id: 'contextual-dock',
    group: 'patterns',
    title: 'Contextual dock',
    description: 'Stable bottom actions that adapt to the current selection.',
    keywords: ['dock', 'contextual', 'morphing', 'actions', 'selection'],
  },
  {
    id: 'tabs-segments',
    group: 'patterns',
    title: 'Tabs & segments',
    description: 'Small-scope view switching with persistent context.',
    keywords: ['tabs', 'segment', 'navigation', 'filter'],
  },
] as const satisfies readonly CatalogExample[];

const groupCopy: Record<CatalogGroup, { title: string; description: string }> =
  {
    foundations: {
      title: 'Foundations',
      description: 'Tokens and principles behind every native component.',
    },
    controls: {
      title: 'Controls',
      description: 'Clear, reachable actions and selection patterns.',
    },
    forms: {
      title: 'Forms',
      description: 'Input, validation and continuous values.',
    },
    feedback: {
      title: 'Feedback',
      description: 'Progress and recovery states that keep context.',
    },
    'data-display': {
      title: 'Data display',
      description: 'Readable rows, values and scalable collections.',
    },
    surfaces: {
      title: 'Surfaces',
      description: 'Material hierarchy from matte panels to liquid glass.',
    },
    patterns: {
      title: 'Patterns',
      description: 'Composed interactions for real mobile flows.',
    },
  };

const groupOrder: readonly CatalogGroup[] = [
  'foundations',
  'controls',
  'forms',
  'feedback',
  'data-display',
  'surfaces',
  'patterns',
];

export const CATALOG_EXAMPLES = examples;

export const CATALOG_SECTIONS: readonly CatalogSection[] = groupOrder.map(
  id => ({
    id,
    ...groupCopy[id],
    examples: examples.filter(example => example.group === id),
  }),
);

export const FOUNDATION_EXAMPLES = examples.filter(
  example => example.group === 'foundations',
);

export const COMPONENT_EXAMPLES = examples.filter(example =>
  ['controls', 'forms', 'feedback', 'data-display', 'surfaces'].includes(
    example.group,
  ),
);

export const PATTERN_EXAMPLES = examples.filter(
  example => example.group === 'patterns' || example.id === 'form-flow',
);

export const getCatalogExample = (id: string): CatalogExample | undefined =>
  examples.find(example => example.id === (id as CatalogExampleId));

export const filterCatalogExamples = (
  query: string,
): readonly CatalogExample[] => {
  const normalized = query.trim().toLocaleLowerCase();

  if (!normalized) {
    return examples;
  }

  return examples.filter(example =>
    [example.title, example.description, example.group, ...example.keywords]
      .join(' ')
      .toLocaleLowerCase()
      .includes(normalized),
  );
};
