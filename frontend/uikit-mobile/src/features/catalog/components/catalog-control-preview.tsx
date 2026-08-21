import { useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import {
  Bell,
  Check,
  CheckCircle2,
  CircleAlert,
  Info,
  Minus,
  MoreHorizontal,
  TriangleAlert,
  X,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

import { DemoButton, DemoSurface } from './catalog-primitives';
import type { CatalogExampleId } from '../types/catalog.types';

export const CONTROL_PARITY_EXAMPLES = new Set<CatalogExampleId>([
  'alert',
  'badge',
  'checkbox',
  'chip',
  'dialog',
  'label',
  'menu',
  'multi-language',
  'popover',
  'progress',
  'radio-button',
  'snackbar',
  'switch',
  'tabs',
  'tooltip',
]);

export function CatalogControlPreview({
  exampleId,
}: Readonly<{ exampleId: CatalogExampleId }>) {
  switch (exampleId) {
    case 'alert':
      return <AlertVariants />;
    case 'badge':
      return <BadgeVariants />;
    case 'checkbox':
      return <CheckboxVariants />;
    case 'chip':
      return <ChipVariants />;
    case 'dialog':
      return <DialogVariants />;
    case 'label':
      return <LabelVariants />;
    case 'menu':
      return <MenuVariants />;
    case 'multi-language':
      return <LanguageVariants />;
    case 'popover':
      return <PopoverVariants />;
    case 'progress':
      return <ProgressVariants />;
    case 'radio-button':
      return <RadioVariants />;
    case 'snackbar':
      return <SnackbarVariants />;
    case 'switch':
      return <SwitchVariants />;
    case 'tabs':
      return <TabsVariants />;
    case 'tooltip':
      return <TooltipVariants />;
    default:
      return null;
  }
}

function AlertVariants() {
  const theme = useAppTheme();
  const alerts = [
    {
      title: 'Information',
      body: 'A new component version is available.',
      color: theme.colors.text,
      Icon: Info,
    },
    {
      title: 'Success',
      body: 'Changes were saved locally.',
      color: theme.colors.positive,
      Icon: CheckCircle2,
    },
    {
      title: 'Warning',
      body: 'Review two incomplete fields.',
      color: theme.colors.warning,
      Icon: TriangleAlert,
    },
    {
      title: 'Error',
      body: 'The preview could not be exported.',
      color: theme.colors.negative,
      Icon: CircleAlert,
    },
  ];
  return (
    <View style={styles.stack}>
      {alerts.map(({ title, body, color, Icon }) => (
        <GlassView
          accessibilityRole="alert"
          key={title}
          variant="surface"
          style={[styles.alert, { borderColor: color }]}
        >
          <Icon color={color} size={22} />
          <View style={styles.flex}>
            <Text style={[theme.typography.label, { color }]}>{title}</Text>
            <Text style={[styles.caption, { color: theme.colors.text }]}>
              {body}
            </Text>
          </View>
          <Pressable
            accessibilityLabel={`Dismiss ${title}`}
            style={styles.iconTarget}
          >
            <X color={theme.colors.textMuted} size={18} />
          </Pressable>
        </GlassView>
      ))}
    </View>
  );
}

function BadgeVariants() {
  const theme = useAppTheme();
  return (
    <DemoSurface
      title="Badge placement"
      description="Counts, dots and maximum values remain readable at native sizes."
    >
      <View style={styles.badgeRow}>
        {[
          ['Inbox', '8'],
          ['Updates', '99+'],
          ['Online', '•'],
        ].map(([label, value], index) => (
          <View key={label} style={styles.badgeItem}>
            <View
              style={[
                styles.badgeIcon,
                { backgroundColor: theme.colors.surfaceElevated },
              ]}
            >
              <Bell color={theme.colors.text} size={24} />
              <View
                style={[
                  styles.badgeBubble,
                  {
                    backgroundColor:
                      index === 2
                        ? theme.colors.positive
                        : theme.colors.negative,
                  },
                ]}
              >
                <Text style={styles.badgeText}>{value}</Text>
              </View>
            </View>
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              {label}
            </Text>
          </View>
        ))}
      </View>
    </DemoSurface>
  );
}

function CheckboxVariants() {
  const theme = useAppTheme();
  const [selected, setSelected] = useState(['Design']);
  const options = ['Design', 'Engineering', 'Research'];
  const all = selected.length === options.length;
  return (
    <DemoSurface title="Checkbox group">
      <SelectionRow
        label="Select all"
        state={all ? 'checked' : selected.length ? 'mixed' : 'unchecked'}
        onPress={() => setSelected(all ? [] : [...options])}
      />
      <View
        style={[styles.divider, { backgroundColor: theme.colors.border }]}
      />
      {options.map(option => (
        <SelectionRow
          key={option}
          label={option}
          state={selected.includes(option) ? 'checked' : 'unchecked'}
          onPress={() =>
            setSelected(current =>
              current.includes(option)
                ? current.filter(value => value !== option)
                : [...current, option],
            )
          }
        />
      ))}
      <SelectionRow
        disabled
        label="Unavailable option"
        state="unchecked"
        onPress={() => undefined}
      />
    </DemoSurface>
  );
}

function SelectionRow({
  label,
  state,
  onPress,
  disabled = false,
}: {
  label: string;
  state: 'checked' | 'mixed' | 'unchecked';
  onPress: () => void;
  disabled?: boolean;
}) {
  const theme = useAppTheme();
  const active = state !== 'unchecked';
  const selectionStyle = {
    backgroundColor: active ? theme.colors.text : 'transparent',
    borderColor: active ? theme.colors.text : theme.colors.border,
  };
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{
        checked: state === 'mixed' ? 'mixed' : active,
        disabled,
      }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.controlRow, disabled && styles.disabled]}
    >
      <View style={[styles.selectionBox, selectionStyle]}>
        {state === 'checked' ? (
          <Check color={theme.colors.canvas} size={15} strokeWidth={3} />
        ) : state === 'mixed' ? (
          <Minus color={theme.colors.canvas} size={15} strokeWidth={3} />
        ) : null}
      </View>
      <Text style={[theme.typography.body, { color: theme.colors.text }]}>
        {label}
      </Text>
    </Pressable>
  );
}

