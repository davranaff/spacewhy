import { useMemo, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  FilePlus2,
  Folder,
  LockKeyhole,
  Mail,
  MoreHorizontal,
  Paperclip,
  Search,
  Send,
  ShieldCheck,
  UserRound,
} from 'lucide-react-native';

import { DemoButton, DemoSurface } from '@/features/catalog';
import type { DashboardTemplate } from '@/features/templates';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui';

type Props = Readonly<{ template: DashboardTemplate }>;

const entityRows: Readonly<Record<string, readonly string[]>> = {
  User: ['Maya Chen', 'Noah Williams', 'Zara Khan', 'Leo Martin'],
  Product: [
    'Orbital console',
    'Glass controls',
    'Mobile kit',
    'Data workspace',
  ],
  Order: ['#SW-1048', '#SW-1047', '#SW-1046', '#SW-1045'],
  Invoice: ['INV-2048', 'INV-2047', 'INV-2046', 'INV-2045'],
  Blog: [
    'Designing native glass',
    'A faster dashboard',
    'Mobile UI systems',
    'Release notes',
  ],
  Job: [
    'Senior iOS engineer',
    'Product designer',
    'Platform lead',
    'QA engineer',
  ],
  Tour: [
    'Lunar observatory',
    'Samarkand night',
    'Alpine research',
    'Desert signals',
  ],
};

const formFields: Readonly<Record<string, readonly string[]>> = {
  User: ['Full name', 'Email address', 'Role'],
  Product: ['Product name', 'Description', 'Price'],
  Invoice: ['Customer', 'Invoice number', 'Payment terms'],
  Blog: ['Post title', 'Summary', 'Content'],
  Job: ['Job title', 'Location', 'Compensation'],
  Tour: ['Tour title', 'Destination', 'Price'],
};

export function DashboardTemplatePreview({ template }: Props) {
  switch (template.kind) {
    case 'overview':
      return <OverviewTemplate template={template} />;
    case 'profile':
      return <ProfileTemplate />;
    case 'cards':
      return <CardsTemplate />;
    case 'list':
      return <ListTemplate template={template} />;
    case 'detail':
      return <DetailTemplate template={template} />;
    case 'form':
      return <FormTemplate template={template} />;
    case 'account':
      return <AccountTemplate />;
    case 'file-manager':
      return <FileManagerTemplate />;
    case 'mail':
      return <MailTemplate />;
    case 'chat':
      return <ChatTemplate />;
    case 'calendar':
      return <CalendarTemplate />;
    case 'kanban':
      return <KanbanTemplate />;
    case 'permission':
      return <PermissionTemplate />;
    case 'blank':
      return <BlankTemplate />;
  }
}

function OverviewTemplate({ template }: Props) {
  const theme = useAppTheme();
  const [range, setRange] = useState<'Week' | 'Month'>('Week');
  const metrics = useMemo(() => getOverviewMetrics(template.id), [template.id]);
  const values =
    range === 'Week'
      ? [24, 44, 38, 68, 56, 82, 72]
      : [35, 58, 43, 76, 61, 88, 92];

  return (
    <View style={styles.stack}>
      <View style={styles.metricGrid}>
        {metrics.map((metric, index) => (
          <GlassView
            key={metric.label}
            variant="surface"
            style={styles.metricCard}
          >
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
              {metric.label}
            </Text>
            <Text
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              {metric.value}
            </Text>
            <View style={styles.inline}>
              {index === 2 ? (
                <ArrowDownRight color={theme.colors.negative} size={15} />
              ) : (
                <ArrowUpRight color={theme.colors.positive} size={15} />
              )}
              <Text
                style={[
                  styles.caption,
                  {
                    color:
                      index === 2
                        ? theme.colors.negative
                        : theme.colors.positive,
                  },
                ]}
              >
                {index === 2 ? '-1.2%' : `+${index + 2}.4%`}
              </Text>
            </View>
          </GlassView>
        ))}
      </View>

      <DemoSurface
        title={`${template.family} performance`}
        description="Live native layout with touch-selectable range."
      >
        <View style={styles.segmentRow}>
          {(['Week', 'Month'] as const).map(option => (
            <Segment
              key={option}
              label={option}
              selected={range === option}
              onPress={() => setRange(option)}
            />
          ))}
        </View>
        <View
          accessibilityLabel={`${template.family} activity chart`}
          style={styles.barChart}
        >
          {values.map((height, index) => (
            <View key={index} style={styles.barColumn}>
              <View
                style={[
                  styles.bar,
                  { backgroundColor: theme.colors.text, height: `${height}%` },
                ]}
              />
            </View>
          ))}
        </View>
      </DemoSurface>

      <DemoSurface title="Recent activity">
        {[
          'Interface review completed',
          'Workspace member invited',
          'Report exported',
        ].map((label, index) => (
          <TemplateRow
            key={label}
            label={label}
            meta={`${index + 1}${index ? 'h' : 'm'} ago`}
          />
        ))}
      </DemoSurface>
    </View>
  );
}

