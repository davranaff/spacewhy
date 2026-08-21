import type {
  CatalogExample,
  CatalogExampleId,
  CatalogGroup,
  CatalogSection,
} from '@/features/catalog/types/catalog.types';

type ExampleInput = readonly [
  id: CatalogExampleId,
  title: string,
  description: string,
  keywords?: readonly string[],
];

const foundationInputs: readonly ExampleInput[] = [
  [
    'colors',
    'Colors',
    'Theme palette, semantic roles and accessible tonal scales.',
  ],
  [
    'typography',
    'Typography',
    'Display, heading, body, caption and responsive native text styles.',
  ],
  [
    'shadows',
    'Shadows',
    'Elevation levels, ambient shadows and glass surface depth.',
  ],
  [
    'grid',
    'Grid',
    'Responsive columns, gutters, spacing and layout proportions.',
  ],
  [
    'icons',
    'Icons',
    'The original component icon family and native glyph sizing.',
  ],
];

const muiInputs: readonly ExampleInput[] = [
  [
    'accordion',
    'Accordion',
    'Expandable content panels with one or multiple open sections.',
  ],
  [
    'alert',
    'Alert',
    'Success, information, warning and error messages with actions.',
  ],
  [
    'autocomplete',
    'Autocomplete',
    'Searchable suggestions, single select and multi-value input.',
  ],
  [
    'avatar',
    'Avatar',
    'Image, initials, grouped and status-aware identity treatments.',
  ],
  [
    'badge',
    'Badge',
    'Notification counts, dots, maximum values and placement variants.',
  ],
  [
    'breadcrumbs',
    'Breadcrumbs',
    'Compact hierarchy trails adapted to mobile navigation.',
  ],
  [
    'buttons',
    'Buttons',
    'Contained, outlined, text, icon, loading and disabled actions.',
  ],
  [
    'checkbox',
    'Checkbox',
    'Selected, indeterminate, disabled and grouped selection states.',
  ],
  ['chip', 'Chip', 'Filled, outlined, selectable, deletable and avatar chips.'],
  ['dialog', 'Dialog', 'Alert, confirmation and full-screen modal patterns.'],
  [
    'list',
    'List',
    'Dense rows, leading media, metadata, actions and nested items.',
  ],
  [
    'menu',
    'Menu',
    'Anchored action menus, selected items and contextual commands.',
  ],
  [
    'pagination',
    'Pagination',
    'Page navigation, compact counters and boundary states.',
  ],
  [
    'pickers',
    'Pickers',
    'Native date and time selection with formatted values.',
  ],
  ['popover', 'Popover', 'Contextual floating content anchored to a trigger.'],
  [
    'progress',
    'Progress',
    'Circular, linear, determinate and indeterminate progress.',
  ],
  [
    'radio-button',
    'Radio Button',
    'Exclusive selection, grouped options and disabled states.',
  ],
  [
    'rating',
    'Rating',
    'Read-only and editable rating with precision feedback.',
  ],
  [
    'slider',
    'Slider',
    'Single-value, stepped and disabled continuous controls.',
  ],
  ['stepper', 'Stepper', 'Horizontal and vertical multi-step task progress.'],
  ['switch', 'Switch', 'On, off, disabled and labelled preference controls.'],
  [
    'table',
    'Table',
    'Sortable data rows, selection and compact mobile presentation.',
  ],
  ['tabs', 'Tabs', 'Scrollable, fixed and icon-assisted content tabs.'],
  [
    'textfield',
    'Textfield',
    'Standard, filled, multiline, secure and validation fields.',
  ],
  [
    'timeline',
    'Timeline',
    'Status history with connectors, timestamps and metadata.',
  ],
  ['tooltip', 'Tooltip', 'Accessible contextual hints for compact controls.'],
  [
    'transfer-list',
    'Transfer List',
    'Move selected items between available and chosen sets.',
  ],
  [
    'tree-view',
    'Tree View',
    'Expandable hierarchical navigation and selection.',
  ],
  [
    'data-grid',
    'Data Grid',
    'Virtualized records, sorting, filtering and row selection.',
  ],
];

