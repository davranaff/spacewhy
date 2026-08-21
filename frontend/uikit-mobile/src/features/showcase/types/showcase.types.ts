export type ShowcasePreviewState = 'success' | 'loading' | 'empty' | 'error';

export type ShowcaseRouteName =
  | 'ShowcaseLogin'
  | 'ShowcaseRegister'
  | 'ShowcaseDashboard'
  | 'ShowcaseRecords'
  | 'ShowcaseRecordDetail'
  | 'ShowcaseRecordForm'
  | 'ShowcaseMail'
  | 'ShowcaseChat'
  | 'ShowcaseCalendar'
  | 'ShowcaseProfileSettings';

export interface ShowcaseRouteDescriptor {
  name: ShowcaseRouteName;
  title: string;
  description: string;
  group: 'auth' | 'dashboard' | 'management' | 'communication' | 'account';
}

export interface ShowcaseRecord {
  id: string;
  name: string;
  category: 'Design' | 'Engineering' | 'Operations';
  owner: string;
  status: 'Active' | 'Draft' | 'Review';
  updatedAt: string;
  progress: number;
}

export interface MailPreview {
  id: string;
  sender: string;
  subject: string;
  preview: string;
  time: string;
  unread: boolean;
}

export interface ChatMessage {
  id: string;
  author: string;
  body: string;
  time: string;
  own: boolean;
}

export interface AgendaItem {
  id: string;
  time: string;
  title: string;
  subtitle: string;
  color: string;
}
