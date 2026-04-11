import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import LoginScreen from './src/screens/LoginScreen';
import ChamadosScreen from './src/screens/ChamadosScreen';
import AtendimentoScreen from './src/screens/AtendimentoScreen';
import { RootStackParamList } from './src/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <>
      <StatusBar style="light" />
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Chamados" component={ChamadosScreen} />
          <Stack.Screen name="Atendimento" component={AtendimentoScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </>
  );
}
