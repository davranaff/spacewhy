import { useState, type ReactElement } from 'react';
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type ListRenderItem,
} from 'react-native';
import { CalendarDays, Send } from 'lucide-react-native';

import {
  ShowcaseHeader,
  ShowcaseStatePanel,
  ShowcaseStateStrip,
} from '@/features/showcase/components/showcase-primitives';
import {
  AGENDA_ITEMS,
  CHAT_MESSAGES,
  MAIL_PREVIEWS,
} from '@/features/showcase/data/showcase-data';
import type {
  AgendaItem,
  ChatMessage,
  MailPreview,
  ShowcasePreviewState,
} from '@/features/showcase/types/showcase.types';
import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

function StatefulList<T>({
  title,
  description,
  data,
  renderItem,
  emptyTitle,
  footer,
  keyExtractor,
}: {
  title: string;
  description: string;
  data: readonly T[];
  renderItem: ListRenderItem<T>;
  emptyTitle: string;
  footer?: ReactElement;
  keyExtractor: (item: T) => string;
}) {
  const theme = useAppTheme();
  const [state, setState] = useState<ShowcasePreviewState>('success');
  return (
    <FlatList
      ListEmptyComponent={
        state === 'success' ? null : (
          <ShowcaseStatePanel
            emptyTitle={emptyTitle}
            onRetry={() => setState('success')}
            state={state}
          />
        )
      }
      ListFooterComponent={state === 'success' ? footer : null}
      ListHeaderComponent={
        <View style={styles.header}>
          <ShowcaseHeader title={title} description={description} />
          <ShowcaseStateStrip onChange={setState} value={state} />
        </View>
      }
      contentContainerStyle={[
        styles.content,
        { backgroundColor: theme.colors.canvas },
      ]}
      data={state === 'success' ? [...data] : []}
      keyExtractor={keyExtractor}
      renderItem={renderItem}
    />
  );
}