function getOverviewMetrics(id: DashboardTemplate['id']) {
  if (id === 'banking-overview')
    return [
      { label: 'Balance', value: '$48.2K' },
      { label: 'Income', value: '$12.8K' },
      { label: 'Expense', value: '$7.4K' },
    ];
  if (id === 'booking-overview')
    return [
      { label: 'Bookings', value: '186' },
      { label: 'Occupancy', value: '78%' },
      { label: 'Cancelled', value: '12' },
    ];
  if (id === 'ecommerce-overview')
    return [
      { label: 'Sales', value: '$18.7K' },
      { label: 'Orders', value: '876' },
      { label: 'Returns', value: '24' },
    ];
  if (id === 'analytics-overview')
    return [
      { label: 'Users', value: '18.7K' },
      { label: 'Sessions', value: '24.8K' },
      { label: 'Bounce', value: '31%' },
    ];
  if (id === 'file-overview')
    return [
      { label: 'Used', value: '68 GB' },
      { label: 'Files', value: '4.8K' },
      { label: 'Shared', value: '126' },
    ];
  return [
    { label: 'Active users', value: '18.7K' },
    { label: 'Installed', value: '4.8K' },
    { label: 'Downloads', value: '678' },
  ];
}

function ProfileTemplate() {
  const theme = useAppTheme();
  return (
    <View style={styles.stack}>
      <GlassView variant="surface" style={styles.profileHero}>
        <View style={[styles.avatar, { backgroundColor: theme.colors.text }]}>
          <Text
            style={[theme.typography.title, { color: theme.colors.canvas }]}
          >
            MC
          </Text>
        </View>
        <Text style={[theme.typography.title, { color: theme.colors.text }]}>
          Maya Chen
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          Product design lead · Spacewhy
        </Text>
        <View style={styles.profileStats}>
          <SmallStat label="Projects" value="24" />
          <SmallStat label="Followers" value="8.6K" />
          <SmallStat label="Following" value="438" />
        </View>
      </GlassView>
      <DemoSurface title="About">
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          Building clear tools for teams that work with complex systems.
        </Text>
      </DemoSurface>
      <DemoSurface title="Activity">
        {[
          'Published a component set',
          'Reviewed Orbital analytics',
          'Joined Mobile QA',
        ].map((label, index) => (
          <TemplateRow key={label} label={label} meta={`${index + 1}d`} />
        ))}
      </DemoSurface>
    </View>
  );
}

function CardsTemplate() {
  const theme = useAppTheme();
  return (
    <View style={styles.stack}>
      {['Maya Chen', 'Noah Williams', 'Zara Khan', 'Leo Martin'].map(
        (name, index) => (
          <GlassView
            key={name}
            interactive
            variant="surface"
            style={styles.personCard}
          >
            <View
              style={[
                styles.avatarSmall,
                { backgroundColor: theme.colors.surfaceElevated },
              ]}
            >
              <UserRound color={theme.colors.text} size={22} />
            </View>
            <View style={styles.flex}>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {name}
              </Text>
              <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
                {
                  [
                    'Product designer',
                    'iOS engineer',
                    'Operations lead',
                    'Researcher',
                  ][index]
                }
              </Text>
            </View>
            <Pressable
              accessibilityLabel={`More actions for ${name}`}
              style={styles.iconTarget}
            >
              <MoreHorizontal color={theme.colors.textMuted} size={20} />
            </Pressable>
          </GlassView>
        ),
      )}
    </View>
  );
}

