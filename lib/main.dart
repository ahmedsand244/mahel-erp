import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MahelPosApp());
}

class MahelPosApp extends StatelessWidget {
  const MahelPosApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'النماء POS & ERP',
      debugShowCheckedModeBanner: false,
      locale: const Locale('ar', 'EG'),
      supportedLocales: const [Locale('ar', 'EG')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D1117),
        primaryColor: const Color(0xFF2F81F7),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF2F81F7),
          secondary: Color(0xFF10B981),
          surface: Color(0xFF161B22),
        ),
        fontFamily: 'Cairo',
      ),
      home: const LoginScreen(),
    );
  }
}
