import type { PropsWithChildren, ReactNode } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import {
  ChevronRight,
  CircleAlert,
  Component,
  Layers3,
  ListTree,
  MousePointer2,
  Palette,
  PanelsTopLeft,
  Search,
  TextCursorInput,
  X,
  type LucideIcon,
} from 'lucide-react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';

import type {
  CatalogExample,
  CatalogGroup,
} from '@/features/catalog/types/catalog.types';

const GROUP_ICONS: Record<CatalogGroup, LucideIcon> = {
  foundations: Palette,
  controls: MousePointer2,
  forms: TextCursorInput,
  feedback: CircleAlert,
  'data-display': ListTree,
  surfaces: Layers3,
  patterns: PanelsTopLeft,
};

type CatalogScreenHeaderProps = Readonly<{
  eyebrow?: string;
  title: string;
  description: string;
  trailing?: ReactNode;
}>;

export function CatalogScreenHeader({
  eyebrow = 'Spacewhy UI Kit',
  title,
  description,
  trailing,
}: CatalogScreenHeaderProps) {
  const theme = useAppTheme();

  return (
    <View style={styles.header}>
      <View style={styles.headerCopy}>
        <Text style={[styles.eyebrow, { color: theme.colors.accent }]}>
          {eyebrow.toLocaleUpperCase()}
        </Text>
        <Text
          accessibilityRole="header"
          style={[
            styles.title,
            theme.typography.display,
            { color: theme.colors.text },
          ]}
        >
          {title}
        </Text>
        <Text
          style={[
            styles.description,
            theme.typography.body,
            { color: theme.colors.textMuted },
          ]}
        >
          {description}
        </Text>
      </View>
      {trailing}
    </View>
  );
}

type CatalogExampleCardProps = Readonly<{
  example: CatalogExample;
  onPress: (example: CatalogExample) => void;
}>;

