import type { PropsWithChildren, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from 'react-native';
import { CircleAlert, Inbox, RotateCcw } from 'lucide-react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

import type { ShowcasePreviewState } from '../types/showcase.types';

export function ShowcasePage({
  children,
  topInsetHandled = false,
}: PropsWithChildren<{ topInsetHandled?: boolean }>) {
  const theme = useAppTheme();
  return (
    <SafeAreaView
      edges={
        topInsetHandled
          ? ['right', 'bottom', 'left']
          : ['top', 'right', 'bottom', 'left']
      }
      style={[styles.safeArea, { backgroundColor: theme.colors.canvas }]}
    >
      <ScrollView
        contentContainerStyle={styles.pageContent}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function ShowcaseHeader({
  eyebrow = 'Spacewhy native',
  title,
  description,
  trailing,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  trailing?: ReactNode;
}) {
  const theme = useAppTheme();
  return (
    <View style={styles.header}>
      <View style={styles.headerCopy}>
        <Text style={[styles.eyebrow, { color: theme.colors.accent }]}>
          {eyebrow.toUpperCase()}
        </Text>
        <Text
          accessibilityRole="header"
          style={[theme.typography.display, { color: theme.colors.text }]}
        >
          {title}
        </Text>
        <Text
          style={[theme.typography.body, { color: theme.colors.textMuted }]}
        >
          {description}
        </Text>
      </View>
      {trailing}
    </View>
  );
}

export function ShowcaseNotice({ children }: PropsWithChildren) {
  const theme = useAppTheme();
  return (
    <View
      accessibilityRole="summary"
      style={[
        styles.notice,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <CircleAlert color={theme.colors.accent} size={18} />
      <Text
        style={[
          theme.typography.label,
          styles.noticeText,
          { color: theme.colors.textMuted },
        ]}
      >
        {children}
      </Text>
    </View>
  );
}

export function ShowcaseButton({
  label,
  onPress,
  variant = 'primary',
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}) {
  const theme = useAppTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor:
            variant === 'primary'
              ? theme.colors.accent
              : theme.colors.surfaceElevated,
          borderColor: theme.colors.border,
        },
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <Text
        style={[
          theme.typography.label,
          {
            color:
              variant === 'primary'
                ? theme.colors.accentContrast
                : theme.colors.text,
          },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function ShowcaseField({
  label,
  error,
  multiline,
  ...props
}: TextInputProps & { label: string; error?: string }) {
  const theme = useAppTheme();
  const errorId = `${label.toLowerCase().replace(/\s+/g, '-')}-error`;
  return (
    <View style={styles.field}>
      <Text style={[theme.typography.label, { color: theme.colors.text }]}>
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        accessibilityHint={error}
        aria-describedby={error ? errorId : undefined}
        multiline={multiline}
        placeholderTextColor={theme.colors.textMuted}
        style={[
          theme.typography.body,
          styles.input,
          multiline && styles.multiline,
          {
            backgroundColor: theme.colors.surface,
            borderColor: error ? theme.colors.negative : theme.colors.border,
            color: theme.colors.text,
          },
        ]}
        {...props}
      />
      {error ? (
        <Text
          nativeID={errorId}
          style={[styles.errorText, { color: theme.colors.negative }]}
        >
          {error}
        </Text>
      ) : null}
    </View>
  );
}

export function ShowcaseStateStrip({
  value,
  onChange,
}: {
  value: ShowcasePreviewState;
  onChange: (state: ShowcasePreviewState) => void;
}) {
  const theme = useAppTheme();
  const states: ShowcasePreviewState[] = [
    'success',
    'loading',
    'empty',
    'error',
  ];
  return (
    <ScrollView
      horizontal
      contentContainerStyle={styles.stateStrip}
      showsHorizontalScrollIndicator={false}
    >
      {states.map(state => {
        const selected = state === value;
        return (
          <Pressable
            key={state}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            onPress={() => onChange(state)}
            style={[
              styles.chip,
              {
                backgroundColor: selected
                  ? theme.colors.accent
                  : theme.colors.surface,
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
              {state[0].toUpperCase() + state.slice(1)}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function ShowcaseStatePanel({
  state,
  emptyTitle = 'Nothing here yet',
  onRetry,
}: {
  state: Exclude<ShowcasePreviewState, 'success'>;
  emptyTitle?: string;
  onRetry: () => void;
}) {
  const theme = useAppTheme();
  const loading = state === 'loading';
  const error = state === 'error';
  return (
    <GlassView
      accessibilityLiveRegion="polite"
      style={styles.statePanel}
      variant="surface"
    >
      {loading ? (
        <ActivityIndicator
          accessibilityLabel="Loading preview"
          color={theme.colors.accent}
          size="large"
        />
      ) : error ? (
        <CircleAlert color={theme.colors.negative} size={34} />
      ) : (
        <Inbox color={theme.colors.textMuted} size={34} />
      )}
      <Text
        accessibilityRole="header"
        style={[theme.typography.title, { color: theme.colors.text }]}
      >
        {loading
          ? 'Loading local demo…'
          : error
          ? 'Preview unavailable'
          : emptyTitle}
      </Text>
      <Text
        style={[
          theme.typography.body,
          styles.centerText,
          { color: theme.colors.textMuted },
        ]}
      >
        {loading
          ? 'No network request is made.'
          : error
          ? 'This simulated failure keeps the demo honest and testable.'
          : 'Try another filter or create a local item.'}
      </Text>
      {!loading ? (
        <Pressable
          accessibilityRole="button"
          onPress={onRetry}
          style={styles.retry}
        >
          <RotateCcw color={theme.colors.accent} size={18} />
          <Text
            style={[theme.typography.label, { color: theme.colors.accent }]}
          >
            Restore success state
          </Text>
        </Pressable>
      ) : null}
    </GlassView>
  );
}

export const showcaseStyles = StyleSheet.create({
  card: { gap: 12, padding: 18 },
  row: { alignItems: 'center', flexDirection: 'row', gap: 12 },
  section: { gap: 12 },
});

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  pageContent: { gap: 22, padding: 20, paddingBottom: 120 },
  header: { alignItems: 'flex-start', flexDirection: 'row', gap: 12 },
  headerCopy: { flex: 1, gap: 8 },
  eyebrow: { fontSize: 12, fontWeight: '800', letterSpacing: 1.3 },
  notice: {
    alignItems: 'center',
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 10,
    padding: 14,
  },
  noticeText: { flex: 1 },
  button: {
    alignItems: 'center',
    borderRadius: 15,
    borderWidth: StyleSheet.hairlineWidth,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: 18,
  },
  pressed: { opacity: 0.74, transform: [{ scale: 0.985 }] },
  disabled: { opacity: 0.45 },
  field: { gap: 7 },
  input: {
    borderRadius: 15,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 48,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },
  multiline: { minHeight: 112, textAlignVertical: 'top' },
  errorText: { fontSize: 12, lineHeight: 17 },
  stateStrip: { gap: 8 },
  chip: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 15,
  },
  statePanel: {
    alignItems: 'center',
    gap: 12,
    minHeight: 250,
    justifyContent: 'center',
    padding: 24,
  },
  centerText: { textAlign: 'center' },
  retry: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    minHeight: 44,
    paddingHorizontal: 12,
  },
});