function ListTemplate({ template }: Props) {
  const theme = useAppTheme();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const rows = entityRows[template.family] ?? entityRows.Product;
  const filtered = rows.filter(row =>
    row.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );

  return (
    <DemoSurface
      title={`${template.family} records`}
      description={`${filtered.length} visible records`}
    >
      <GlassView variant="control" style={styles.searchBox}>
        <Search color={theme.colors.textMuted} size={19} />
        <TextInput
          accessibilityLabel={`Search ${template.family}`}
          onChangeText={setQuery}
          placeholder={`Search ${template.family.toLocaleLowerCase()}`}
          placeholderTextColor={theme.colors.textMuted}
          style={[
            theme.typography.body,
            styles.searchInput,
            { color: theme.colors.text },
          ]}
          value={query}
        />
      </GlassView>
      {filtered.map((row, index) => {
        const active = selected === row;
        const checkboxStyle = {
          borderColor: active ? theme.colors.text : theme.colors.border,
          backgroundColor: active ? theme.colors.text : 'transparent',
        };
        return (
          <Pressable
            key={row}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: active }}
            onPress={() => setSelected(active ? null : row)}
            style={[styles.dataRow, { borderColor: theme.colors.border }]}
          >
            <View style={[styles.checkBox, checkboxStyle]}>
              {active ? <Check color={theme.colors.canvas} size={14} /> : null}
            </View>
            <View style={styles.flex}>
              <Text
                numberOfLines={1}
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {row}
              </Text>
              <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
                Updated {index ? `${index + 1} days ago` : 'today'}
              </Text>
            </View>
            <StatusPill
              label={index === 2 ? 'Draft' : index === 1 ? 'Review' : 'Active'}
            />
          </Pressable>
        );
      })}
      {!filtered.length ? (
        <Text
          style={[
            theme.typography.body,
            styles.center,
            { color: theme.colors.textMuted },
          ]}
        >
          No matching records
        </Text>
      ) : null}
    </DemoSurface>
  );
}

function DetailTemplate({ template }: Props) {
  const theme = useAppTheme();
  const title = (entityRows[template.family] ?? ['Spacewhy record'])[0];
  return (
    <View style={styles.stack}>
      <GlassView variant="surface" style={styles.detailHero}>
        <StatusPill label="Active" />
        <Text
          style={[
            theme.typography.display,
            styles.detailTitle,
            { color: theme.colors.text },
          ]}
        >
          {title}
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {template.description}
        </Text>
      </GlassView>
      <DemoSurface title="Summary">
        <KeyValue label="Owner" value="Maya Chen" />
        <KeyValue label="Created" value="Aug 12, 2026" />
        <KeyValue label="Status" value="Active" />
        <KeyValue label="Progress" value="84%" last />
      </DemoSurface>
      <View style={styles.actionRow}>
        <DemoButton
          label="Edit"
          onPress={() => undefined}
          style={styles.flex}
        />
        <DemoButton
          label="More"
          onPress={() => undefined}
          style={styles.flex}
          variant="secondary"
        />
      </View>
    </View>
  );
}

function FormTemplate({ template }: Props) {
  const theme = useAppTheme();
  const fields = formFields[template.family] ?? [
    'Title',
    'Description',
    'Status',
  ];
  const [values, setValues] = useState(() =>
    Object.fromEntries(
      fields.map(field => [
        field,
        template.title.includes('Edit') ? `${template.family} sample` : '',
      ]),
    ),
  );
  const [enabled, setEnabled] = useState(true);
  const [saved, setSaved] = useState(false);

  return (
    <DemoSurface
      title={template.title}
      description="Local native form with labels, validation and save feedback."
    >
      {fields.map((field, index) => (
        <View key={field} style={styles.fieldGroup}>
          <Text style={[theme.typography.label, { color: theme.colors.text }]}>
            {field}
          </Text>
          <GlassView
            variant="control"
            style={[styles.fieldGlass, index === 1 && styles.multilineField]}
          >
            <TextInput
              accessibilityLabel={field}
              multiline={index === 1}
              onChangeText={value => {
                setValues(current => ({ ...current, [field]: value }));
                setSaved(false);
              }}
              placeholder={`Enter ${field.toLocaleLowerCase()}`}
              placeholderTextColor={theme.colors.textMuted}
              style={[
                theme.typography.body,
                styles.fieldInput,
                { color: theme.colors.text },
              ]}
              value={values[field]}
            />
          </GlassView>
        </View>
      ))}
      <View style={styles.preferenceRow}>
        <View style={styles.flex}>
          <Text style={[theme.typography.body, { color: theme.colors.text }]}>
            Published
          </Text>
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
            Visible in the local demo
          </Text>
        </View>
        <Switch
          accessibilityLabel="Published"
          onValueChange={setEnabled}
          trackColor={{ false: theme.colors.border, true: theme.colors.text }}
          value={enabled}
        />
      </View>
      <DemoButton
        label={saved ? 'Saved locally' : 'Save changes'}
        onPress={() => setSaved(true)}
      />
      {saved ? (
        <View accessibilityLiveRegion="polite" style={styles.successRow}>
          <Check color={theme.colors.positive} size={18} />
          <Text style={[styles.caption, { color: theme.colors.positive }]}>
            Changes saved in this demo session
          </Text>
        </View>
      ) : null}
    </DemoSurface>
  );
}

