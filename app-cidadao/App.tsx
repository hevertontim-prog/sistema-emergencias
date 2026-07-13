import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from './src/theme';
import { RootStackParamList } from './src/navigation';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import AcompanhamentoScreen from './src/screens/AcompanhamentoScreen';
import ErrorBoundary from './src/ErrorBoundary';

const Stack = createNativeStackNavigator<RootStackParamList>();

const DarkNavTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.background,
    card: colors.surface,
    text: colors.text,
    border: colors.border,
    primary: colors.primary,
  },
};

export default function App() {
  return (
    <ErrorBoundary>
      <NavigationContainer theme={DarkNavTheme}>
        <StatusBar style="light" />
        <Stack.Navigator
          initialRouteName="Login"
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
            animation: 'slide_from_right',
          }}
        >
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="Acompanhamento" component={AcompanhamentoScreen} options={{ headerShown: false }} />
        </Stack.Navigator>
      </NavigationContainer>
    </ErrorBoundary>
  );
}