const extraInputs: readonly ExampleInput[] = [
  ['chart', 'Chart', 'Line, area, bar, mixed and radial data visualization.'],
  [
    'map',
    'Map',
    'Native map-style markers, selected places and location sheets.',
  ],
  [
    'editor',
    'Editor',
    'Rich-text toolbar, editable document and formatting state.',
  ],
  [
    'copy-to-clipboard',
    'Copy to clipboard',
    'Copy actions with immediate success feedback.',
  ],
  [
    'upload',
    'Upload',
    'File selection, image preview, progress, errors and removal.',
  ],
  [
    'carousel',
    'Carousel',
    'Swipeable media, pagination dots and previous/next actions.',
  ],
  [
    'multi-language',
    'Multi language',
    'Locale selection and live translated interface copy.',
  ],
  [
    'animate',
    'Animate',
    'Purposeful enter, press and layout transitions with reduced motion.',
  ],
  [
    'mega-menu',
    'Mega Menu',
    'Grouped navigation adapted to a native expandable sheet.',
  ],
  [
    'form-validation',
    'Form Validation',
    'Complete labelled form with inline validation and submit state.',
  ],
  [
    'lightbox',
    'Lightbox',
    'Full-screen media browsing with dismiss and paging controls.',
  ],
  [
    'image',
    'Image',
    'Aspect ratios, placeholders, loading and fallback states.',
  ],
  [
    'label',
    'Label',
    'Filled, outlined and status labels with semantic colors.',
  ],
  [
    'scroll',
    'Scroll',
    'Directional scroll affordances and position-aware actions.',
  ],
  [
    'scroll-progress',
    'Scroll Progress',
    'Document reading progress tied to content position.',
  ],
  [
    'snackbar',
    'Snackbar',
    'Temporary success, information and recovery messages.',
  ],
  [
    'text-max-line',
    'Text Max Line',
    'Predictable line clamping with expand and collapse.',
  ],
  [
    'navigation-bar',
    'Navigation Bar',
    'Native top bar, bottom bar and active location states.',
  ],
  [
    'organization-chart',
    'Organization Chart',
    'Expandable people hierarchy and reporting lines.',
  ],
  [
    'markdown',
    'Markdown',
    'Structured headings, lists, quotes, links and code blocks.',
  ],
];

function toExamples(
  group: CatalogGroup,
  inputs: readonly ExampleInput[],
): readonly CatalogExample[] {
  return inputs.map(([id, title, description, keywords = []]) => ({
    id,
    group,
    title,
    description,
    keywords: [id, title, group, ...keywords],
  }));
}

export const FOUNDATION_EXAMPLES = toExamples('foundations', foundationInputs);
export const COMPONENT_EXAMPLES = toExamples('mui', muiInputs);
export const EXTRA_EXAMPLES = toExamples('extra', extraInputs);

// Kept as a compatibility export for the existing Patterns stack while its
// visible contract now matches the original UI kit's Extra section.
export const PATTERN_EXAMPLES = EXTRA_EXAMPLES;

export const CATALOG_EXAMPLES = [
  ...FOUNDATION_EXAMPLES,
  ...COMPONENT_EXAMPLES,
  ...EXTRA_EXAMPLES,
] as const;

const sectionCopy: Record<
  CatalogGroup,
  Readonly<{ title: string; description: string }>
> = {
  foundations: {
    title: 'Foundations',
    description: 'The same visual foundations exposed by the web UI kit.',
  },
  mui: {
    title: 'MUI components',
    description:
      'Native counterparts for every component route in the web kit.',
  },
  extra: {
    title: 'Extra components',
    description: 'Advanced and third-party patterns adapted for mobile.',
  },
};

export const CATALOG_SECTIONS: readonly CatalogSection[] = (
  ['foundations', 'mui', 'extra'] as const
).map(id => ({
  id,
  ...sectionCopy[id],
  examples: CATALOG_EXAMPLES.filter(example => example.group === id),
}));

export const getCatalogExample = (id: string): CatalogExample | undefined =>
  CATALOG_EXAMPLES.find(example => example.id === (id as CatalogExampleId));

export const filterCatalogExamples = (
  query: string,
): readonly CatalogExample[] => {
  const normalized = query.trim().toLocaleLowerCase();

  if (!normalized) return CATALOG_EXAMPLES;

  return CATALOG_EXAMPLES.filter(example =>
    [example.title, example.description, example.group, ...example.keywords]
      .join(' ')
      .toLocaleLowerCase()
      .includes(normalized),
  );
};