function AccountTemplate() {
  const [tab, setTab] = useState('General');
  const [notifications, setNotifications] = useState(true);
  const [security, setSecurity] = useState(true);
  return (
    <View style={styles.stack}>
      <View style={styles.segmentRow}>
        {['General', 'Billing', 'Security'].map(label => (
          <Segment
            key={label}
            label={label}
            selected={tab === label}
            onPress={() => setTab(label)}
          />
        ))}
      </View>
      <DemoSurface title={`${tab} settings`}>
        <Preference
          label="Product notifications"
          value={notifications}
          onValueChange={setNotifications}
        />
        <Preference
          label="Two-factor security"
          value={security}
          onValueChange={setSecurity}
        />
        <TemplateRow label="Email" meta="demo@spacewhy.uz" />
        <TemplateRow label="Plan" meta="Studio" />
      </DemoSurface>
      <DemoButton label="Save account settings" onPress={() => undefined} />
    </View>
  );
}

function FileManagerTemplate() {
  const theme = useAppTheme();
  const [uploaded, setUploaded] = useState(false);
  return (
    <View style={styles.stack}>
      <View style={styles.metricGrid}>
        <SmallGlassStat label="Used" value="68 GB" />
        <SmallGlassStat label="Files" value="4,876" />
        <SmallGlassStat label="Shared" value="126" />
      </View>
      <DemoSurface title="Folders">
        <View style={styles.folderGrid}>
          {['Design', 'Documents', 'Media', 'Archive'].map(label => (
            <Pressable
              key={label}
              style={[styles.folderCard, { borderColor: theme.colors.border }]}
            >
              <Folder color={theme.colors.text} size={26} />
              <Text
                style={[theme.typography.label, { color: theme.colors.text }]}
              >
                {label}
              </Text>
            </Pressable>
          ))}
        </View>
      </DemoSurface>
      <DemoSurface title="Recent files">
        {['spacewhy-system.fig', 'launch-notes.pdf', 'mobile-preview.mov'].map(
          (label, index) => (
            <TemplateRow
              key={label}
              label={label}
              meta={`${index + 1}.${index + 2} MB`}
            />
          ),
        )}
      </DemoSurface>
      <DemoButton
        label={uploaded ? 'Upload ready' : 'Choose a local file'}
        onPress={() => setUploaded(true)}
      />
    </View>
  );
}

function MailTemplate() {
  const theme = useAppTheme();
  const messages = [
    'Design review is ready',
    'Weekly system digest',
    'Dashboard handoff',
  ];
  const [selected, setSelected] = useState(0);
  return (
    <View style={styles.stack}>
      <DemoButton label="Compose" onPress={() => undefined} />
      <DemoSurface title="Inbox" description="32 unread messages">
        {messages.map((subject, index) => (
          <Pressable
            key={subject}
            accessibilityState={{ selected: selected === index }}
            onPress={() => setSelected(index)}
            style={[styles.dataRow, { borderColor: theme.colors.border }]}
          >
            <Mail color={theme.colors.text} size={20} />
            <View style={styles.flex}>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {subject}
              </Text>
              <Text
                numberOfLines={1}
                style={[styles.caption, { color: theme.colors.textMuted }]}
              >
                Maya Chen · {index ? 'Yesterday' : '09:42'}
              </Text>
            </View>
            <ChevronRight color={theme.colors.textMuted} size={18} />
          </Pressable>
        ))}
      </DemoSurface>
      <DemoSurface
        title={messages[selected]}
        description="A native reading pane appears below the inbox on compact screens."
      >
        <Text style={[theme.typography.body, { color: theme.colors.text }]}>
          The complete Spacewhy mobile UI kit is ready for another review pass.
          Every action here is local and safe to explore.
        </Text>
      </DemoSurface>
    </View>
  );
}

