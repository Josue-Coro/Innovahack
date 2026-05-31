import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../services/authStore';

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const usuario = useAuthStore((s) => s.usuario);
  const isDarkMode = useAuthStore((s) => s.isDarkMode);

  const themeColors = {
    background: isDarkMode ? '#0F1115' : '#F3F4F6',
    card: isDarkMode ? '#1F2937' : '#FFFFFF',
    textPrimary: isDarkMode ? '#F9FAFB' : '#111827',
    textSecondary: isDarkMode ? '#9CA3AF' : '#6B7280',
    iconColor: isDarkMode ? '#3B82F6' : '#2563EB',
  };

  const initials = usuario?.nombre ? usuario.nombre.substring(0, 2).toUpperCase() : 'AV';

  return (
    <View style={[styles.container, { paddingTop: insets.top, backgroundColor: themeColors.background }]}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color={themeColors.textPrimary} />
        </Pressable>
        <Text style={[styles.headerTitle, { color: themeColors.textPrimary }]}>Mi Perfil</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.content}>
        <View style={[styles.card, { backgroundColor: themeColors.card }]}>
          <View style={[styles.avatarContainer, { borderColor: themeColors.iconColor }]}>
            <Text style={[styles.avatarText, { color: themeColors.iconColor }]}>{initials}</Text>
          </View>
          
          <Text style={[styles.nameText, { color: themeColors.textPrimary }]}>{usuario?.nombre || 'Usuario'}</Text>
          <Text style={[styles.roleText, { color: themeColors.textSecondary }]}>{usuario?.rol || 'Reponedor'}</Text>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <Ionicons name="mail-outline" size={20} color={themeColors.textSecondary} />
            <Text style={[styles.infoText, { color: themeColors.textPrimary }]}>{usuario?.email || 'No especificado'}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Ionicons name="call-outline" size={20} color={themeColors.textSecondary} />
            <Text style={[styles.infoText, { color: themeColors.textPrimary }]}>{usuario?.telefono || '+591 00000000'}</Text>
          </View>

          <View style={styles.infoRow}>
            <Ionicons name="business-outline" size={20} color={themeColors.textSecondary} />
            <Text style={[styles.infoText, { color: themeColors.textPrimary }]}>Innovahack 2026</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  backBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(156, 163, 175, 0.1)',
  },
  headerTitle: { fontSize: 20, fontWeight: '700' },
  content: { flex: 1, padding: 20, alignItems: 'center' },
  card: {
    width: '100%',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  avatarContainer: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  avatarText: { fontSize: 32, fontWeight: 'bold' },
  nameText: { fontSize: 24, fontWeight: 'bold', marginBottom: 4 },
  roleText: { fontSize: 16, textTransform: 'capitalize', marginBottom: 24 },
  divider: {
    height: 1,
    width: '100%',
    backgroundColor: 'rgba(156, 163, 175, 0.2)',
    marginBottom: 24,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    marginBottom: 16,
  },
  infoText: { fontSize: 16, marginLeft: 12 },
});
