import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, Switch } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '../services/authStore';

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const isDarkMode = useAuthStore((s) => s.isDarkMode);

  // Fake states for demo purposes
  const [notif, setNotif] = useState(true);
  const [sync, setSync] = useState(false);

  const themeColors = {
    background: isDarkMode ? '#0F1115' : '#F3F4F6',
    card: isDarkMode ? '#1F2937' : '#FFFFFF',
    textPrimary: isDarkMode ? '#F9FAFB' : '#111827',
    textSecondary: isDarkMode ? '#9CA3AF' : '#6B7280',
    border: isDarkMode ? '#374151' : '#E5E7EB',
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top, backgroundColor: themeColors.background }]}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color={themeColors.textPrimary} />
        </Pressable>
        <Text style={[styles.headerTitle, { color: themeColors.textPrimary }]}>Ajustes</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.content}>
        <View style={[styles.section, { backgroundColor: themeColors.card, borderColor: themeColors.border }]}>
          <View style={[styles.row, { borderBottomColor: themeColors.border, borderBottomWidth: 1 }]}>
            <View style={styles.rowLeft}>
              <Ionicons name="notifications-outline" size={22} color={themeColors.textPrimary} />
              <Text style={[styles.rowText, { color: themeColors.textPrimary }]}>Notificaciones Push</Text>
            </View>
            <Switch value={notif} onValueChange={setNotif} trackColor={{ true: '#3B82F6' }} />
          </View>

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="cloud-offline-outline" size={22} color={themeColors.textPrimary} />
              <Text style={[styles.rowText, { color: themeColors.textPrimary }]}>Sincronización Offline</Text>
            </View>
            <Switch value={sync} onValueChange={setSync} trackColor={{ true: '#3B82F6' }} />
          </View>
        </View>
        <Text style={[styles.hint, { color: themeColors.textSecondary }]}>La sincronización offline consumirá más espacio en el dispositivo.</Text>
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
  content: { flex: 1, padding: 20 },
  section: {
    width: '100%',
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  rowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rowText: {
    fontSize: 16,
    marginLeft: 12,
    fontWeight: '500',
  },
  hint: {
    fontSize: 13,
    marginTop: 12,
    paddingHorizontal: 8,
  }
});