function ChatTemplate() {
  const theme = useAppTheme();
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState([
    'The web dashboard inventory is mapped.',
    'Great — port the native templates next.',
  ]);
  const send = () => {
    if (!draft.trim()) return;
    setMessages(current => [...current, draft.trim()]);
    setDraft('');
  };
  return (
    <DemoSurface title="Maya Chen" description="Active now">
      <View style={styles.chatBody}>
        {messages.map((message, index) => (
          <View
            key={`${message}-${index}`}
            style={[
              styles.bubble,
              index % 2 ? styles.ownBubble : styles.otherBubble,
              {
                backgroundColor:
                  index % 2 ? theme.colors.text : theme.colors.surfaceElevated,
              },
            ]}
          >
            <Text
              style={[
                theme.typography.body,
                { color: index % 2 ? theme.colors.canvas : theme.colors.text },
              ]}
            >
              {message}
            </Text>
          </View>
        ))}
      </View>
      <GlassView variant="control" style={styles.composer}>
        <Pressable accessibilityLabel="Attach file" style={styles.iconTarget}>
          <Paperclip color={theme.colors.textMuted} size={19} />
        </Pressable>
        <TextInput
          accessibilityLabel="Message"
          onChangeText={setDraft}
          onSubmitEditing={send}
          placeholder="Message"
          placeholderTextColor={theme.colors.textMuted}
          returnKeyType="send"
          style={[
            theme.typography.body,
            styles.composerInput,
            { color: theme.colors.text },
          ]}
          value={draft}
        />
        <Pressable
          accessibilityLabel="Send message"
          onPress={send}
          style={styles.iconTarget}
        >
          <Send color={theme.colors.text} size={19} />
        </Pressable>
      </GlassView>
    </DemoSurface>
  );
}

function CalendarTemplate() {
  const theme = useAppTheme();
  const [day, setDay] = useState(16);
  return (
    <View style={styles.stack}>
      <DemoSurface
        title="August 2026"
        description="Select a day to update the agenda."
      >
        <View style={styles.calendarGrid}>
          {Array.from({ length: 28 }, (_, index) => index + 1).map(value => (
            <Pressable
              key={value}
              accessibilityLabel={`August ${value}`}
              accessibilityState={{ selected: day === value }}
              onPress={() => setDay(value)}
              style={[
                styles.day,
                day === value && { backgroundColor: theme.colors.text },
              ]}
            >
              <Text
                style={[
                  styles.caption,
                  {
                    color:
                      day === value ? theme.colors.canvas : theme.colors.text,
                  },
                ]}
              >
                {value}
              </Text>
            </Pressable>
          ))}
        </View>
      </DemoSurface>
      <DemoSurface title={`Agenda · Aug ${day}`}>
        <TemplateRow label="Product review" meta="09:30" />
        <TemplateRow label="Mobile QA" meta="11:00" />
        <TemplateRow label="Architecture sync" meta="14:30" />
      </DemoSurface>
    </View>
  );
}

function KanbanTemplate() {
  const theme = useAppTheme();
  const [stage, setStage] = useState(0);
  const columns = ['Backlog', 'In progress', 'Review'];
  return (
    <View style={styles.stack}>
      <View style={styles.segmentRow}>
        {columns.map((label, index) => (
          <Segment
            key={label}
            label={label}
            selected={stage === index}
            onPress={() => setStage(index)}
          />
        ))}
      </View>
      <DemoSurface title={columns[stage]} description={`${stage + 2} cards`}>
        {[
          'Port invoice template',
          'Verify native glass',
          'Audit component states',
        ]
          .slice(0, stage + 2)
          .map((label, index) => (
            <GlassView key={label} variant="control" style={styles.taskCard}>
              <Text
                style={[theme.typography.body, { color: theme.colors.text }]}
              >
                {label}
              </Text>
              <View style={styles.inline}>
                <StatusPill label={index === 1 ? 'High' : 'Normal'} />
                <Text
                  style={[styles.caption, { color: theme.colors.textMuted }]}
                >
                  SW-{1048 - index}
                </Text>
              </View>
            </GlassView>
          ))}
        <DemoButton
          disabled={stage === 2}
          label={
            stage === 2
              ? 'Ready for release'
              : `Move first card to ${columns[stage + 1]}`
          }
          onPress={() => setStage(current => Math.min(2, current + 1))}
          variant="secondary"
        />
      </DemoSurface>
    </View>
  );
}

