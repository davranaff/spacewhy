import { addDays } from 'date-fns';

import { IPostItem } from 'src/types/blog';
import { ICalendarEvent } from 'src/types/calendar';
import { IChatConversation, IChatParticipant } from 'src/types/chat';
import { IKanbanBoard } from 'src/types/kanban';
import { IMail, IMailLabel } from 'src/types/mail';
import { IProduct } from 'src/types/product';

import { CALENDAR_COLOR_OPTIONS } from './_calendar';
import { _mock } from './_mock';

// ----------------------------------------------------------------------

const PRODUCT_COLORS = ['#00AB55', '#1890FF', '#FFC107', '#FF4842'];
const PRODUCT_SIZES = ['7', '8', '9', '10', '11'];

const products: IProduct[] = [...Array(16)].map((_, index) => {
  const price = _mock.number.price(index);

  return {
    id: _mock.id(index),
    sku: `SW-${String(index + 1).padStart(4, '0')}`,
    name: _mock.productName(index),
    code: `SPW${String(index + 1).padStart(4, '0')}`,
    price,
    taxes: 10,
    tags: ['Spacewhy', 'Design system'],
    gender: ['Men', 'Women', 'Kids'][index % 3],
    sizes: PRODUCT_SIZES,
    publish: index % 4 === 0 ? 'draft' : 'published',
    coverUrl: _mock.image.product(index),
    images: [0, 1, 2, 3].map((offset) => _mock.image.product((index + offset) % 24)),
    colors: PRODUCT_COLORS.slice(0, (index % PRODUCT_COLORS.length) + 1),
    quantity: 1,
    category: ['Shoes', 'Apparel', 'Accessories'][index % 3],
    available: Math.max(0, 72 - index * 4),
    totalSold: 120 + index * 17,
    description: _mock.description(index),
    totalRatings: 48 + index * 3,
    totalReviews: 12 + index,
    inventoryType: ['in stock', 'low stock', 'out of stock'][index % 3],
    subDescription: _mock.sentence(index),
    priceSale: index % 3 === 0 ? Math.max(1, price - 20) : null,
    reviews: [],
    createdAt: _mock.time(index),
    ratings: [5, 4, 3, 2, 1].map((star) => ({
      name: `${star} Star`,
      starCount: star,
      reviewCount: Math.max(1, 18 - star - index),
    })),
    saleLabel: { enabled: index % 3 === 0, content: 'SALE' },
    newLabel: { enabled: index < 4, content: 'NEW' },
  };
});

const posts: IPostItem[] = [...Array(12)].map((_, index) => ({
  id: _mock.id(index),
  title: _mock.postTitle(index),
  tags: ['Spacewhy', 'UI', 'Design'],
  publish: index % 4 === 0 ? 'draft' : 'published',
  content: `<p>${_mock.description(index)}</p>`,
  coverUrl: _mock.image.cover(index),
  metaTitle: _mock.postTitle(index),
  totalViews: 1200 + index * 173,
  totalShares: 80 + index * 7,
  description: _mock.description(index),
  totalComments: 12 + index,
  totalFavorites: 24 + index * 2,
  metaKeywords: ['spacewhy', 'ui kit', 'liquid glass'],
  metaDescription: _mock.sentence(index),
  comments: [],
  createdAt: _mock.time(index),
  favoritePerson: [...Array(3)].map((__, personIndex) => ({
    name: _mock.fullName(personIndex),
    avatarUrl: _mock.image.avatar(personIndex),
  })),
  author: {
    name: _mock.fullName(index),
    avatarUrl: _mock.image.avatar(index),
  },
}));

const mailLabels: IMailLabel[] = [
  { id: 'all', type: 'system', name: 'All', color: 'default', unreadCount: 4 },
  { id: 'inbox', type: 'system', name: 'Inbox', color: 'primary', unreadCount: 4 },
  { id: 'important', type: 'system', name: 'Important', color: 'warning' },
  { id: 'starred', type: 'system', name: 'Starred', color: 'info' },
  { id: 'sent', type: 'system', name: 'Sent', color: 'success' },
  { id: 'drafts', type: 'system', name: 'Drafts', color: 'default' },
  { id: 'trash', type: 'system', name: 'Trash', color: 'error' },
];