export function ShowcaseMailScreen() {
  const theme = useAppTheme();
  return (
    <StatefulList<MailPreview>
      title="Inbox"
      description="Message hierarchy optimized for scanning, unread state and 44pt targets."
      data={MAIL_PREVIEWS}
      emptyTitle="Inbox zero"
      keyExtractor={item => item.id}
      renderItem={({ item }) => (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${item.unread ? 'Unread, ' : ''}${
            item.sender
          }, ${item.subject}`}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <GlassView style={styles.mail} variant="surface">
            <View
              style={[
                styles.avatar,
                {
                  backgroundColor: item.unread
                    ? theme.colors.accent
                    : theme.colors.surfaceElevated,
                },
              ]}
            >
              <Text
                style={[
                  theme.typography.label,
                  {
                    color: item.unread
                      ? theme.colors.accentContrast
                      : theme.colors.text,
                  },
                ]}
              >
                {item.sender[0]}
              </Text>
            </View>
            <View style={styles.mailCopy}>
              <View style={styles.rowBetween}>
                <Text
                  style={[
                    theme.typography.title,
                    styles.flex,
                    { color: theme.colors.text },
                  ]}
                  numberOfLines={1}
                >
                  {item.sender}
                </Text>
                <Text
                  style={[
                    theme.typography.label,
                    { color: theme.colors.textMuted },
                  ]}
                >
                  {item.time}
                </Text>
              </View>
              <Text
                style={[
                  theme.typography.label,
                  {
                    color: item.unread
                      ? theme.colors.text
                      : theme.colors.textMuted,
                  },
                ]}
                numberOfLines={1}
              >
                {item.subject}
              </Text>
              <Text
                style={[
                  theme.typography.body,
                  { color: theme.colors.textMuted },
                ]}
                numberOfLines={2}
              >
                {item.preview}
              </Text>
            </View>
          </GlassView>
        </Pressable>
      )}
    />
  );
}

export function ShowcaseChatScreen() {
  const theme = useAppTheme();
  const [draft, setDraft] = useState('');
  const [sent, setSent] = useState('');
  const footer = (
    <View style={styles.chatFooter}>
      {sent ? (
        <Text
          accessibilityLiveRegion="polite"
          style={[theme.typography.label, { color: theme.colors.positive }]}
        >
          Local message added: {sent}
        </Text>
      ) : null}
      <GlassView style={styles.composer} variant="control">
        <TextInput
          accessibilityLabel="Message"
          onChangeText={setDraft}
          placeholder="Write a local message"
          placeholderTextColor={theme.colors.textMuted}
          style={[
            theme.typography.body,
            styles.composerInput,
            { color: theme.colors.text },
          ]}
          value={draft}
        />
        <Pressable
          accessibilityLabel="Send local message"
          accessibilityRole="button"
          disabled={!draft.trim()}
          onPress={() => {
            setSent(draft.trim());
            setDraft('');
          }}
          style={[
            styles.send,
            { backgroundColor: theme.colors.accent },
            !draft.trim() && styles.disabled,
          ]}
        >
          <Send color={theme.colors.accentContrast} size={19} />
        </Pressable>
      </GlassView>
    </View>
  );
  return (
    <StatefulList<ChatMessage>
      title="Team chat"
      description="Conversation, composer and simulated delivery states without a socket or API."
      data={CHAT_MESSAGES}
      emptyTitle="No conversation selected"
      footer={footer}
      keyExtractor={item => item.id}
      renderItem={({ item }) => (
        <View style={[styles.bubbleRow, item.own && styles.ownRow]}>
          <GlassView
            accessibilityLabel={`${item.author} at ${item.time}: ${item.body}`}
            style={[
              styles.bubble,
              {
                backgroundColor: item.own
                  ? theme.colors.surfaceElevated
                  : undefined,
              },
            ]}
            variant="control"
          >
            <Text
              style={[theme.typography.label, { color: theme.colors.accent }]}
            >
              {item.author} · {item.time}
            </Text>
            <Text style={[theme.typography.body, { color: theme.colors.text }]}>
              {item.body}
            </Text>
          </GlassView>
        </View>
      )}
    />
  );
}

export function ShowcaseCalendarScreen() {
  const theme = useAppTheme();
  return (
    <StatefulList<AgendaItem>
      title="Today · August 15"
      description="A mobile agenda with semantic time ordering and compact event cards."
      data={AGENDA_ITEMS}
      emptyTitle="No events today"
      keyExtractor={item => item.id}
      renderItem={({ item }) => (
        <GlassView
          accessibilityLabel={`${item.time}, ${item.title}, ${item.subtitle}`}
          style={styles.event}
          variant="surface"
        >
          <View style={[styles.eventMark, { backgroundColor: item.color }]} />
          <View style={styles.eventTime}>
            <Text
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              {item.time}
            </Text>
            <CalendarDays color={theme.colors.textMuted} size={17} />
          </View>
          <View style={styles.flex}>
            <Text
              style={[theme.typography.title, { color: theme.colors.text }]}
            >
              {item.title}
            </Text>
            <Text
              style={[theme.typography.body, { color: theme.colors.textMuted }]}
            >
              {item.subtitle}
            </Text>
          </View>
        </GlassView>
      )}
    />
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, gap: 10, padding: 20, paddingBottom: 120 },
  header: { gap: 16, marginBottom: 8 },
  pressed: { opacity: 0.72 },
  mail: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    minHeight: 112,
    padding: 15,
  },
  avatar: {
    alignItems: 'center',
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  mailCopy: { flex: 1, gap: 3 },
  rowBetween: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
  flex: { flex: 1 },
  bubbleRow: { alignItems: 'flex-start' },
  ownRow: { alignItems: 'flex-end' },
  bubble: { gap: 5, maxWidth: '86%', padding: 14 },
  chatFooter: { gap: 8, marginTop: 10 },
  composer: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    minHeight: 58,
    padding: 7,
  },
  composerInput: { flex: 1, minHeight: 44, paddingHorizontal: 10 },
  send: {
    alignItems: 'center',
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  disabled: { opacity: 0.4 },
  event: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    minHeight: 92,
    padding: 14,
  },
  eventMark: { borderRadius: 3, height: 48, width: 5 },
  eventTime: { alignItems: 'center', gap: 4, width: 62 },
});
