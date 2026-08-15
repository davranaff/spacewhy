import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import Slider from '@react-native-community/slider';
import {
  Bell,
  Check,
  ChevronRight,
  CircleAlert,
  CloudOff,
  Command,
  Heart,
  Info,
  Layers3,
  Palette,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  UserRound,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import {
  ContextualDock,
  type ContextualDockActions,
} from '@/widgets/contextual-dock';
import {
  DockIndicatorExamples,
  type DockIndicatorVariant,
} from '@/widgets/dock';

import {
  DemoButton,
  DemoSurface,
} from '@/features/catalog/components/catalog-primitives';
import type { CatalogExampleId } from '@/features/catalog/types/catalog.types';

type Props = Readonly<{ exampleId: CatalogExampleId }>;

const people = [
  { id: '1', name: 'Amelia Stone', role: 'Product designer', initials: 'AS' },
  { id: '2', name: 'Noah Kim', role: 'iOS engineer', initials: 'NK' },
  { id: '3', name: 'Mia Johnson', role: 'Research lead', initials: 'MJ' },
] as const;

export function CatalogExamplePreview({ exampleId }: Props) {
  switch (exampleId) {
    case 'colors':
      return <ColorPreview />;
    case 'typography':
      return <TypographyPreview />;
    case 'spacing':
      return <SpacingPreview />;
    case 'icons':
      return <IconsPreview />;
    case 'glass-material':
      return <GlassPreview />;
    case 'buttons':
      return <ButtonsPreview />;
    case 'selection-controls':
      return <SelectionPreview />;
    case 'chips-badges':
      return <ChipsPreview />;
    case 'text-fields':
      return <FieldsPreview />;
    case 'slider-progress':
      return <SliderPreview />;
    case 'form-flow':
      return <FormPreview />;
    case 'alerts':
      return <AlertsPreview />;
    case 'loading-states':
      return <LoadingPreview />;
    case 'empty-error':
      return <EmptyPreview />;
    case 'avatars-lists':
      return <PeoplePreview />;
    case 'metrics':
      return <MetricsPreview />;
    case 'virtualized-list':
      return <VirtualizedPreview />;
    case 'cards':
      return <CardsPreview />;
    case 'dialogs':
      return <DialogPreview />;
    case 'dock-indicators':
      return <DockIndicatorsPreview />;
    case 'contextual-dock':
      return <ContextualDockPreview />;
    case 'tabs-segments':
      return <SegmentsPreview />;
  }
}

function ColorPreview() {
  const theme = useAppTheme();
  const swatches = [
    ['Accent', theme.colors.accent],
    ['Positive', theme.colors.positive],
    ['Warning', theme.colors.warning],
    ['Negative', theme.colors.negative],
    ['Surface', theme.colors.surface],
    ['Elevated', theme.colors.surfaceElevated],
  ] as const;

  return (
    <DemoSurface
      title="Semantic palette"
      description="Roles stay stable when the theme changes."
    >
      <View style={styles.swatchGrid}>
        {swatches.map(([label, color]) => (
          <View key={label} style={styles.swatchItem}>
            <View
              accessibilityLabel={`${label} color ${color}`}
              style={[
                styles.swatch,
                { backgroundColor: color, borderColor: theme.colors.border },
              ]}
            />
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              {label}
            </Text>
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              {color}
            </Text>
          </View>
        ))}
      </View>
    </DemoSurface>
  );
}

function TypographyPreview() {
  const theme = useAppTheme();
  return (
    <DemoSurface
      title="Native type ramp"
      description="Supports system font scaling and readable line heights."
    >
      <Text style={[theme.typography.display, { color: theme.colors.text }]}>
        Display
      </Text>
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        Title
      </Text>
      <Text style={[theme.typography.body, { color: theme.colors.text }]}>
        Body text is calm, legible and long-form friendly.
      </Text>
      <Text style={[theme.typography.label, { color: theme.colors.textMuted }]}>
        LABEL / METADATA
      </Text>
    </DemoSurface>
  );
}

function SpacingPreview() {
  const theme = useAppTheme();
  const scale = Object.entries(theme.spacing);
  return (
    <DemoSurface
      title="Spacing scale"
      description="A small scale keeps layout rhythm consistent."
    >
      {scale.map(([name, value]) => (
        <View key={name} style={styles.scaleRow}>
          <Text
            style={[
              theme.typography.label,
              styles.scaleName,
              { color: theme.colors.textMuted },
            ]}
          >
            {name}
          </Text>
          <View
            style={[
              styles.scaleBar,
              {
                width: Math.max(value * 3, 12),
                backgroundColor: theme.colors.accent,
              },
            ]}
          />
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            {value} pt
          </Text>
        </View>
      ))}
      <View style={styles.radiusRow}>
        {(['sm', 'md', 'lg'] as const).map(key => (
          <View
            key={key}
            style={[
              styles.radiusSample,
              {
                borderRadius: theme.radius[key],
                borderColor: theme.colors.border,
                backgroundColor: theme.colors.surfaceElevated,
              },
            ]}
          >
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              {key}
            </Text>
          </View>
        ))}
      </View>
    </DemoSurface>
  );
}

function IconsPreview() {
  const theme = useAppTheme();
  const icons = [
    Palette,
    Command,
    Bell,
    Search,
    UserRound,
    Settings2,
    Heart,
    ShieldCheck,
  ];
  return (
    <DemoSurface
      title="Iconography"
      description="24 pt base grid, 1.8 pt stroke and semantic labels."
    >
      <View style={styles.iconGrid}>
        {icons.map((Icon, index) => (
          <View
            key={index}
            style={[styles.iconCell, { borderColor: theme.colors.border }]}
          >
            <Icon color={theme.colors.text} size={24} strokeWidth={1.8} />
          </View>
        ))}
      </View>
    </DemoSurface>
  );
}

function GlassPreview() {
  const theme = useAppTheme();
  return (
    <View style={styles.stack}>
      <DemoSurface
        title="Surface material"
        description="Content groups use a quieter glass depth."
        glass
      >
        <View style={styles.inline}>
          <Sparkles color={theme.colors.accent} size={22} />
          <Text
            style={[
              theme.typography.body,
              styles.flex,
              { color: theme.colors.text },
            ]}
          >
            Native on supported iOS versions, bounded blur fallback elsewhere.
          </Text>
        </View>
      </DemoSurface>
      <GlassView variant="control" interactive style={styles.controlGlass}>
        <Text style={[theme.typography.label, { color: theme.colors.text }]}>
          Interactive control glass
        </Text>
      </GlassView>
      <GlassView variant="floating" style={styles.floatingGlass}>
        <Layers3 color={theme.colors.text} size={20} />
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Floating material
        </Text>
      </GlassView>
    </View>
  );
}

function ButtonsPreview() {
  const [liked, setLiked] = useState(false);
  const theme = useAppTheme();
  return (
    <DemoSurface
      title="Action hierarchy"
      description="Every action meets the 44 pt minimum touch target."
    >
      <DemoButton label="Primary action" onPress={() => undefined} />
      <DemoButton
        label="Secondary"
        variant="secondary"
        onPress={() => undefined}
      />
      <DemoButton
        label="Quiet action"
        variant="quiet"
        onPress={() => undefined}
      />
      <DemoButton label="Disabled" disabled onPress={() => undefined} />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={
          liked ? 'Remove from favorites' : 'Add to favorites'
        }
        accessibilityState={{ selected: liked }}
        onPress={() => setLiked(value => !value)}
        style={[
          styles.iconButton,
          {
            backgroundColor: theme.colors.surfaceElevated,
            borderColor: theme.colors.border,
          },
        ]}
      >
        <Heart
          color={liked ? theme.colors.negative : theme.colors.text}
          fill={liked ? theme.colors.negative : 'transparent'}
          size={22}
        />
      </Pressable>
    </DemoSurface>
  );
}

function SelectionPreview() {
  const theme = useAppTheme();
  const [notifications, setNotifications] = useState(true);
  const [checked, setChecked] = useState(false);
  const [radio, setRadio] = useState<'daily' | 'weekly'>('daily');
  return (
    <DemoSurface title="Selection controls">
      <View style={styles.selectionRow}>
        <View style={styles.flex}>
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            Notifications
          </Text>
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
            Receive important product updates
          </Text>
        </View>
        <Switch
          accessibilityLabel="Notifications"
          onValueChange={setNotifications}
          trackColor={{ false: theme.colors.border, true: theme.colors.accent }}
          value={notifications}
        />
      </View>
      <Pressable
        accessibilityRole="checkbox"
        accessibilityLabel="Include archived projects"
        accessibilityState={{ checked }}
        onPress={() => setChecked(value => !value)}
        style={styles.selectionRow}
      >
        <SelectionMark selected={checked} />
        <Text
          style={[
            theme.typography.body,
            styles.flex,
            { color: theme.colors.text },
          ]}
        >
          Include archived projects
        </Text>
      </Pressable>
      {(['daily', 'weekly'] as const).map(value => (
        <Pressable
          key={value}
          accessibilityRole="radio"
          accessibilityLabel={`${value} summary`}
          accessibilityState={{ selected: radio === value }}
          onPress={() => setRadio(value)}
          style={styles.selectionRow}
        >
          <SelectionMark radio selected={radio === value} />
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            {value === 'daily' ? 'Daily summary' : 'Weekly summary'}
          </Text>
        </Pressable>
      ))}
    </DemoSurface>
  );
}

function SelectionMark({
  selected,
  radio = false,
}: {
  selected: boolean;
  radio?: boolean;
}) {
  const theme = useAppTheme();
  const selectedStyle = {
    borderColor: selected ? theme.colors.accent : theme.colors.border,
    backgroundColor: selected ? theme.colors.accent : 'transparent',
  };
  return (
    <View style={[styles.selectionMark, radio && styles.radio, selectedStyle]}>
      {selected ? (
        <Check color={theme.colors.accentContrast} size={14} strokeWidth={3} />
      ) : null}
    </View>
  );
}

function ChipsPreview() {
  const theme = useAppTheme();
  const [active, setActive] = useState('All');
  return (
    <DemoSurface title="Compact controls">
      <View style={styles.wrap}>
        {['All', 'Design', 'Engineering', 'Research'].map(label => {
          const selected = active === label;
          return (
            <Pressable
              key={label}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => setActive(label)}
              style={[
                styles.chip,
                {
                  backgroundColor: selected
                    ? theme.colors.accent
                    : theme.colors.surfaceElevated,
                  borderColor: selected
                    ? theme.colors.accent
                    : theme.colors.border,
                },
              ]}
            >
              <Text
                style={[
                  theme.typography.label,
                  {
                    color: selected
                      ? theme.colors.accentContrast
                      : theme.colors.text,
                  },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <View style={styles.inline}>
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Inbox
        </Text>
        <View
          style={[styles.badge, { backgroundColor: theme.colors.negative }]}
        >
          <Text style={[theme.typography.label, styles.badgeText]}>12</Text>
        </View>
      </View>
    </DemoSurface>
  );
}

function FieldsPreview() {
  const [name, setName] = useState('Spacewhy');
  const [email, setEmail] = useState('invalid address');
  return (
    <DemoSurface
      title="Form fields"
      description="Labels never rely on placeholder text alone."
    >
      <DemoField
        label="Workspace name"
        value={name}
        onChangeText={setName}
        hint="Visible to every team member"
      />
      <DemoField
        label="Contact email"
        value={email}
        onChangeText={setEmail}
        error="Enter a valid email address"
        keyboardType="email-address"
      />
    </DemoSurface>
  );
}

function DemoField({
  label,
  hint,
  error,
  ...props
}: React.ComponentProps<typeof TextInput> & {
  label: string;
  hint?: string;
  error?: string;
}) {
  const theme = useAppTheme();
  return (
    <View style={styles.fieldGroup}>
      <Text
        style={[
          theme.typography.label,
          { color: error ? theme.colors.negative : theme.colors.text },
        ]}
      >
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        accessibilityHint={hint}
        placeholderTextColor={theme.colors.textMuted}
        style={[
          theme.typography.body,
          styles.field,
          {
            color: theme.colors.text,
            backgroundColor: theme.colors.surfaceElevated,
            borderColor: error ? theme.colors.negative : theme.colors.border,
          },
        ]}
        {...props}
      />
      {error || hint ? (
        <Text
          style={[
            styles.caption,
            { color: error ? theme.colors.negative : theme.colors.textMuted },
          ]}
        >
          {error ?? hint}
        </Text>
      ) : null}
    </View>
  );
}

function SliderPreview() {
  const theme = useAppTheme();
  const [value, setValue] = useState(64);
  return (
    <DemoSurface title="Continuous values">
      <View style={styles.labelRow}>
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Intensity
        </Text>
        <Text
          accessibilityLiveRegion="polite"
          style={[theme.typography.label, { color: theme.colors.textMuted }]}
        >
          {Math.round(value)}%
        </Text>
      </View>
      <Slider
        accessibilityLabel="Intensity"
        maximumTrackTintColor={theme.colors.border}
        maximumValue={100}
        minimumTrackTintColor={theme.colors.accent}
        minimumValue={0}
        onValueChange={setValue}
        step={1}
        thumbTintColor={theme.colors.text}
        value={value}
      />
      <View
        style={[
          styles.progressTrack,
          { backgroundColor: theme.colors.surfaceElevated },
        ]}
      >
        <View
          style={[
            styles.progressValue,
            { backgroundColor: theme.colors.accent, width: `${value}%` },
          ]}
        />
      </View>
    </DemoSurface>
  );
}

function FormPreview() {
  const theme = useAppTheme();
  const [name, setName] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const error = submitted && name.trim().length < 2;
  return (
    <DemoSurface
      title="Create a workspace"
      description="A small complete flow with inline validation."
    >
      <DemoField
        label="Workspace name"
        value={name}
        onChangeText={value => {
          setName(value);
          setSubmitted(false);
        }}
        error={error ? 'Use at least two characters' : undefined}
        returnKeyType="done"
      />
      <DemoButton label="Create workspace" onPress={() => setSubmitted(true)} />
      {submitted && !error ? (
        <View accessibilityLiveRegion="polite" style={styles.inline}>
          <Check color={theme.colors.positive} size={20} />
          <Text
            style={[theme.typography.body, { color: theme.colors.positive }]}
          >
            Workspace ready
          </Text>
        </View>
      ) : null}
    </DemoSurface>
  );
}

function AlertsPreview() {
  const theme = useAppTheme();
  const alerts = [
    {
      label: 'Information',
      body: 'Your settings sync across devices.',
      color: theme.colors.accent,
      Icon: Info,
    },
    {
      label: 'Success',
      body: 'The latest changes are published.',
      color: theme.colors.positive,
      Icon: Check,
    },
    {
      label: 'Warning',
      body: 'Two fields still need your attention.',
      color: theme.colors.warning,
      Icon: TriangleAlert,
    },
    {
      label: 'Error',
      body: 'We could not save this version.',
      color: theme.colors.negative,
      Icon: CircleAlert,
    },
  ];
  return (
    <View style={styles.stack}>
      {alerts.map(({ label, body, color, Icon }) => (
        <View
          key={label}
          accessibilityRole="alert"
          style={[
            styles.alert,
            { backgroundColor: `${color}18`, borderColor: `${color}55` },
          ]}
        >
          <Icon color={color} size={21} />
          <View style={styles.flex}>
            <Text style={[theme.typography.label, { color }]}>{label}</Text>
            <Text
              style={[
                theme.typography.body,
                styles.alertBody,
                { color: theme.colors.text },
              ]}
            >
              {body}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function LoadingPreview() {
  const theme = useAppTheme();
  return (
    <DemoSurface title="Loading without layout shifts">
      <View style={styles.inline}>
        <ActivityIndicator color={theme.colors.accent} />
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Syncing latest components…
        </Text>
      </View>
      {[1, 2, 3].map(value => (
        <View key={value} style={styles.skeletonRow}>
          <View
            style={[
              styles.skeletonAvatar,
              { backgroundColor: theme.colors.surfaceElevated },
            ]}
          />
          <View style={styles.flex}>
            <View
              style={[
                styles.skeletonLine,
                {
                  backgroundColor: theme.colors.surfaceElevated,
                  width: `${84 - value * 8}%`,
                },
              ]}
            />
            <View
              style={[
                styles.skeletonLine,
                styles.skeletonLineShort,
                { backgroundColor: theme.colors.surfaceElevated },
              ]}
            />
          </View>
        </View>
      ))}
    </DemoSurface>
  );
}

function EmptyPreview() {
  const theme = useAppTheme();
  const [offline, setOffline] = useState(false);
  return (
    <DemoSurface
      title={offline ? 'You are offline' : 'Nothing here yet'}
      description={
        offline
          ? 'Reconnect and retry without losing your filters.'
          : 'Create your first saved view to see it here.'
      }
    >
      <View style={styles.emptyIcon}>
        {offline ? (
          <CloudOff color={theme.colors.warning} size={32} />
        ) : (
          <Sparkles color={theme.colors.accent} size={32} />
        )}
      </View>
      <DemoButton
        label={offline ? 'Try again' : 'Create a view'}
        onPress={() => setOffline(value => !value)}
      />
    </DemoSurface>
  );
}

function PeoplePreview() {
  const theme = useAppTheme();
  return (
    <DemoSurface title="Team members">
      {people.map(person => (
        <Pressable
          key={person.id}
          accessibilityRole="button"
          accessibilityLabel={`${person.name}, ${person.role}`}
          style={styles.personRow}
        >
          <View
            style={[
              styles.avatar,
              {
                backgroundColor: theme.colors.surfaceElevated,
                borderColor: theme.colors.border,
              },
            ]}
          >
            <Text
              style={[theme.typography.label, { color: theme.colors.accent }]}
            >
              {person.initials}
            </Text>
          </View>
          <View style={styles.flex}>
            <Text style={[theme.typography.body, { color: theme.colors.text }]}>
              {person.name}
            </Text>
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              {person.role}
            </Text>
          </View>
          <ChevronRight color={theme.colors.textMuted} size={19} />
        </Pressable>
      ))}
    </DemoSurface>
  );
}

function MetricsPreview() {
  const theme = useAppTheme();
  const metrics = [
    ['Active users', '18,765', '+2.6%', theme.colors.positive],
    ['Installed', '4,876', '+0.2%', theme.colors.accent],
    ['Downloads', '678', '-0.1%', theme.colors.negative],
  ] as const;
  return (
    <View style={styles.stack}>
      {metrics.map(([label, value, trend, color]) => (
        <GlassView key={label} variant="surface" style={styles.metricCard}>
          <View style={styles.labelRow}>
            <Text
              style={[
                theme.typography.label,
                { color: theme.colors.textMuted },
              ]}
            >
              {label}
            </Text>
            <Text style={[theme.typography.label, { color }]}>{trend}</Text>
          </View>
          <Text
            style={[theme.typography.display, { color: theme.colors.text }]}
          >
            {value}
          </Text>
        </GlassView>
      ))}
    </View>
  );
}

function VirtualizedPreview() {
  const theme = useAppTheme();
  const rows = useMemo(
    () =>
      Array.from({ length: 80 }, (_, index) => ({
        id: String(index),
        title: `Component token ${String(index + 1).padStart(2, '0')}`,
      })),
    [],
  );
  return (
    <View
      style={[
        styles.virtualizedFrame,
        {
          borderColor: theme.colors.border,
          backgroundColor: theme.colors.surface,
        },
      ]}
    >
      <FlatList
        accessibilityLabel="Virtualized token list"
        data={rows}
        getItemLayout={(_, index) => ({
          length: 58,
          offset: 58 * index,
          index,
        })}
        initialNumToRender={8}
        keyExtractor={item => item.id}
        nestedScrollEnabled
        renderItem={({ item, index }) => (
          <View
            style={[
              styles.virtualRow,
              { borderBottomColor: theme.colors.border },
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                { color: theme.colors.textMuted },
              ]}
            >
              {String(index + 1).padStart(2, '0')}
            </Text>
            <Text
              style={[
                theme.typography.body,
                styles.flex,
                { color: theme.colors.text },
              ]}
            >
              {item.title}
            </Text>
          </View>
        )}
        style={styles.virtualList}
        windowSize={5}
      />
    </View>
  );
}

function CardsPreview() {
  const theme = useAppTheme();
  return (
    <View style={styles.stack}>
      <DemoSurface
        title="Matte surface"
        description="Best for dense, scrolling content."
      >
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Low visual noise and strong contrast.
        </Text>
      </DemoSurface>
      <DemoSurface
        title="Glass surface"
        description="Use over meaningful background depth."
        glass
      >
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Material is reserved for hierarchy, not decoration.
        </Text>
      </DemoSurface>
    </View>
  );
}

function DialogPreview() {
  const theme = useAppTheme();
  const [open, setOpen] = useState(false);
  return (
    <DemoSurface
      title="Focused confirmation"
      description="The system modal traps interaction until resolved."
    >
      <DemoButton label="Open dialog" onPress={() => setOpen(true)} />
      <Modal
        animationType="fade"
        onRequestClose={() => setOpen(false)}
        transparent
        visible={open}
      >
        <View style={styles.modalBackdrop}>
          <GlassView
            accessibilityViewIsModal
            variant="floating"
            style={styles.dialog}
          >
            <Text
              accessibilityRole="header"
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              Delete this draft?
            </Text>
            <Text
              style={[theme.typography.body, { color: theme.colors.textMuted }]}
            >
              This action cannot be undone.
            </Text>
            <View style={styles.dialogActions}>
              <DemoButton
                label="Cancel"
                variant="secondary"
                onPress={() => setOpen(false)}
                style={styles.flex}
              />
              <DemoButton
                label="Delete"
                variant="danger"
                onPress={() => setOpen(false)}
                style={styles.flex}
              />
            </View>
          </GlassView>
        </View>
      </Modal>
    </DemoSurface>
  );
}

const indicatorVariants: readonly {
  label: string;
  variant: DockIndicatorVariant;
}[] = [
  { label: 'Dot', variant: 'dot' },
  { label: 'Glass pill', variant: 'glass-pill' },
  { label: 'Segmented', variant: 'segmented' },
  { label: 'Progress', variant: 'progress' },
];

function DockIndicatorsPreview() {
  const theme = useAppTheme();
  const [activeIndex, setActiveIndex] = useState(1);
  const pageCount = 4;

  return (
    <DemoSurface
      title="Page and dock indicators"
      description="Alternative indicators remain catalog-only; production navigation keeps one stable active pill."
    >
      {indicatorVariants.map(({ label, variant }) => (
        <View
          key={variant}
          style={[
            styles.indicatorSample,
            { borderBottomColor: theme.colors.border },
          ]}
        >
          <Text
            style={[
              theme.typography.label,
              styles.indicatorLabel,
              { color: theme.colors.textMuted },
            ]}
          >
            {label}
          </Text>
          <DockIndicatorExamples
            activeIndex={activeIndex}
            count={pageCount}
            variant={variant}
          />
        </View>
      ))}
      <View style={styles.dialogActions}>
        <DemoButton
          label="Previous"
          variant="secondary"
          onPress={() =>
            setActiveIndex(index => (index - 1 + pageCount) % pageCount)
          }
          style={styles.flex}
        />
        <DemoButton
          label="Next"
          onPress={() => setActiveIndex(index => (index + 1) % pageCount)}
          style={styles.flex}
        />
      </View>
    </DemoSurface>
  );
}

function ContextualDockPreview() {
  const theme = useAppTheme();
  const [selectionCount, setSelectionCount] = useState<1 | 2>(1);
  const [lastAction, setLastAction] = useState('No action selected.');
  const actions = useMemo<ContextualDockActions>(
    () =>
      selectionCount === 1
        ? [
            {
              id: 'inspect',
              label: 'Inspect',
              icon: 'settings',
              onPress: () => setLastAction('Opened the selected item.'),
            },
            {
              id: 'refresh',
              label: 'Refresh',
              icon: 'refresh',
              onPress: () => setLastAction('Refreshed one selected item.'),
            },
          ]
        : [
            {
              id: 'refresh',
              label: 'Sync',
              icon: 'refresh',
              onPress: () => setLastAction('Synced two selected items.'),
            },
            {
              id: 'edit',
              label: 'Edit',
              icon: 'settings',
              onPress: () => setLastAction('Opened bulk edit.'),
            },
            {
              id: 'remove',
              label: 'Remove',
              icon: 'close',
              destructive: true,
              onPress: () => setLastAction('Removed two demo selections.'),
            },
          ],
    [selectionCount],
  );

  return (
    <View style={styles.stack}>
      <DemoSurface
        title="Selection-aware actions"
        description="The action set changes without reordering the primary navigation destinations."
      >
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          {selectionCount} {selectionCount === 1 ? 'item' : 'items'} selected
        </Text>
        <DemoButton
          label={selectionCount === 1 ? 'Select another item' : 'Keep one item'}
          variant="secondary"
          onPress={() => {
            setSelectionCount(count => (count === 1 ? 2 : 1));
            setLastAction('Contextual actions adapted to the selection.');
          }}
        />
        <Text
          accessibilityLiveRegion="polite"
          style={[styles.caption, { color: theme.colors.textMuted }]}
        >
          {lastAction}
        </Text>
      </DemoSurface>
      <ContextualDock
        key={`contextual-${selectionCount}`}
        accessibilityLabel={`Actions for ${selectionCount} selected ${
          selectionCount === 1 ? 'item' : 'items'
        }`}
        actions={actions}
      />
    </View>
  );
}

function SegmentsPreview() {
  const theme = useAppTheme();
  const [active, setActive] = useState('Preview');
  return (
    <DemoSurface title="Segmented control">
      <View
        accessibilityRole="tablist"
        style={[
          styles.segmented,
          { backgroundColor: theme.colors.surfaceElevated },
        ]}
      >
        {['Preview', 'Specs', 'Usage'].map(label => {
          const selected = active === label;
          return (
            <Pressable
              key={label}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              onPress={() => setActive(label)}
              style={[
                styles.segment,
                selected && {
                  backgroundColor: theme.colors.surface,
                  borderColor: theme.colors.border,
                },
              ]}
            >
              <Text
                style={[
                  theme.typography.label,
                  {
                    color: selected
                      ? theme.colors.text
                      : theme.colors.textMuted,
                  },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <Text
        accessibilityLiveRegion="polite"
        style={[theme.typography.body, { color: theme.colors.text }]}
      >
        Showing the {active.toLocaleLowerCase()} view.
      </Text>
    </DemoSurface>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  stack: { gap: 12 },
  inline: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  caption: { fontSize: 12, lineHeight: 17 },
  swatchGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 14 },
  swatchItem: { width: '29%', gap: 6 },
  swatch: {
    height: 64,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
  },
  scaleRow: {
    minHeight: 36,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  scaleName: { width: 34 },
  scaleBar: { height: 8, borderRadius: 4 },
  radiusRow: { flexDirection: 'row', gap: 10 },
  radiusSample: {
    flex: 1,
    minHeight: 72,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: StyleSheet.hairlineWidth,
  },
  iconGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  iconCell: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
  },
  controlGlass: {
    minHeight: 52,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  floatingGlass: {
    minHeight: 64,
    borderRadius: 24,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 18,
  },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectionRow: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  selectionMark: {
    width: 24,
    height: 24,
    borderRadius: 7,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radio: { borderRadius: 12 },
  chip: {
    minHeight: 44,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    minWidth: 25,
    height: 25,
    borderRadius: 13,
    paddingHorizontal: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: { color: '#FFFFFF' },
  fieldGroup: { gap: 7 },
  field: {
    minHeight: 52,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  progressTrack: { height: 9, borderRadius: 5, overflow: 'hidden' },
  progressValue: { height: '100%', borderRadius: 5 },
  alert: {
    borderRadius: 19,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 15,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 11,
  },
  alertBody: { fontSize: 14, lineHeight: 19 },
  skeletonRow: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  skeletonAvatar: { width: 42, height: 42, borderRadius: 21 },
  skeletonLine: { height: 10, borderRadius: 5 },
  skeletonLineShort: { width: '44%', marginTop: 8 },
  emptyIcon: { height: 68, alignItems: 'center', justifyContent: 'center' },
  personRow: {
    minHeight: 62,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricCard: { padding: 18, borderRadius: 24, gap: 9 },
  virtualizedFrame: {
    height: 360,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  virtualList: { flex: 1 },
  virtualRow: {
    height: 58,
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.62)',
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dialog: {
    width: '100%',
    maxWidth: 420,
    borderRadius: 28,
    padding: 22,
    gap: 14,
  },
  dialogActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  indicatorSample: {
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 48,
  },
  indicatorLabel: { flex: 1 },
  segmented: { borderRadius: 17, padding: 4, flexDirection: 'row' },
  segment: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