export function CatalogExampleCard({
  example,
  onPress,
}: CatalogExampleCardProps) {
  const theme = useAppTheme();
  const Icon = GROUP_ICONS[example.group] ?? Component;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${example.title}. ${example.description}`}
      accessibilityHint="Opens the interactive component example"
      onPress={() => onPress(example)}
      style={({ pressed }) => [styles.cardPressable, pressed && styles.pressed]}
    >
      <GlassView variant="surface" interactive style={styles.cardGlass}>
        <View
          style={[
            styles.iconBox,
            {
              backgroundColor: theme.colors.surfaceElevated,
              borderColor: theme.colors.border,
            },
          ]}
        >
          <Icon color={theme.colors.accent} size={20} strokeWidth={1.8} />
        </View>
        <View style={styles.cardCopy}>
          <Text
            style={[
              theme.typography.title,
              styles.cardTitle,
              { color: theme.colors.text },
            ]}
          >
            {example.title}
          </Text>
          <Text
            numberOfLines={2}
            style={[
              theme.typography.body,
              styles.cardDescription,
              { color: theme.colors.textMuted },
            ]}
          >
            {example.description}
          </Text>
        </View>
        <ChevronRight color={theme.colors.textMuted} size={20} />
      </GlassView>
    </Pressable>
  );
}

type CatalogSectionHeadingProps = Readonly<{
  title: string;
  description?: string;
}>;

export function CatalogSectionHeading({
  title,
  description,
}: CatalogSectionHeadingProps) {
  const theme = useAppTheme();

  return (
    <View style={styles.sectionHeading}>
      <Text
        accessibilityRole="header"
        style={[theme.typography.title, { color: theme.colors.text }]}
      >
        {title}
      </Text>
      {description ? (
        <Text
          style={[
            theme.typography.body,
            styles.sectionDescription,
            { color: theme.colors.textMuted },
          ]}
        >
          {description}
        </Text>
      ) : null}
    </View>
  );
}

type CatalogSearchProps = Readonly<{
  value: string;
  onChangeText: (value: string) => void;
}>;

export function CatalogSearch({ value, onChangeText }: CatalogSearchProps) {
  const theme = useAppTheme();

  return (
    <View
      style={[
        styles.search,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <Search color={theme.colors.textMuted} size={19} />
      <TextInput
        accessibilityLabel="Search component catalog"
        accessibilityHint="Filters examples by name and category"
        autoCapitalize="none"
        autoCorrect={false}
        clearButtonMode="while-editing"
        onChangeText={onChangeText}
        placeholder="Search components"
        placeholderTextColor={theme.colors.textMuted}
        returnKeyType="search"
        style={[
          theme.typography.body,
          styles.searchInput,
          { color: theme.colors.text },
        ]}
        value={value}
      />
      {value ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Clear search"
          hitSlop={8}
          onPress={() => onChangeText('')}
          style={styles.searchClear}
        >
          <X color={theme.colors.textMuted} size={18} />
        </Pressable>
      ) : null}
    </View>
  );
}

type DemoSurfaceProps = PropsWithChildren<{
  title?: string;
  description?: string;
  glass?: boolean;
  style?: StyleProp<ViewStyle>;
}>;

export function DemoSurface({
  title,
  description,
  glass = false,
  style,
  children,
}: DemoSurfaceProps) {
  const theme = useAppTheme();
  const copy =
    title || description ? (
      <View style={styles.demoCopy}>
        {title ? (
          <Text style={[theme.typography.title, { color: theme.colors.text }]}>
            {title}
          </Text>
        ) : null}
        {description ? (
          <Text
            style={[theme.typography.body, { color: theme.colors.textMuted }]}
          >
            {description}
          </Text>
        ) : null}
      </View>
    ) : null;

  if (glass) {
    return (
      <GlassView variant="surface" style={[styles.demoSurface, style]}>
        {copy}
        {children}
      </GlassView>
    );
  }

  return (
    <View
      style={[
        styles.demoSurface,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        style,
      ]}
    >
      {copy}
      {children}
    </View>
  );
}

type DemoButtonProps = Omit<PressableProps, 'children' | 'style'> &
  Readonly<{
    label: string;
    variant?: 'primary' | 'secondary' | 'quiet' | 'danger';
    style?: StyleProp<ViewStyle>;
  }>;

export function DemoButton({
  label,
  variant = 'primary',
  disabled,
  style,
  ...props
}: DemoButtonProps) {
  const theme = useAppTheme();
  const isPrimary = variant === 'primary';
  const isDanger = variant === 'danger';
  const backgroundColor = isPrimary
    ? theme.colors.accent
    : isDanger
    ? theme.colors.negative
    : variant === 'quiet'
    ? 'transparent'
    : theme.colors.surfaceElevated;
  const color =
    isPrimary || isDanger ? theme.colors.accentContrast : theme.colors.text;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      style={({ pressed }) => [
        styles.demoButton,
        { backgroundColor, borderColor: theme.colors.border },
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
      {...props}
    >
      <Text style={[theme.typography.label, styles.demoButtonLabel, { color }]}>
        {label}
      </Text>
    </Pressable>
  );
}

export function CatalogBackdrop({ children }: PropsWithChildren) {
  const theme = useAppTheme();
  const topOrbStyle = {
    backgroundColor: theme.isDark ? '#322019' : '#FFD7CC',
  };
  const bottomOrbStyle = {
    backgroundColor: theme.isDark ? '#111B25' : '#DCEEFF',
  };

  return (
    <View style={[styles.backdrop, { backgroundColor: theme.colors.canvas }]}>
      <View
        pointerEvents="none"
        style={[styles.backdropOrb, styles.orbTop, topOrbStyle]}
      />
      <View
        pointerEvents="none"
        style={[styles.backdropOrb, styles.orbBottom, bottomOrbStyle]}
      />
      {children}
    </View>
  );
}

export const catalogLayout = StyleSheet.create({
  content: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 132,
    gap: 12,
  },
  listSeparator: { height: 12 },
});

const styles = StyleSheet.create({
  backdrop: { flex: 1, overflow: 'hidden' },
  backdropOrb: {
    position: 'absolute',
    width: 260,
    height: 260,
    borderRadius: 130,
    opacity: 0.38,
    transform: [{ scaleX: 1.4 }],
  },
  orbTop: { right: -120, top: -80 },
  orbBottom: { left: -140, bottom: 40 },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 10,
  },
  headerCopy: { flex: 1, gap: 7 },
  eyebrow: {
    fontSize: 11,
    lineHeight: 15,
    fontWeight: '800',
    letterSpacing: 1.3,
  },
  title: { fontSize: 34, lineHeight: 40 },
  description: { maxWidth: 520 },
  cardPressable: { minHeight: 104 },
  cardGlass: {
    minHeight: 104,
    padding: 14,
    borderRadius: 22,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: 15,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardCopy: { flex: 1, gap: 3 },
  cardTitle: { fontSize: 17, lineHeight: 22 },
  cardDescription: { fontSize: 14, lineHeight: 19 },
  pressed: { opacity: 0.68, transform: [{ scale: 0.985 }] },
  disabled: { opacity: 0.42 },
  sectionHeading: { gap: 4, paddingTop: 12, paddingBottom: 4 },
  sectionDescription: { fontSize: 14, lineHeight: 19 },
  search: {
    minHeight: 48,
    borderRadius: 17,
    borderWidth: StyleSheet.hairlineWidth,
    paddingLeft: 14,
    paddingRight: 6,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  searchInput: { flex: 1, minHeight: 46, paddingVertical: 0 },
  searchClear: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  demoSurface: {
    padding: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 24,
    gap: 16,
    overflow: 'hidden',
  },
  demoCopy: { gap: 4 },
  demoButton: {
    minHeight: 48,
    minWidth: 80,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  demoButtonLabel: { fontSize: 14, lineHeight: 18 },
});
