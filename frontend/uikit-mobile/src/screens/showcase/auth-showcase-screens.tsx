import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useAppTheme } from '@/shared/theme';
import { GlassView } from '@/shared/ui/glass-view';
import {
  ShowcaseButton,
  ShowcaseField,
  ShowcaseHeader,
  ShowcaseNotice,
  ShowcasePage,
} from '@/features/showcase/components/showcase-primitives';

function AuthShell({
  mode,
  onSwitchMode,
  topInsetHandled,
}: {
  mode: 'login' | 'register';
  onSwitchMode?: () => void;
  topInsetHandled?: boolean;
}) {
  const theme = useAppTheme();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('demo@spacewhy.uz');
  const [password, setPassword] = useState('spacewhy');
  const [message, setMessage] = useState('');
  const register = mode === 'register';
  const invalid =
    !/^\S+@\S+\.\S+$/.test(email) ||
    password.length < 6 ||
    (register && name.trim().length < 2);

  return (
    <ShowcasePage topInsetHandled={topInsetHandled}>
      <ShowcaseHeader
        title={register ? 'Create your workspace' : 'Welcome back'}
        description={
          register
            ? 'A complete mobile registration shell with local validation.'
            : 'A focused, thumb-friendly entry into the UI kit.'
        }
      />
      <ShowcaseNotice>
        This is an honest local demo. It does not create an account, contact a
        backend or store credentials.
      </ShowcaseNotice>
      <GlassView style={styles.form} variant="floating">
        {register ? (
          <ShowcaseField
            autoComplete="name"
            label="Full name"
            onChangeText={setName}
            placeholder="Your name"
            value={name}
          />
        ) : null}
        <ShowcaseField
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          label="Email"
          onChangeText={setEmail}
          value={email}
        />
        <ShowcaseField
          autoComplete={register ? 'new-password' : 'current-password'}
          label="Password"
          onChangeText={setPassword}
          secureTextEntry
          value={password}
        />
        <ShowcaseButton
          disabled={invalid}
          label={register ? 'Create local demo' : 'Continue to demo'}
          onPress={() =>
            setMessage(
              register
                ? 'Demo profile created locally.'
                : 'Signed in to the local showcase.',
            )
          }
        />
        {message ? (
          <Text
            accessibilityLiveRegion="polite"
            style={[theme.typography.label, { color: theme.colors.positive }]}
          >
            {message}
          </Text>
        ) : null}
        <View style={styles.divider}>
          <View
            style={[styles.line, { backgroundColor: theme.colors.border }]}
          />
          <Text
            style={[theme.typography.label, { color: theme.colors.textMuted }]}
          >
            OR
          </Text>
          <View
            style={[styles.line, { backgroundColor: theme.colors.border }]}
          />
        </View>
        <ShowcaseButton
          disabled={!onSwitchMode}
          label={
            register ? 'I already have a demo profile' : 'Preview registration'
          }
          onPress={onSwitchMode ?? (() => undefined)}
          variant="secondary"
        />
      </GlassView>
    </ShowcasePage>
  );
}

export function ShowcaseLoginScreen({
  onOpenRegister,
  topInsetHandled,
}: {
  onOpenRegister?: () => void;
  topInsetHandled?: boolean;
}) {
  return (
    <AuthShell
      mode="login"
      onSwitchMode={onOpenRegister}
      topInsetHandled={topInsetHandled}
    />
  );
}
export function ShowcaseRegisterScreen({
  onOpenLogin,
  topInsetHandled,
}: {
  onOpenLogin?: () => void;
  topInsetHandled?: boolean;
}) {
  return (
    <AuthShell
      mode="register"
      onSwitchMode={onOpenLogin}
      topInsetHandled={topInsetHandled}
    />
  );
}

const styles = StyleSheet.create({
  form: { gap: 16, padding: 20 },
  divider: { alignItems: 'center', flexDirection: 'row', gap: 10 },
  line: { flex: 1, height: StyleSheet.hairlineWidth },
});
