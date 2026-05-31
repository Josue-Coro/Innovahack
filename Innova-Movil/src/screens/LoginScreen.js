import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  ActivityIndicator,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  useWindowDimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import api from '../services/apiClient';
import { useAuthStore } from '../services/authStore';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';
import { colors } from '../constants/theme';

const REMEMBER_KEY = 'camporuta.rememberEmail';

function InputRow({
  label,
  icon,
  value,
  onChangeText,
  placeholder,
  secureTextEntry,
  keyboardType,
  autoCapitalize,
  showToggle,
  onToggleSecure,
  valid,
}) {
  return (
    <View style={styles.fieldBlock}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={[styles.inputRow, valid && styles.inputRowValid]}>
        <Ionicons name={icon} size={18} color={colors.goldDark} style={styles.inputIcon} />
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor="#9CA3AF"
          secureTextEntry={secureTextEntry}
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          autoCorrect={false}
          style={styles.input}
        />
        <View style={styles.inputTrailing}>
          {valid ? <Ionicons name="checkmark-circle" size={18} color={colors.success} /> : null}
          {showToggle ? (
            <Pressable onPress={onToggleSecure} hitSlop={8}>
              <Ionicons
                name={secureTextEntry ? 'eye-off-outline' : 'eye-outline'}
                size={18}
                color={colors.textMuted}
              />
            </Pressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const loginSuccess = useAuthStore((s) => s.loginSuccess);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    AsyncStorage.getItem(REMEMBER_KEY).then((saved) => {
      if (saved) {
        setEmail(saved);
        setRemember(true);
      }
    });
  }, []);

  const emailValid = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()), [email]);
  const passwordValid = useMemo(() => password.length >= 4, [password]);
  const canSubmit = useMemo(() => emailValid && passwordValid, [emailValid, passwordValid]);

  async function onSubmit() {
    if (!canSubmit || loading) return;
    setLoading(true);
    setError(null);

    try {
      const res = await api.post(endpoints.login, {
        email: email.trim(),
        password,
      });

      const token = res?.data?.token;
      const usuario = res?.data?.usuario;
      const rol = res?.data?.rol;

      if (!token || !usuario) {
        throw new Error('Respuesta de login incompleta');
      }

      if (rol !== 'reponedor') {
        setError('Esta app es solo para reponedores.');
        return;
      }

      if (remember) {
        await AsyncStorage.setItem(REMEMBER_KEY, email.trim());
      } else {
        await AsyncStorage.removeItem(REMEMBER_KEY);
      }

      await loginSuccess({ token, usuario, rol });
    } catch (e) {
      setError(getApiError(e, 'Error al iniciar sesión'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <LinearGradient
      colors={['#1E1E24', '#2D2D35', '#1a1a20']}
      style={styles.root}
    >
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={[styles.scrollContainer, { paddingTop: insets.top, paddingBottom: insets.bottom }]}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.formCard}>
            <View style={styles.goldTopBar} />

            <View style={styles.badge}>
              <Ionicons name="map-outline" size={13} color={colors.goldDark} />
              <Text style={styles.badgeText}>PORTAL DE MONITOREO GPS</Text>
            </View>

            <Text style={styles.formTitle}>Iniciar Sesión</Text>
            <Text style={styles.formSubtitle}>
              Bienvenido al panel logístico. Ingresa tus credenciales corporativas.
            </Text>

            <InputRow
              label="Correo Electrónico"
              icon="mail-outline"
              value={email}
              onChangeText={setEmail}
              placeholder="correo@empresa.com"
              keyboardType="email-address"
              autoCapitalize="none"
              valid={emailValid}
            />

            <InputRow
              label="Contraseña"
              icon="lock-closed-outline"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry={!showPassword}
              valid={passwordValid}
              showToggle
              onToggleSecure={() => setShowPassword((v) => !v)}
            />

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={styles.optionsRow}>
              <Pressable style={styles.rememberRow} onPress={() => setRemember((v) => !v)}>
                <View style={[styles.checkbox, remember && styles.checkboxChecked]}>
                  {remember ? <Ionicons name="checkmark" size={12} color="#fff" /> : null}
                </View>
                <Text style={styles.rememberText}>Recordar sesión</Text>
              </Pressable>
              <Pressable>
                <Text style={styles.forgotText}>¿Recuperar contraseña?</Text>
              </Pressable>
            </View>

            <Pressable
              style={[styles.submitBtn, (!canSubmit || loading) && styles.submitBtnDisabled]}
              onPress={onSubmit}
              disabled={!canSubmit || loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <View style={styles.submitInner}>
                  <Text style={styles.submitText}>Ingresar al Sistema</Text>
                  <Ionicons name="arrow-forward" size={18} color="#fff" />
                </View>
              )}
            </Pressable>

            <Text style={styles.footer}>Soporte TI: soporte@grupovenado.com · Términos de Uso</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 40,
  },
  formCard: {
    backgroundColor: colors.white,
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingBottom: 24,
    paddingTop: 10,
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 10,
    width: '100%',
    maxWidth: 420,
    overflow: 'hidden',
  },
  goldTopBar: {
    height: 5,
    backgroundColor: colors.gold,
    marginHorizontal: -24,
    marginBottom: 20,
  },
  badge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.goldLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 16,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    color: colors.goldDark,
  },
  formTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: colors.textDark,
    marginBottom: 8,
  },
  formSubtitle: {
    fontSize: 14,
    lineHeight: 20,
    color: colors.textMuted,
    marginBottom: 24,
  },
  fieldBlock: { marginBottom: 16 },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.goldDark,
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.inputBg,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: colors.border,
    paddingHorizontal: 14,
    minHeight: 52,
  },
  inputRowValid: { borderColor: colors.gold },
  inputIcon: { marginRight: 8 },
  input: {
    flex: 1,
    fontSize: 15,
    color: colors.textDark,
    paddingVertical: 12,
  },
  inputTrailing: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  optionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
    flexWrap: 'wrap',
    gap: 10,
  },
  rememberRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: colors.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: {
    backgroundColor: colors.gold,
    borderColor: colors.gold,
  },
  rememberText: { fontSize: 13, color: colors.textDark, fontWeight: '500' },
  forgotText: { fontSize: 13, color: colors.goldDark, fontWeight: '700' },
  submitBtn: {
    backgroundColor: colors.gold,
    borderRadius: 12,
    minHeight: 54,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    shadowColor: colors.gold,
    shadowOpacity: 0.3,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  submitBtnDisabled: { opacity: 0.55 },
  submitInner: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  submitText: { color: '#fff', fontSize: 16, fontWeight: '800', letterSpacing: 0.5 },
  errorText: {
    color: colors.error,
    fontWeight: '600',
    fontSize: 13,
    marginBottom: 16,
    textAlign: 'center',
  },
  footer: {
    textAlign: 'center',
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 16,
    fontWeight: '500',
  },
});