function PermissionTemplate() {
  const theme = useAppTheme();
  const [admin, setAdmin] = useState(false);
  return (
    <View style={styles.stack}>
      <DemoSurface
        title="Role preview"
        description="Switch roles to verify protected content behavior."
      >
        <Preference
          label="Administrator role"
          value={admin}
          onValueChange={setAdmin}
        />
      </DemoSurface>
      <GlassView variant="surface" style={styles.permissionCard}>
        {admin ? (
          <ShieldCheck color={theme.colors.positive} size={34} />
        ) : (
          <LockKeyhole color={theme.colors.textMuted} size={34} />
        )}
        <Text style={[theme.typography.title, { color: theme.colors.text }]}>
          {admin ? 'Access granted' : 'Administrator access required'}
        </Text>
        <Text
          style={[
            theme.typography.body,
            styles.center,
            { color: theme.colors.textMuted },
          ]}
        >
          {admin
            ? 'Protected analytics and management actions are visible.'
            : 'This content stays hidden for standard members.'}
        </Text>
      </GlassView>
    </View>
  );
}

function BlankTemplate() {
  const theme = useAppTheme();
  return (
    <GlassView variant="surface" style={styles.blankCard}>
      <FilePlus2 color={theme.colors.text} size={42} />
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        Start with a clean canvas
      </Text>
      <Text
        style={[
          theme.typography.body,
          styles.center,
          { color: theme.colors.textMuted },
        ]}
      >
        The authenticated shell, safe areas, theme and dock remain ready while
        product content stays intentionally empty.
      </Text>
      <DemoButton label="Add first section" onPress={() => undefined} />
    </GlassView>
  );
}

