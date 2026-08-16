export type DashboardTemplateGroup =
  | 'overview'
  | 'management'
  | 'workspace'
  | 'system';

export type DashboardTemplateKind =
  | 'overview'
  | 'profile'
  | 'cards'
  | 'list'
  | 'detail'
  | 'form'
  | 'account'
  | 'file-manager'
  | 'mail'
  | 'chat'
  | 'calendar'
  | 'kanban'
  | 'permission'
  | 'blank';

export type DashboardTemplateId =
  | 'app-overview'
  | 'ecommerce-overview'
  | 'analytics-overview'
  | 'banking-overview'
  | 'booking-overview'
  | 'file-overview'
  | 'user-profile'
  | 'user-cards'
  | 'user-list'
  | 'user-create'
  | 'user-edit'
  | 'user-account'
  | 'product-list'
  | 'product-detail'
  | 'product-create'
  | 'product-edit'
  | 'order-list'
  | 'order-detail'
  | 'invoice-list'
  | 'invoice-detail'
  | 'invoice-create'
  | 'invoice-edit'
  | 'blog-list'
  | 'blog-detail'
  | 'blog-create'
  | 'blog-edit'
  | 'job-list'
  | 'job-detail'
  | 'job-create'
  | 'job-edit'
  | 'tour-list'
  | 'tour-detail'
  | 'tour-create'
  | 'tour-edit'
  | 'file-manager'
  | 'mail'
  | 'chat'
  | 'calendar'
  | 'kanban'
  | 'permission'
  | 'blank';

export type DashboardTemplate = Readonly<{
  id: DashboardTemplateId;
  title: string;
  family: string;
  group: DashboardTemplateGroup;
  kind: DashboardTemplateKind;
  description: string;
  webPath: string;
  keywords: readonly string[];
}>;

export type DashboardTemplateSection = Readonly<{
  id: DashboardTemplateGroup;
  title: string;
  description: string;
  templates: readonly DashboardTemplate[];
}>;
