import type {
  AgendaItem,
  ChatMessage,
  MailPreview,
  ShowcaseRecord,
  ShowcaseRouteDescriptor,
} from '../types/showcase.types';

export const SHOWCASE_ROUTE_DESCRIPTORS: readonly ShowcaseRouteDescriptor[] = [
  {
    name: 'ShowcaseLogin',
    title: 'Sign in',
    description: 'Local demo authentication shell',
    group: 'auth',
  },
  {
    name: 'ShowcaseRegister',
    title: 'Create account',
    description: 'Registration and validation states',
    group: 'auth',
  },
  {
    name: 'ShowcaseDashboard',
    title: 'Dashboard',
    description: 'Metrics, activity and native SVG charts',
    group: 'dashboard',
  },
  {
    name: 'ShowcaseRecords',
    title: 'Records',
    description: 'Virtualized search and filtering',
    group: 'management',
  },
  {
    name: 'ShowcaseRecordDetail',
    title: 'Record detail',
    description: 'Mobile detail information hierarchy',
    group: 'management',
  },
  {
    name: 'ShowcaseRecordForm',
    title: 'Editable form',
    description: 'Validation and local save feedback',
    group: 'management',
  },
  {
    name: 'ShowcaseMail',
    title: 'Mail',
    description: 'Inbox and message states',
    group: 'communication',
  },
  {
    name: 'ShowcaseChat',
    title: 'Chat',
    description: 'Conversation and composer states',
    group: 'communication',
  },
  {
    name: 'ShowcaseCalendar',
    title: 'Calendar',
    description: 'Agenda and date selection states',
    group: 'communication',
  },
  {
    name: 'ShowcaseProfileSettings',
    title: 'Profile & settings',
    description: 'Account and preference examples',
    group: 'account',
  },
] as const;

export const SHOWCASE_RECORDS: readonly ShowcaseRecord[] = [
  {
    id: 'sw-1048',
    name: 'Orbital analytics',
    category: 'Engineering',
    owner: 'Maya Chen',
    status: 'Active',
    updatedAt: 'Today, 09:42',
    progress: 84,
  },
  {
    id: 'sw-1047',
    name: 'Glass controls',
    category: 'Design',
    owner: 'Noah Williams',
    status: 'Review',
    updatedAt: 'Yesterday',
    progress: 68,
  },
  {
    id: 'sw-1046',
    name: 'Billing automations',
    category: 'Operations',
    owner: 'Zara Khan',
    status: 'Draft',
    updatedAt: 'Aug 13',
    progress: 42,
  },
  {
    id: 'sw-1045',
    name: 'Mobile navigation',
    category: 'Design',
    owner: 'Leo Martin',
    status: 'Active',
    updatedAt: 'Aug 12',
    progress: 91,
  },
  {
    id: 'sw-1044',
    name: 'Realtime events',
    category: 'Engineering',
    owner: 'Amir Saidov',
    status: 'Review',
    updatedAt: 'Aug 11',
    progress: 73,
  },
  {
    id: 'sw-1043',
    name: 'Support workflow',
    category: 'Operations',
    owner: 'Iris Walker',
    status: 'Active',
    updatedAt: 'Aug 10',
    progress: 79,
  },
] as const;

export const MAIL_PREVIEWS: readonly MailPreview[] = [
  {
    id: 'mail-1',
    sender: 'Maya Chen',
    subject: 'Design review is ready',
    preview: 'The native material pass is ready for your notes.',
    time: '09:42',
    unread: true,
  },
  {
    id: 'mail-2',
    sender: 'Spacewhy Ops',
    subject: 'Weekly system digest',
    preview: 'Seven flows improved and all quality gates passed.',
    time: '08:10',
    unread: true,
  },
  {
    id: 'mail-3',
    sender: 'Noah Williams',
    subject: 'Dashboard handoff',
    preview: 'I attached the final mobile chart states.',
    time: 'Yesterday',
    unread: false,
  },
] as const;

export const CHAT_MESSAGES: readonly ChatMessage[] = [
  {
    id: 'chat-1',
    author: 'Maya',
    body: 'The glass fallback now respects Reduce Transparency.',
    time: '09:38',
    own: false,
  },
  {
    id: 'chat-2',
    author: 'You',
    body: 'Perfect. I will verify Android matte mode next.',
    time: '09:40',
    own: true,
  },
  {
    id: 'chat-3',
    author: 'Maya',
    body: 'Great — the component contract is unchanged.',
    time: '09:41',
    own: false,
  },
] as const;

export const AGENDA_ITEMS: readonly AgendaItem[] = [
  {
    id: 'event-1',
    time: '09:30',
    title: 'Product review',
    subtitle: 'Design systems · 45 min',
    color: '#FF5A36',
  },
  {
    id: 'event-2',
    time: '11:00',
    title: 'Mobile QA',
    subtitle: 'iOS & Android · 60 min',
    color: '#5B8CFF',
  },
  {
    id: 'event-3',
    time: '14:30',
    title: 'Architecture sync',
    subtitle: 'Platform team · 30 min',
    color: '#40D886',
  },
] as const;

export function filterShowcaseRecords(
  records: readonly ShowcaseRecord[],
  query: string,
  category: 'All' | ShowcaseRecord['category'],
): ShowcaseRecord[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();

  return records.filter(record => {
    const matchesCategory = category === 'All' || record.category === category;
    const matchesQuery =
      !normalizedQuery ||
      [record.name, record.owner, record.id, record.status]
        .join(' ')
        .toLocaleLowerCase()
        .includes(normalizedQuery);

    return matchesCategory && matchesQuery;
  });
}
