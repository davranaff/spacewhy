import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import {
  Bold,
  Check,
  ChevronDown,
  ChevronRight,
  Circle,
  Copy,
  FileUp,
  Image as ImageIcon,
  Italic,
  Link,
  MapPin,
  Minus,
  Plus,
  Star,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';
import { DemoButton, DemoSurface } from './catalog-primitives';
import type { CatalogExampleId } from '../types/catalog.types';

type Props = Readonly<{ exampleId: CatalogExampleId }>;

export function CatalogParityPreview({ exampleId }: Props) {
  switch (exampleId) {
    case 'accordion':
      return <AccordionParity />;
    case 'autocomplete':
      return <AutocompleteParity />;
    case 'breadcrumbs':
    case 'pagination':
    case 'stepper':
    case 'navigation-bar':
      return <NavigationParity kind={exampleId} />;
    case 'pickers':
      return <PickerParity />;
    case 'rating':
      return <RatingParity />;
    case 'table':
    case 'timeline':
    case 'transfer-list':
    case 'tree-view':
    case 'organization-chart':
      return <StructuredParity kind={exampleId} />;
    case 'editor':
    case 'markdown':
    case 'text-max-line':
      return <DocumentParity kind={exampleId} />;
    case 'carousel':
    case 'image':
    case 'lightbox':
    case 'map':
    case 'upload':
      return <MediaParity kind={exampleId} />;
    case 'animate':
    case 'copy-to-clipboard':
    case 'scroll':
    case 'scroll-progress':
      return <UtilityParity kind={exampleId} />;
    default:
      return null;
  }
}

function AccordionParity() {
  const theme = useAppTheme();
  const [expanded, setExpanded] = useState(0);
  return (
    <DemoSurface
      title="Accordion variants"
      description="Tap a header to expand its native content region."
    >
      {['General settings', 'Notifications', 'Privacy & access'].map(
        (label, index) => {
          const open = expanded === index;
          return (
            <View
              key={label}
              style={[styles.rowBlock, { borderColor: theme.colors.border }]}
            >
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ expanded: open }}
                onPress={() => setExpanded(open ? -1 : index)}
                style={styles.row}
              >
                <Text
                  style={[
                    theme.typography.body,
                    styles.flex,
                    { color: theme.colors.text },
                  ]}
                >
                  {label}
                </Text>
                {open ? (
                  <ChevronDown color={theme.colors.textMuted} size={19} />
                ) : (
                  <ChevronRight color={theme.colors.textMuted} size={19} />
                )}
              </Pressable>
              {open ? (
                <Text
                  style={[styles.detail, { color: theme.colors.textMuted }]}
                >
                  The content stays in the reading order and preserves the
                  expanded state.
                </Text>
              ) : null}
            </View>
          );
        },
      )}
    </DemoSurface>
  );
}

function AutocompleteParity() {
  const theme = useAppTheme();
  const options = ['Design system', 'Dashboard', 'Data grid', 'Dialog'];
  const [query, setQuery] = useState('D');
  const [value, setValue] = useState('');
  const matches = options.filter(option =>
    option.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <DemoSurface
      title="Autocomplete"
      description="Suggestions filter live and remain fully tappable."
    >
      <GlassView variant="control" style={styles.inputGlass}>
        <TextInput
          accessibilityLabel="Search component"
          onChangeText={text => {
            setQuery(text);
            setValue('');
          }}
          placeholder="Search components"
          placeholderTextColor={theme.colors.textMuted}
          style={[
            theme.typography.body,
            styles.input,
            { color: theme.colors.text },
          ]}
          value={value || query}
        />
      </GlassView>
      {!value
        ? matches.map(option => (
            <Pressable
              key={option}
              onPress={() => {
                setValue(option);
                setQuery(option);
              }}
              style={styles.optionRow}
            >
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {option}
              </Text>
              <ChevronRight color={theme.colors.textMuted} size={18} />
            </Pressable>
          ))
        : null}
    </DemoSurface>
  );
}