const mails: IMail[] = [...Array(12)].map((_, index) => ({
  id: _mock.id(index),
  labelIds: index % 3 === 0 ? ['important', 'starred'] : [],
  folder: index > 9 ? 'sent' : 'inbox',
  isImportant: index % 3 === 0,
  isStarred: index % 4 === 0,
  isUnread: index < 4,
  subject: _mock.sentence(index),
  message: _mock.description(index),
  createdAt: _mock.time(index),
  attachments: [],
  from: {
    name: _mock.fullName(index),
    email: _mock.email(index),
    avatarUrl: _mock.image.avatar(index),
  },
  to: [
    {
      name: 'Spacewhy Demo',
      email: 'demo@minimals.cc',
      avatarUrl: _mock.image.avatar(24),
    },
  ],
}));

const CHAT_STATUSES: IChatParticipant['status'][] = ['online', 'offline', 'busy'];

const contacts: IChatParticipant[] = [...Array(8)].map((_, index) => ({
  id: _mock.id(index),
  name: _mock.fullName(index),
  role: _mock.role(index),
  email: _mock.email(index),
  address: _mock.fullAddress(index),
  avatarUrl: _mock.image.avatar(index),
  phoneNumber: _mock.phoneNumber(index),
  lastActivity: _mock.time(index),
  status: CHAT_STATUSES[index % CHAT_STATUSES.length],
}));

const currentUser = contacts[0];

const conversations: IChatConversation[] = contacts.slice(1, 6).map((contact, index) => ({
  id: `conversation-${contact.id}`,
  type: 'ONE_TO_ONE',
  unreadCount: index < 2 ? index + 1 : 0,
  participants: [currentUser, contact],
  messages: [...Array(5)].map((_, messageIndex) => ({
    id: `${contact.id}-message-${messageIndex}`,
    body: _mock.sentence((index + messageIndex) % 24),
    createdAt: _mock.time(messageIndex),
    senderId: messageIndex % 2 === 0 ? contact.id : currentUser.id,
    contentType: 'text',
    attachments: [],
  })),
}));

const kanbanColumns = [
  { id: 'column-todo', name: 'To do', taskIds: ['task-1', 'task-2'] },
  { id: 'column-progress', name: 'In progress', taskIds: ['task-3', 'task-4'] },
  { id: 'column-done', name: 'Done', taskIds: ['task-5', 'task-6'] },
];

const kanbanBoard: IKanbanBoard = {
  columns: kanbanColumns,
  ordered: kanbanColumns.map((column) => column.id),
  tasks: [...Array(6)].map((_, index) => ({
    id: `task-${index + 1}`,
    name: _mock.taskNames(index),
    status: kanbanColumns[Math.floor(index / 2)].name,
    priority: ['low', 'medium', 'high'][index % 3],
    labels: ['UI', 'Spacewhy'],
    description: _mock.description(index),
    attachments: [],
    comments: [],
    assignee: [
      {
        ...contacts[index % contacts.length],
        lastActivity: new Date(contacts[index % contacts.length].lastActivity),
      },
    ],
    due: [new Date(), addDays(new Date(), index + 2)],
    reporter: {
      id: currentUser.id,
      name: currentUser.name,
      avatarUrl: currentUser.avatarUrl,
    },
  })),
};

const calendarEvents: ICalendarEvent[] = [...Array(8)].map((_, index) => ({
  id: `event-${index + 1}`,
  title: _mock.taskNames(index),
  description: _mock.sentence(index),
  color: CALENDAR_COLOR_OPTIONS[index % CALENDAR_COLOR_OPTIONS.length],
  allDay: index % 3 === 0,
  start: addDays(new Date(), index - 3),
  end: addDays(new Date(), index - 2),
}));

// ----------------------------------------------------------------------