function Segment({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  const theme = useAppTheme();
  const segmentStyle = {
    backgroundColor: selected ? theme.colors.text : 'transparent',
    borderColor: theme.colors.border,
  };
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.segment, segmentStyle]}
    >
      <Text
        numberOfLines={1}
        style={[
          theme.typography.label,
          { color: selected ? theme.colors.canvas : theme.colors.text },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

function TemplateRow({ label, meta }: { label: string; meta: string }) {
  const theme = useAppTheme();
  return (
    <View style={[styles.templateRow, { borderColor: theme.colors.border }]}>
      <View style={styles.flex}>
        <Text
          numberOfLines={1}
          style={[theme.typography.body, { color: theme.colors.text }]}
        >
          {label}
        </Text>
        <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
          {meta}
        </Text>
      </View>
      <ChevronRight color={theme.colors.textMuted} size={18} />
    </View>
  );
}

function SmallStat({ label, value }: { label: string; value: string }) {
  const theme = useAppTheme();
  return (
    <View style={styles.smallStat}>
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
    </View>
  );
}

function SmallGlassStat({ label, value }: { label: string; value: string }) {
  const theme = useAppTheme();
  return (
    <GlassView variant="surface" style={styles.metricCard}>
      <Text style={[theme.typography.title, { color: theme.colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
    </GlassView>
  );
}

function StatusPill({ label }: { label: string }) {
  const theme = useAppTheme();
  return (
    <View
      style={[
        styles.status,
        {
          borderColor: theme.colors.border,
          backgroundColor: theme.colors.surfaceElevated,
        },
      ]}
    >
      <Text style={[styles.statusText, { color: theme.colors.text }]}>
        {label}
      </Text>
    </View>
  );
}

function KeyValue({
  label,
  value,
  last = false,
}: {
  label: string;
  value: string;
  last?: boolean;
}) {
  const theme = useAppTheme();
  return (
    <View
      style={[
        styles.keyValue,
        !last && {
          borderBottomColor: theme.colors.border,
          borderBottomWidth: StyleSheet.hairlineWidth,
        },
      ]}
    >
      <Text style={[theme.typography.body, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
      <Text style={[theme.typography.body, { color: theme.colors.text }]}>
        {value}
      </Text>
    </View>
  );
}

function Preference({
  label,
  value,
  onValueChange,
}: {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
}) {
  const theme = useAppTheme();
  return (
    <View style={styles.preferenceRow}>
      <Text
        style={[
          theme.typography.body,
          styles.flex,
          { color: theme.colors.text },
        ]}
      >
        {label}
      </Text>
      <Switch
        accessibilityLabel={label}
        onValueChange={onValueChange}
        trackColor={{ false: theme.colors.border, true: theme.colors.text }}
        value={value}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  stack: { gap: 14 },
  flex: { flex: 1 },
  inline: { alignItems: 'center', flexDirection: 'row', gap: 4 },
  center: { textAlign: 'center' },
  caption: { fontSize: 13, lineHeight: 18 },
  metricGrid: { flexDirection: 'row', gap: 8 },
  metricCard: {
    borderRadius: 20,
    flex: 1,
    gap: 3,
    minHeight: 104,
    padding: 13,
  },
  segmentRow: { flexDirection: 'row', gap: 8 },
  segment: {
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    flex: 1,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 8,
  },
  barChart: {
    alignItems: 'flex-end',
    flexDirection: 'row',
    gap: 8,
    height: 160,
    paddingTop: 12,
  },
  barColumn: { flex: 1, height: '100%', justifyContent: 'flex-end' },
  bar: { borderRadius: 8, minHeight: 12, opacity: 0.86, width: '100%' },
  templateRow: {
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    minHeight: 58,
    paddingVertical: 8,
  },
  profileHero: { alignItems: 'center', borderRadius: 28, gap: 8, padding: 22 },
  avatar: {
    alignItems: 'center',
    borderRadius: 38,
    height: 76,
    justifyContent: 'center',
    width: 76,
  },
  profileStats: { flexDirection: 'row', marginTop: 10, width: '100%' },
  smallStat: { alignItems: 'center', flex: 1, gap: 2 },
  personCard: {
    alignItems: 'center',
    borderRadius: 22,
    flexDirection: 'row',
    gap: 12,
    minHeight: 78,
    padding: 14,
  },
  avatarSmall: {
    alignItems: 'center',
    borderRadius: 20,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  iconTarget: {
    alignItems: 'center',
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  searchBox: {
    alignItems: 'center',
    borderRadius: 18,
    flexDirection: 'row',
    minHeight: 52,
    paddingHorizontal: 14,
  },
  searchInput: { flex: 1, minHeight: 52, paddingHorizontal: 10 },
  dataRow: {
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 10,
    minHeight: 68,
    paddingVertical: 8,
  },
  checkBox: {
    alignItems: 'center',
    borderRadius: 7,
    borderWidth: 1,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  status: {
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  statusText: { fontSize: 11, fontWeight: '600', lineHeight: 14 },
  detailHero: { borderRadius: 28, gap: 10, padding: 20 },
  detailTitle: { fontSize: 28, lineHeight: 34 },
  keyValue: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 54,
    paddingVertical: 14,
  },
  actionRow: { flexDirection: 'row', gap: 10 },
  fieldGroup: { gap: 7 },
  fieldGlass: { borderRadius: 18, minHeight: 52 },
  multilineField: { minHeight: 112 },
  fieldInput: {
    minHeight: 52,
    paddingHorizontal: 14,
    paddingVertical: 12,
    textAlignVertical: 'top',
  },
  preferenceRow: { alignItems: 'center', flexDirection: 'row', minHeight: 54 },
  successRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 7,
    justifyContent: 'center',
  },
  folderGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  folderCard: {
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 8,
    minHeight: 96,
    padding: 14,
    width: '48%',
  },
  chatBody: { gap: 10, minHeight: 240 },
  bubble: {
    borderRadius: 20,
    maxWidth: '86%',
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  ownBubble: { alignSelf: 'flex-end', borderBottomRightRadius: 7 },
  otherBubble: { alignSelf: 'flex-start', borderBottomLeftRadius: 7 },
  composer: {
    alignItems: 'center',
    borderRadius: 22,
    flexDirection: 'row',
    minHeight: 54,
  },
  composerInput: { flex: 1, minHeight: 52 },
  calendarGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  day: {
    alignItems: 'center',
    borderRadius: 16,
    height: 42,
    justifyContent: 'center',
    width: '13%',
  },
  taskCard: { borderRadius: 18, gap: 12, padding: 14 },
  permissionCard: {
    alignItems: 'center',
    borderRadius: 28,
    gap: 12,
    padding: 28,
  },
  blankCard: {
    alignItems: 'center',
    borderRadius: 30,
    gap: 14,
    minHeight: 360,
    justifyContent: 'center',
    padding: 28,
  },
});