function NavigationParity({
  kind,
}: Readonly<{
  kind: 'breadcrumbs' | 'pagination' | 'stepper' | 'navigation-bar';
}>) {
  const theme = useAppTheme();
  const [index, setIndex] = useState(1);
  if (kind === 'breadcrumbs') {
    return (
      <DemoSurface title="Breadcrumbs">
        <View style={styles.inline}>
          {['Home', 'Components', 'Breadcrumbs'].map((item, itemIndex) => (
            <View key={item} style={styles.inline}>
              <Text
                style={[
                  theme.typography.label,
                  {
                    color:
                      itemIndex === 2
                        ? theme.colors.text
                        : theme.colors.textMuted,
                  },
                ]}
              >
                {item}
              </Text>
              {itemIndex < 2 ? (
                <ChevronRight color={theme.colors.textMuted} size={15} />
              ) : null}
            </View>
          ))}
        </View>
      </DemoSurface>
    );
  }
  if (kind === 'navigation-bar') {
    return (
      <DemoSurface
        title="Navigation bars"
        description="Top and bottom native hierarchy"
      >
        <GlassView variant="control" style={styles.navBar}>
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            Back
          </Text>
          <Text
            style={[
              theme.typography.title,
              styles.navTitle,
              { color: theme.colors.text },
            ]}
          >
            Components
          </Text>
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            More
          </Text>
        </GlassView>
        <View style={styles.segmentRow}>
          {['Home', 'Search', 'Saved'].map((item, itemIndex) => (
            <DemoButton
              key={item}
              label={item}
              onPress={() => setIndex(itemIndex)}
              style={styles.flex}
              variant={index === itemIndex ? 'primary' : 'secondary'}
            />
          ))}
        </View>
      </DemoSurface>
    );
  }
  const labels =
    kind === 'stepper'
      ? ['Account', 'Profile', 'Done']
      : ['1', '2', '3', '4', '5'];
  return (
    <DemoSurface title={kind === 'stepper' ? 'Stepper' : 'Pagination'}>
      <View style={styles.stepRow}>
        {labels.map((label, itemIndex) => (
          <Pressable
            key={label}
            accessibilityState={{ selected: index === itemIndex }}
            onPress={() => setIndex(itemIndex)}
            style={[
              styles.step,
              {
                backgroundColor:
                  index === itemIndex
                    ? theme.colors.accent
                    : theme.colors.surfaceElevated,
                borderColor: theme.colors.border,
              },
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                {
                  color:
                    index === itemIndex
                      ? theme.colors.accentContrast
                      : theme.colors.text,
                },
              ]}
            >
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={[styles.centerText, { color: theme.colors.textMuted }]}>
        Current {kind === 'stepper' ? 'step' : 'page'}: {index + 1}
      </Text>
    </DemoSurface>
  );
}

function PickerParity() {
  const theme = useAppTheme();
  const [date, setDate] = useState(new Date(2026, 7, 15, 11, 30));
  return (
    <DemoSurface
      title="Native date & time picker"
      description={date.toLocaleString()}
    >
      <DateTimePicker
        accessibilityLabel="Select date and time"
        display="compact"
        mode="datetime"
        onChange={(_, next) => next && setDate(next)}
        value={date}
      />
      <Text style={[styles.centerText, { color: theme.colors.textMuted }]}>
        Uses the platform picker instead of a web-shaped imitation.
      </Text>
    </DemoSurface>
  );
}

function RatingParity() {
  const theme = useAppTheme();
  const [rating, setRating] = useState(4);
  return (
    <DemoSurface title="Editable rating" description={`${rating} of 5`}>
      <View style={styles.ratingRow}>
        {[1, 2, 3, 4, 5].map(value => (
          <Pressable
            key={value}
            accessibilityLabel={`${value} stars`}
            accessibilityState={{ selected: rating === value }}
            onPress={() => setRating(value)}
            style={styles.iconTarget}
          >
            <Star
              color={theme.colors.text}
              fill={value <= rating ? theme.colors.text : 'transparent'}
              size={30}
            />
          </Pressable>
        ))}
      </View>
    </DemoSurface>
  );
}

function StructuredParity({
  kind,
}: Readonly<{
  kind:
    | 'table'
    | 'timeline'
    | 'transfer-list'
    | 'tree-view'
    | 'organization-chart';
}>) {
  const theme = useAppTheme();
  const [expanded, setExpanded] = useState(true);
  const [chosen, setChosen] = useState(['Analytics']);
  if (kind === 'timeline') {
    return (
      <DemoSurface title="Timeline">
        {[
          'Release created',
          'Quality review passed',
          'Published to testers',
        ].map((item, index) => (
          <View key={item} style={styles.timelineRow}>
            <View style={styles.timelineRail}>
              <Circle
                color={theme.colors.text}
                fill={index === 2 ? theme.colors.text : 'transparent'}
                size={14}
              />
              {index < 2 ? (
                <View
                  style={[
                    styles.connector,
                    { backgroundColor: theme.colors.border },
                  ]}
                />
              ) : null}
            </View>
            <View style={styles.flex}>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {item}
              </Text>
              <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
                {10 + index}:0{index}
              </Text>
            </View>
          </View>
        ))}
      </DemoSurface>
    );
  }
  if (kind === 'transfer-list') {
    return (
      <DemoSurface title="Transfer List">
        <View style={styles.transferRow}>
          {['Available', 'Chosen'].map(side => (
            <GlassView
              key={side}
              variant="control"
              style={styles.transferColumn}
            >
              <Text
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                {side}
              </Text>
              {['Analytics', 'Billing', 'Files']
                .filter(item =>
                  side === 'Chosen'
                    ? chosen.includes(item)
                    : !chosen.includes(item),
                )
                .map(item => (
                  <Pressable
                    key={item}
                    onPress={() =>
                      setChosen(current =>
                        current.includes(item)
                          ? current.filter(value => value !== item)
                          : [...current, item],
                      )
                    }
                    style={styles.optionRow}
                  >
                    <Text
                      style={[styles.caption, { color: theme.colors.text }]}
                    >
                      {item}
                    </Text>
                    {side === 'Chosen' ? (
                      <Minus color={theme.colors.textMuted} size={15} />
                    ) : (
                      <Plus color={theme.colors.textMuted} size={15} />
                    )}
                  </Pressable>
                ))}
            </GlassView>
          ))}
        </View>
      </DemoSurface>
    );
  }
  if (kind === 'tree-view' || kind === 'organization-chart') {
    const root = kind === 'tree-view' ? 'src' : 'Maya Chen · CEO';
    return (
      <DemoSurface
        title={kind === 'tree-view' ? 'Tree View' : 'Organization Chart'}
      >
        <Pressable
          accessibilityState={{ expanded }}
          onPress={() => setExpanded(value => !value)}
          style={styles.treeRow}
        >
          {expanded ? (
            <ChevronDown color={theme.colors.text} size={18} />
          ) : (
            <ChevronRight color={theme.colors.text} size={18} />
          )}
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            {root}
          </Text>
        </Pressable>
        {expanded
          ? ['Design', 'Engineering', 'Operations'].map(item => (
              <View key={item} style={styles.treeChild}>
                <View
                  style={[
                    styles.treeLine,
                    { backgroundColor: theme.colors.border },
                  ]}
                />
                <Text
                  style={[
                    theme.typography.body,
                    { color: theme.colors.textMuted },
                  ]}
                >
                  {item}
                </Text>
              </View>
            ))
          : null}
      </DemoSurface>
    );
  }
  return (
    <DemoSurface title="Responsive table">
      <View style={[styles.tableHeader, { borderColor: theme.colors.border }]}>
        <Text
          style={[
            theme.typography.label,
            styles.tableName,
            { color: theme.colors.textMuted },
          ]}
        >
          Project
        </Text>
        <Text
          style={[theme.typography.label, { color: theme.colors.textMuted }]}
        >
          Status
        </Text>
      </View>
      {['Orbital UI', 'Glass controls', 'Mobile kit'].map((item, index) => (
        <View
          key={item}
          style={[styles.tableRow, { borderColor: theme.colors.border }]}
        >
          <Text
            style={[
              theme.typography.body,
              styles.tableName,
              { color: theme.colors.text },
            ]}
          >
            {item}
          </Text>
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            {index === 2 ? 'Review' : 'Active'}
          </Text>
        </View>
      ))}
    </DemoSurface>
  );
}

function DocumentParity({
  kind,
}: Readonly<{ kind: 'editor' | 'markdown' | 'text-max-line' }>) {
  const theme = useAppTheme();
  const [expanded, setExpanded] = useState(false);
  const [body, setBody] = useState(
    'Spacewhy UI Kit\n\nA native document surface with readable typography.',
  );
  if (kind === 'editor') {
    return (
      <DemoSurface title="Rich text editor">
        <View style={styles.toolbar}>
          {[Bold, Italic, Link].map((Icon, index) => (
            <Pressable
              key={index}
              accessibilityLabel={['Bold', 'Italic', 'Insert link'][index]}
              style={styles.iconTarget}
            >
              <Icon color={theme.colors.text} size={20} />
            </Pressable>
          ))}
        </View>
        <GlassView variant="control" style={styles.editor}>
          <TextInput
            multiline
            onChangeText={setBody}
            style={[
              theme.typography.body,
              styles.editorInput,
              { color: theme.colors.text },
            ]}
            value={body}
          />
        </GlassView>
      </DemoSurface>
    );
  }
  if (kind === 'markdown') {
    return (
      <DemoSurface title="Markdown">
        <Text style={[theme.typography.display, { color: theme.colors.text }]}>
          Mission notes
        </Text>
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          A structured document renders as native text:
        </Text>
        {['Fast local demo', 'Accessible controls', 'Theme-aware glass'].map(
          item => (
            <View key={item} style={styles.bulletRow}>
              <Text style={{ color: theme.colors.text }}>•</Text>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {item}
              </Text>
            </View>
          ),
        )}
        <GlassView variant="control" style={styles.codeBlock}>
          <Text style={[styles.mono, { color: theme.colors.text }]}>
            npm run ios
          </Text>
        </GlassView>
      </DemoSurface>
    );
  }
  return (
    <DemoSurface title="Text Max Line">
      <Text
        numberOfLines={expanded ? undefined : 3}
        style={[theme.typography.body, { color: theme.colors.text }]}
      >
        This deliberately longer paragraph demonstrates a stable collapsed
        reading state. It can expand without replacing the text, losing the
        reader position, or hiding the control from assistive technology.
      </Text>
      <DemoButton
        label={expanded ? 'Show less' : 'Read more'}
        onPress={() => setExpanded(value => !value)}
        variant="secondary"
      />
    </DemoSurface>
  );
}

function MediaParity({
  kind,
}: Readonly<{ kind: 'carousel' | 'image' | 'lightbox' | 'map' | 'upload' }>) {
  const theme = useAppTheme();
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState(false);
  if (kind === 'upload') {
    return (
      <DemoSurface title="Upload">
        <Pressable
          accessibilityRole="button"
          onPress={() => setSelected(true)}
          style={[styles.dropzone, { borderColor: theme.colors.border }]}
        >
          <FileUp color={theme.colors.text} size={30} />
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            {selected ? 'spacewhy-preview.png' : 'Choose a local image'}
          </Text>
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
            {selected ? 'Ready to upload · 1.8 MB' : 'PNG, JPG or WebP'}
          </Text>
        </Pressable>
        {selected ? (
          <DemoButton
            label="Remove file"
            onPress={() => setSelected(false)}
            variant="secondary"
          />
        ) : null}
      </DemoSurface>
    );
  }
  if (kind === 'map') {
    return (
      <DemoSurface title="Map">
        <View
          style={[
            styles.map,
            { backgroundColor: theme.colors.surfaceElevated },
          ]}
        >
          {[20, 45, 70].map(offset => (
            <View
              key={offset}
              style={[
                styles.mapRoad,
                { backgroundColor: theme.colors.border, left: `${offset}%` },
              ]}
            />
          ))}
          <View style={styles.mapPin}>
            <MapPin color={theme.colors.accentContrast} size={21} />
          </View>
        </View>
        <Text style={[theme.typography.label, { color: theme.colors.text }]}>
          Spacewhy Studio · Tashkent
        </Text>
      </DemoSurface>
    );
  }
  const labels = ['Mission control', 'Component system', 'Release dashboard'];
  return (
    <DemoSurface
      title={
        kind === 'carousel'
          ? 'Carousel'
          : kind === 'lightbox'
          ? 'Lightbox'
          : 'Responsive image'
      }
    >
      <View
        style={[
          styles.mediaFrame,
          kind === 'lightbox' && styles.lightboxFrame,
          { backgroundColor: theme.colors.surfaceElevated },
        ]}
      >
        <ImageIcon color={theme.colors.text} size={42} />
        <Text style={[theme.typography.title, { color: theme.colors.text }]}>
          {labels[index]}
        </Text>
      </View>
      {kind !== 'image' ? (
        <View style={styles.segmentRow}>
          {labels.map((_, itemIndex) => (
            <Pressable
              key={itemIndex}
              accessibilityLabel={`Show image ${itemIndex + 1}`}
              onPress={() => setIndex(itemIndex)}
              style={[
                styles.dot,
                {
                  backgroundColor:
                    index === itemIndex
                      ? theme.colors.text
                      : theme.colors.border,
                },
              ]}
            />
          ))}
        </View>
      ) : null}
    </DemoSurface>
  );
}

function UtilityParity({
  kind,
}: Readonly<{
  kind: 'animate' | 'copy-to-clipboard' | 'scroll' | 'scroll-progress';
}>) {
  const theme = useAppTheme();
  const [value, setValue] = useState(kind === 'scroll-progress' ? 42 : 0);
  const [done, setDone] = useState(false);
  if (kind === 'copy-to-clipboard') {
    return (
      <DemoSurface
        title="Copy to clipboard"
        description="The preview exposes the same success feedback contract without requesting external access."
      >
        <GlassView variant="control" style={styles.copyRow}>
          <Text
            numberOfLines={1}
            style={[
              theme.typography.body,
              styles.flex,
              { color: theme.colors.text },
            ]}
          >
            spacewhy://components
          </Text>
          <Pressable
            accessibilityLabel="Copy component link"
            onPress={() => setDone(true)}
            style={styles.iconTarget}
          >
            {done ? (
              <Check color={theme.colors.positive} size={22} />
            ) : (
              <Copy color={theme.colors.text} size={22} />
            )}
          </Pressable>
        </GlassView>
        <Text
          accessibilityLiveRegion="polite"
          style={[styles.centerText, { color: theme.colors.textMuted }]}
        >
          {done ? 'Copied state confirmed' : 'Ready to copy'}
        </Text>
      </DemoSurface>
    );
  }
  return (
    <DemoSurface
      title={
        kind === 'animate'
          ? 'Animate'
          : kind === 'scroll'
          ? 'Scroll controls'
          : 'Scroll Progress'
      }
    >
      <View
        style={[styles.progressTrack, { backgroundColor: theme.colors.border }]}
      >
        <View
          style={[
            styles.progressFill,
            {
              backgroundColor: theme.colors.text,
              width: `${Math.max(8, value)}%`,
            },
          ]}
        />
      </View>
      <DemoButton
        label={kind === 'animate' ? 'Run transition' : 'Advance position'}
        onPress={() => setValue(current => (current >= 100 ? 0 : current + 20))}
      />
      <Text style={[styles.centerText, { color: theme.colors.textMuted }]}>
        {kind === 'animate'
          ? 'Transform and opacity only · reduced-motion aware'
          : `${value}% of content`}
      </Text>
    </DemoSurface>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  inline: { alignItems: 'center', flexDirection: 'row', gap: 5 },
  rowBlock: { borderBottomWidth: StyleSheet.hairlineWidth },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    minHeight: 52,
    paddingHorizontal: 4,
  },
  detail: {
    fontSize: 14,
    lineHeight: 20,
    paddingBottom: 14,
    paddingHorizontal: 4,
  },
  inputGlass: { borderRadius: 18, minHeight: 52 },
  input: { minHeight: 52, paddingHorizontal: 14 },
  optionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
    paddingHorizontal: 6,
  },
  segmentRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
  },
  stepRow: { flexDirection: 'row', gap: 8, justifyContent: 'center' },
  step: {
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    height: 44,
    justifyContent: 'center',
    minWidth: 44,
    paddingHorizontal: 10,
  },
  centerText: { fontSize: 13, lineHeight: 18, textAlign: 'center' },
  navBar: {
    alignItems: 'center',
    borderRadius: 20,
    flexDirection: 'row',
    minHeight: 54,
    paddingHorizontal: 14,
  },
  navTitle: { flex: 1, textAlign: 'center' },
  ratingRow: { flexDirection: 'row', justifyContent: 'center' },
  iconTarget: {
    alignItems: 'center',
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  timelineRow: { flexDirection: 'row', gap: 12, minHeight: 62 },
  timelineRail: { alignItems: 'center', width: 18 },
  connector: { flex: 1, width: StyleSheet.hairlineWidth },
  caption: { fontSize: 13, lineHeight: 18 },
  transferRow: { flexDirection: 'row', gap: 10 },
  transferColumn: { borderRadius: 18, flex: 1, minHeight: 160, padding: 12 },
  treeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    minHeight: 48,
  },
  treeChild: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    minHeight: 42,
    paddingLeft: 12,
  },
  treeLine: { height: StyleSheet.hairlineWidth, width: 24 },
  tableHeader: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    paddingBottom: 10,
  },
  tableRow: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    minHeight: 48,
    paddingVertical: 12,
  },
  tableName: { flex: 1 },
  toolbar: { flexDirection: 'row', gap: 4 },
  editor: { borderRadius: 18, minHeight: 180 },
  editorInput: { minHeight: 180, padding: 14, textAlignVertical: 'top' },
  bulletRow: { alignItems: 'flex-start', flexDirection: 'row', gap: 8 },
  codeBlock: { borderRadius: 16, padding: 14 },
  mono: { fontFamily: 'Courier', fontSize: 14 },
  dropzone: {
    alignItems: 'center',
    borderRadius: 22,
    borderStyle: 'dashed',
    borderWidth: 1,
    gap: 8,
    justifyContent: 'center',
    minHeight: 180,
  },
  map: { borderRadius: 22, height: 220, overflow: 'hidden' },
  mapRoad: {
    height: '100%',
    opacity: 0.8,
    position: 'absolute',
    transform: [{ rotate: '24deg' }],
    width: 2,
  },
  mapPin: {
    alignItems: 'center',
    backgroundColor: '#111216',
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    left: '48%',
    position: 'absolute',
    top: '42%',
    width: 44,
  },
  mediaFrame: {
    alignItems: 'center',
    aspectRatio: 16 / 10,
    borderRadius: 22,
    gap: 10,
    justifyContent: 'center',
  },
  lightboxFrame: { aspectRatio: 3 / 4 },
  dot: { borderRadius: 5, height: 10, width: 10 },
  copyRow: {
    alignItems: 'center',
    borderRadius: 18,
    flexDirection: 'row',
    minHeight: 56,
    paddingLeft: 14,
  },
  progressTrack: { borderRadius: 4, height: 8, overflow: 'hidden' },
  progressFill: { borderRadius: 4, height: 8 },
});