function ChipVariants() {
  const theme = useAppTheme();
  const [active, setActive] = useState('All');
  const [visible, setVisible] = useState(['Design', 'Engineering', 'Research']);
  const selectedChipStyle = {
    backgroundColor: theme.colors.text,
    borderColor: theme.colors.border,
  };
  const idleChipStyle = {
    backgroundColor: 'transparent',
    borderColor: theme.colors.border,
  };
  return (
    <DemoSurface title="Chip variants">
      <View style={styles.wrap}>
        {['All', 'Active', 'Archived'].map(label => (
          <Pressable
            key={label}
            accessibilityState={{ selected: active === label }}
            onPress={() => setActive(label)}
            style={[
              styles.chip,
              active === label ? selectedChipStyle : idleChipStyle,
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                {
                  color:
                    active === label ? theme.colors.canvas : theme.colors.text,
                },
              ]}
            >
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
      <View style={styles.wrap}>
        {visible.map(label => (
          <GlassView key={label} variant="control" style={styles.deletableChip}>
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              {label}
            </Text>
            <Pressable
              accessibilityLabel={`Remove ${label}`}
              hitSlop={8}
              onPress={() =>
                setVisible(current => current.filter(value => value !== label))
              }
            >
              <X color={theme.colors.textMuted} size={16} />
            </Pressable>
          </GlassView>
        ))}
      </View>
    </DemoSurface>
  );
}

function DialogVariants() {
  const theme = useAppTheme();
  const [kind, setKind] = useState<'confirm' | 'full' | null>(null);
  return (
    <DemoSurface title="Dialog variants">
      <DemoButton
        label="Open confirmation"
        onPress={() => setKind('confirm')}
      />
      <DemoButton
        label="Open full-screen dialog"
        onPress={() => setKind('full')}
        variant="secondary"
      />
      <Modal
        animationType={kind === 'full' ? 'slide' : 'fade'}
        onRequestClose={() => setKind(null)}
        presentationStyle={kind === 'full' ? 'fullScreen' : 'overFullScreen'}
        transparent={kind !== 'full'}
        visible={Boolean(kind)}
      >
        {kind === 'full' ? (
          <View
            style={[
              styles.fullDialog,
              { backgroundColor: theme.colors.canvas },
            ]}
          >
            <View style={styles.dialogHeader}>
              <Pressable
                accessibilityLabel="Close full-screen dialog"
                onPress={() => setKind(null)}
                style={styles.iconTarget}
              >
                <X color={theme.colors.text} size={24} />
              </Pressable>
              <Text
                style={[theme.typography.title, { color: theme.colors.text }]}
              >
                Create workspace
              </Text>
            </View>
            <DemoSurface
              title="Workspace details"
              description="A full-screen mobile task keeps focus and a predictable dismiss route."
            >
              <DemoButton
                label="Save workspace"
                onPress={() => setKind(null)}
              />
            </DemoSurface>
          </View>
        ) : (
          <View style={styles.modalScrim}>
            <GlassView
              accessibilityViewIsModal
              variant="floating"
              style={styles.dialogCard}
            >
              <Text
                style={[theme.typography.title, { color: theme.colors.text }]}
              >
                Delete local draft?
              </Text>
              <Text
                style={[
                  theme.typography.body,
                  { color: theme.colors.textMuted },
                ]}
              >
                This only removes the temporary demo state.
              </Text>
              <View style={styles.buttonRow}>
                <DemoButton
                  label="Cancel"
                  onPress={() => setKind(null)}
                  style={styles.flex}
                  variant="secondary"
                />
                <DemoButton
                  label="Delete"
                  onPress={() => setKind(null)}
                  style={styles.flex}
                  variant="danger"
                />
              </View>
            </GlassView>
          </View>
        )}
      </Modal>
    </DemoSurface>
  );
}

function LabelVariants() {
  const theme = useAppTheme();
  const labels = [
    { value: 'Active', color: theme.colors.positive },
    { value: 'Pending', color: theme.colors.warning },
    { value: 'Failed', color: theme.colors.negative },
    { value: 'Draft', color: theme.colors.textMuted },
  ];
  return (
    <DemoSurface title="Semantic labels">
      <View style={styles.wrap}>
        {labels.map(({ value, color }) => (
          <View
            key={value}
            style={[
              styles.label,
              { backgroundColor: `${color}22`, borderColor: `${color}66` },
            ]}
          >
            <View style={[styles.labelDot, { backgroundColor: color }]} />
            <Text style={[theme.typography.label, { color }]}>{value}</Text>
          </View>
        ))}
      </View>
      <View style={styles.wrap}>
        {labels.map(({ value, color }) => (
          <View
            key={`outline-${value}`}
            style={[styles.label, { borderColor: color }]}
          >
            <Text style={[theme.typography.label, { color }]}>{value}</Text>
          </View>
        ))}
      </View>
    </DemoSurface>
  );
}

function MenuVariants() {
  const theme = useAppTheme();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState('Rename');
  return (
    <DemoSurface title="Context menu">
      <DemoButton
        label={open ? 'Close menu' : 'Open menu'}
        onPress={() => setOpen(value => !value)}
        variant="secondary"
      />
      {open ? (
        <GlassView
          accessibilityRole="menu"
          variant="floating"
          style={styles.menu}
        >
          {['Rename', 'Duplicate', 'Archive'].map(label => (
            <Pressable
              accessibilityRole="menuitem"
              key={label}
              onPress={() => {
                setSelected(label);
                setOpen(false);
              }}
              style={styles.menuItem}
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
              {selected === label ? (
                <Check color={theme.colors.text} size={18} />
              ) : null}
            </Pressable>
          ))}
        </GlassView>
      ) : null}
      <Text
        accessibilityLiveRegion="polite"
        style={[styles.caption, { color: theme.colors.textMuted }]}
      >
        Selected action: {selected}
      </Text>
    </DemoSurface>
  );
}

function LanguageVariants() {
  const theme = useAppTheme();
  const [locale, setLocale] = useState<'EN' | 'RU' | 'UZ'>('EN');
  const copy = {
    EN: ['Welcome back', 'Continue to dashboard'],
    RU: ['С возвращением', 'Продолжить в панель'],
    UZ: ['Xush kelibsiz', 'Boshqaruvga o‘tish'],
  } as const;
  const selectedLocaleStyle = {
    backgroundColor: theme.colors.text,
    borderColor: theme.colors.border,
  };
  const idleLocaleStyle = {
    backgroundColor: 'transparent',
    borderColor: theme.colors.border,
  };
  return (
    <DemoSurface title="Live locale">
      <View style={styles.buttonRow}>
        {(['EN', 'RU', 'UZ'] as const).map(label => (
          <Pressable
            key={label}
            accessibilityRole="radio"
            accessibilityState={{ selected: locale === label }}
            onPress={() => setLocale(label)}
            style={[
              styles.localeButton,
              locale === label ? selectedLocaleStyle : idleLocaleStyle,
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                {
                  color:
                    locale === label ? theme.colors.canvas : theme.colors.text,
                },
              ]}
            >
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
      <GlassView variant="control" style={styles.copyPreview}>
        <Text style={[theme.typography.title, { color: theme.colors.text }]}>
          {copy[locale][0]}
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {copy[locale][1]}
        </Text>
      </GlassView>
    </DemoSurface>
  );
}

function PopoverVariants() {
  const theme = useAppTheme();
  const [open, setOpen] = useState(false);
  return (
    <DemoSurface title="Anchored popover">
      <View style={styles.popoverStage}>
        <Pressable
          accessibilityHint="Shows release information"
          accessibilityState={{ expanded: open }}
          onPress={() => setOpen(value => !value)}
          style={styles.iconTarget}
        >
          <MoreHorizontal color={theme.colors.text} size={24} />
        </Pressable>
        {open ? (
          <GlassView variant="floating" style={styles.popover}>
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              Release status
            </Text>
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              All native quality gates pass.
            </Text>
            <DemoButton
              label="View report"
              onPress={() => setOpen(false)}
              variant="secondary"
            />
          </GlassView>
        ) : null}
      </View>
    </DemoSurface>
  );
}

function ProgressVariants() {
  const theme = useAppTheme();
  return (
    <DemoSurface title="Progress variants">
      <View style={styles.progressRow}>
        <ActivityIndicator color={theme.colors.text} size="large" />
        <View style={styles.flex}>
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            Indeterminate
          </Text>
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
            Syncing components…
          </Text>
        </View>
      </View>
      {[28, 64, 100].map(value => (
        <View key={value} style={styles.progressBlock}>
          <View style={styles.progressLabel}>
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              {value === 100 ? 'Complete' : 'Uploading'}
            </Text>
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              {value}%
            </Text>
          </View>
          <View
            style={[
              styles.progressTrack,
              { backgroundColor: theme.colors.border },
            ]}
          >
            <View
              style={[
                styles.progressValue,
                { backgroundColor: theme.colors.text, width: `${value}%` },
              ]}
            />
          </View>
        </View>
      ))}
    </DemoSurface>
  );
}

function RadioVariants() {
  const theme = useAppTheme();
  const [plan, setPlan] = useState('Studio');
  return (
    <DemoSurface
      title="Radio group"
      description="Choose exactly one workspace plan."
    >
      {['Starter', 'Studio', 'Enterprise'].map((label, index) => (
        <Pressable
          accessibilityRole="radio"
          accessibilityState={{ selected: plan === label }}
          key={label}
          onPress={() => setPlan(label)}
          style={[
            styles.radioCard,
            {
              borderColor:
                plan === label ? theme.colors.text : theme.colors.border,
            },
          ]}
        >
          <View
            style={[
              styles.radioOuter,
              {
                borderColor:
                  plan === label ? theme.colors.text : theme.colors.border,
              },
            ]}
          >
            {plan === label ? (
              <View
                style={[
                  styles.radioInner,
                  { backgroundColor: theme.colors.text },
                ]}
              />
            ) : null}
          </View>
          <View style={styles.flex}>
            <Text style={[theme.typography.body, { color: theme.colors.text }]}>
              {label}
            </Text>
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              {
                [
                  'For personal prototypes',
                  'For product teams',
                  'For organizations',
                ][index]
              }
            </Text>
          </View>
        </Pressable>
      ))}
    </DemoSurface>
  );
}

function SnackbarVariants() {
  const theme = useAppTheme();
  const [message, setMessage] = useState<string | null>(null);
  return (
    <DemoSurface title="Snackbar feedback">
      <DemoButton
        label="Save changes"
        onPress={() => setMessage('Changes saved')}
      />
      {message ? (
        <GlassView
          accessibilityLiveRegion="polite"
          accessibilityRole="alert"
          variant="floating"
          style={styles.snackbar}
        >
          <CheckCircle2 color={theme.colors.positive} size={20} />
          <Text
            style={[
              theme.typography.body,
              styles.flex,
              { color: theme.colors.text },
            ]}
          >
            {message}
          </Text>
          <Pressable
            accessibilityLabel="Undo save"
            onPress={() => setMessage('Save undone')}
            style={styles.snackbarAction}
          >
            <Text
              style={[theme.typography.label, { color: theme.colors.text }]}
            >
              UNDO
            </Text>
          </Pressable>
          <Pressable
            accessibilityLabel="Dismiss message"
            onPress={() => setMessage(null)}
            style={styles.iconTarget}
          >
            <X color={theme.colors.textMuted} size={18} />
          </Pressable>
        </GlassView>
      ) : null}
    </DemoSurface>
  );
}

function SwitchVariants() {
  const theme = useAppTheme();
  const [states, setStates] = useState({ notifications: true, updates: false });
  return (
    <DemoSurface title="Switch preferences">
      <SwitchRow
        label="Notifications"
        description="Important activity and mentions"
        value={states.notifications}
        onValueChange={value =>
          setStates(current => ({ ...current, notifications: value }))
        }
      />
      <SwitchRow
        label="Product updates"
        description="New components and templates"
        value={states.updates}
        onValueChange={value =>
          setStates(current => ({ ...current, updates: value }))
        }
      />
      <View style={[styles.controlRow, styles.disabled]}>
        <View style={styles.flex}>
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            Managed by organization
          </Text>
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
            This preference cannot be changed
          </Text>
        </View>
        <Switch
          disabled
          trackColor={{ false: theme.colors.border, true: theme.colors.text }}
          value
        />
      </View>
    </DemoSurface>
  );
}

function SwitchRow({
  label,
  description,
  value,
  onValueChange,
}: {
  label: string;
  description: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
}) {
  const theme = useAppTheme();
  return (
    <View style={styles.controlRow}>
      <View style={styles.flex}>
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          {label}
        </Text>
        <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
          {description}
        </Text>
      </View>
      <Switch
        accessibilityLabel={label}
        onValueChange={onValueChange}
        trackColor={{ false: theme.colors.border, true: theme.colors.text }}
        value={value}
      />
    </View>
  );
}

function TabsVariants() {
  const theme = useAppTheme();
  const [tab, setTab] = useState('Overview');
  return (
    <DemoSurface title="Tabs">
      <View accessibilityRole="tablist" style={styles.tabRow}>
        {['Overview', 'Activity', 'Team'].map(label => (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected: tab === label }}
            key={label}
            onPress={() => setTab(label)}
            style={[
              styles.tab,
              tab === label && { borderBottomColor: theme.colors.text },
            ]}
          >
            <Text
              style={[
                theme.typography.label,
                {
                  color:
                    tab === label ? theme.colors.text : theme.colors.textMuted,
                },
              ]}
            >
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
      <GlassView variant="control" style={styles.tabPanel}>
        <Text style={[theme.typography.title, { color: theme.colors.text }]}>
          {tab}
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {tab === 'Overview'
            ? 'Workspace health, progress and current status.'
            : tab === 'Activity'
            ? 'Recent changes from every project member.'
            : 'People, roles and collaboration settings.'}
        </Text>
      </GlassView>
    </DemoSurface>
  );
}

function TooltipVariants() {
  const theme = useAppTheme();
  const [visible, setVisible] = useState(false);
  return (
    <DemoSurface
      title="Tap tooltip"
      description="Touch interfaces reveal hints on press, not hover."
    >
      <View style={styles.tooltipStage}>
        {visible ? (
          <GlassView
            accessibilityRole="text"
            variant="floating"
            style={styles.tooltip}
          >
            <Text style={[styles.caption, { color: theme.colors.text }]}>
              More project actions
            </Text>
          </GlassView>
        ) : null}
        <Pressable
          accessibilityHint="Shows more project actions"
          accessibilityLabel="More actions"
          onPress={() => setVisible(value => !value)}
          style={[styles.tooltipButton, { borderColor: theme.colors.border }]}
        >
          <MoreHorizontal color={theme.colors.text} size={24} />
        </Pressable>
      </View>
    </DemoSurface>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  stack: { gap: 10 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  caption: { fontSize: 13, lineHeight: 18 },
  disabled: { opacity: 0.45 },
  iconTarget: {
    alignItems: 'center',
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  alert: {
    alignItems: 'flex-start',
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 10,
    padding: 14,
  },
  badgeRow: { flexDirection: 'row', justifyContent: 'space-around' },
  badgeItem: { alignItems: 'center', gap: 8 },
  badgeIcon: {
    alignItems: 'center',
    borderRadius: 20,
    height: 52,
    justifyContent: 'center',
    width: 52,
  },
  badgeBubble: {
    alignItems: 'center',
    borderRadius: 10,
    justifyContent: 'center',
    minHeight: 19,
    minWidth: 19,
    paddingHorizontal: 4,
    position: 'absolute',
    right: -5,
    top: -5,
  },
  badgeText: { color: '#FFFFFF', fontSize: 10, fontWeight: '700' },
  controlRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    minHeight: 56,
  },
  selectionBox: {
    alignItems: 'center',
    borderRadius: 7,
    borderWidth: 1,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  divider: { height: StyleSheet.hairlineWidth },
  chip: {
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 38,
    paddingHorizontal: 14,
    justifyContent: 'center',
  },
  deletableChip: {
    alignItems: 'center',
    borderRadius: 18,
    flexDirection: 'row',
    gap: 7,
    minHeight: 38,
    paddingHorizontal: 12,
  },
  fullDialog: { flex: 1, gap: 24, padding: 20, paddingTop: 64 },
  dialogHeader: { alignItems: 'center', flexDirection: 'row', gap: 10 },
  modalScrim: {
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.58)',
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  dialogCard: { borderRadius: 28, gap: 14, padding: 20, width: '100%' },
  buttonRow: { flexDirection: 'row', gap: 8 },
  label: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 11,
    paddingVertical: 6,
  },
  labelDot: { borderRadius: 4, height: 7, width: 7 },
  menu: { alignSelf: 'flex-end', borderRadius: 22, minWidth: 210, padding: 8 },
  menuItem: {
    alignItems: 'center',
    flexDirection: 'row',
    minHeight: 48,
    paddingHorizontal: 10,
  },
  localeButton: {
    alignItems: 'center',
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    flex: 1,
    justifyContent: 'center',
    minHeight: 44,
  },
  copyPreview: { borderRadius: 20, gap: 5, minHeight: 120, padding: 18 },
  popoverStage: { alignItems: 'flex-end', minHeight: 210 },
  popover: {
    borderRadius: 22,
    gap: 10,
    padding: 14,
    position: 'absolute',
    right: 0,
    top: 48,
    width: 250,
  },
  progressRow: { alignItems: 'center', flexDirection: 'row', gap: 14 },
  progressBlock: { gap: 7 },
  progressLabel: { flexDirection: 'row', justifyContent: 'space-between' },
  progressTrack: { borderRadius: 4, height: 8, overflow: 'hidden' },
  progressValue: { borderRadius: 4, height: 8 },
  radioCard: {
    alignItems: 'center',
    borderRadius: 20,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    minHeight: 70,
    padding: 14,
  },
  radioOuter: {
    alignItems: 'center',
    borderRadius: 12,
    borderWidth: 1,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  radioInner: { borderRadius: 6, height: 12, width: 12 },
  snackbar: {
    alignItems: 'center',
    borderRadius: 20,
    flexDirection: 'row',
    gap: 8,
    minHeight: 60,
    paddingLeft: 14,
  },
  snackbarAction: {
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 8,
  },
  tabRow: { borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: 'row' },
  tab: {
    alignItems: 'center',
    borderBottomWidth: 2,
    flex: 1,
    minHeight: 48,
    justifyContent: 'center',
  },
  tabPanel: { borderRadius: 20, gap: 6, minHeight: 130, padding: 18 },
  tooltipStage: {
    alignItems: 'center',
    minHeight: 150,
    justifyContent: 'flex-end',
  },
  tooltip: {
    borderRadius: 14,
    bottom: 58,
    paddingHorizontal: 12,
    paddingVertical: 8,
    position: 'absolute',
  },
  tooltipButton: {
    alignItems: 'center',
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
});
