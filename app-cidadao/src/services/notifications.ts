import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { salvarPushToken } from './api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function registrarPushToken(userId: number): Promise<string | null> {
  if (Platform.OS === 'web') {
    return null;
  }

  if (!Device.isDevice) {
    console.log('Push notifications requerem dispositivo fisico');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  const tokenData = await Notifications.getExpoPushTokenAsync({
    projectId: undefined, // usa o projectId do app.json
  });
  const token = tokenData.data;

  // Salvar no backend
  try {
    await salvarPushToken(userId, token);
  } catch {}

  // Android: canal de alta prioridade
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('emergencias', {
      name: 'Emergencias',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      sound: 'default',
    });
  }

  return token;
}