const normalizeBody = (data: unknown) => {
  if (typeof data !== 'string') {
    return data as Record<string, any> | undefined;
  }

  try {
    return JSON.parse(data) as Record<string, any>;
  } catch {
    return undefined;
  }
};

export function getDemoApiResponse(
  url = '',
  method = 'get',
  params: Record<string, any> = {},
  requestData?: unknown
) {
  const body = normalizeBody(requestData);

  if (url === '/api/product/list') return { products };
  if (url === '/api/product/details') {
    return { product: products.find((product) => product.id === params.productId) || products[0] };
  }
  if (url === '/api/product/search') {
    const query = String(params.query || '').toLowerCase();
    return { results: products.filter((product) => product.name.toLowerCase().includes(query)) };
  }

  if (url === '/api/post/list') return { posts };
  if (url === '/api/post/details') {
    return { post: posts.find((post) => post.title === params.title) || posts[0] };
  }
  if (url === '/api/post/latest') {
    return { posts: posts.filter((post) => post.title !== params.title).slice(0, 4) };
  }
  if (url === '/api/post/search') {
    const query = String(params.query || '').toLowerCase();
    return { results: posts.filter((post) => post.title.toLowerCase().includes(query)) };
  }

  if (url === '/api/mail/labels') return { labels: mailLabels };
  if (url === '/api/mail/list') {
    const labelId = String(params.labelId || 'all');
    const filtered =
      labelId === 'all'
        ? mails
        : mails.filter(
            (mail) => mail.folder === labelId || mail.labelIds.includes(labelId)
          );
    return { mails: filtered };
  }
  if (url === '/api/mail/details') {
    return { mail: mails.find((mail) => mail.id === params.mailId) || mails[0] };
  }

  if (url === '/api/chat' && method === 'get') {
    if (params.endpoint === 'contacts') return { contacts };
    if (params.endpoint === 'conversation') {
      return {
        conversation:
          conversations.find((conversation) => conversation.id === params.conversationId) || null,
      };
    }
    if (params.endpoint === 'mark-as-seen') return { conversationId: params.conversationId };
    return { conversations };
  }
  if (url === '/api/chat' && method === 'put') {
    return {
      conversationId: body?.conversationId,
      message: {
        id: `message-${Date.now()}`,
        body: body?.body || '',
        createdAt: new Date(),
        senderId: currentUser.id,
        contentType: 'text',
        attachments: [],
      },
    };
  }
  if (url === '/api/chat' && method === 'post') {
    const requestedRecipients = body?.recipients;
    const recipients = Array.isArray(requestedRecipients) ? requestedRecipients : [];
    const conversationId = `conversation-${Date.now()}`;

    return {
      conversation: {
        id: conversationId,
        type: recipients.length > 1 ? 'GROUP' : 'ONE_TO_ONE',
        unreadCount: 0,
        participants: [currentUser, ...recipients],
        messages: [
          {
            id: `message-${Date.now()}`,
            body: body?.body || '',
            createdAt: new Date(),
            senderId: currentUser.id,
            contentType: 'text',
            attachments: [],
          },
        ],
      },
    };
  }

  if (url === '/api/kanban' && method === 'get') return { board: kanbanBoard };
  if (url === '/api/kanban' && method === 'post') {
    if (params.endpoint === 'delete') return { columnId: body?.columnId };

    if (params.endpoint === 'update') {
      const existingColumn =
        kanbanColumns.find((item) => item.id === body?.columnId) || kanbanColumns[0];

      return { column: { ...existingColumn, ...body?.newData } };
    }

    return {
      column: { id: `column-${Date.now()}`, name: body?.name || 'New column', taskIds: [] },
    };
  }

  if (url === '/api/calendar' && method === 'get') return { events: calendarEvents };
  if (url === '/api/calendar' && method === 'post') {
    return { event: { id: `event-${Date.now()}`, ...body } };
  }
  if (url === '/api/calendar' && method === 'put') {
    return { event: { id: body?.eventId, ...body?.eventData } };
  }
  if (url === '/api/calendar' && method === 'patch') return { eventId: body?.eventId };

  return undefined;
}
