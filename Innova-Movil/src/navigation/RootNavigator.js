import React from 'react';
import { Pressable, Text } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '../services/authStore';

import LoginScreen from '../screens/LoginScreen';
import HomeRouteScreen from '../screens/HomeRouteScreen';
import VisitExecutionScreen from '../screens/VisitExecutionScreen';

const Stack = createNativeStackNavigator();

function LogoutButton() {
  const logout = useAuthStore((s) => s.logout);
  return (
    <Pressable onPress={logout} style={{ marginRight: 8 }}>
      <Text style={{ color: '#DC2626', fontWeight: '700' }}>Salir</Text>
    </Pressable>
  );
}

export default function RootNavigator() {
  const token = useAuthStore((s) => s.token);
  const hydrate = useAuthStore((s) => s.hydrate);
  const isHydrated = useAuthStore((s) => s.isHydrated);

  React.useEffect(() => {
    hydrate();
  }, [hydrate]);

  if (!isHydrated) {
    return null;
  }

  return (
    <Stack.Navigator>
      {token ? (
        <>
          <Stack.Screen
            name="Home"
            component={HomeRouteScreen}
            options={{
              title: 'Mi Ruta',
              headerRight: () => <LogoutButton />,
            }}
          />
          <Stack.Screen
            name="VisitExecution"
            component={VisitExecutionScreen}
            options={{ title: 'Visita' }}
          />
        </>
      ) : (
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />
      )}
    </Stack.Navigator>
  );
}
