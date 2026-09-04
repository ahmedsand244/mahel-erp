import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SecureStorageService {
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  static FlutterSecureStorage get secureStorage => _secureStorage;

  static SharedPreferences? _prefs;

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  // Secure Storage (Encrypted) - for tokens, passwords, sensitive data
  static Future<void> writeSecure(String key, String value) async {
    await _secureStorage.write(key: key, value: value);
  }

  static Future<String?> readSecure(String key) async {
    return _secureStorage.read(key: key);
  }

  static Future<void> deleteSecure(String key) async {
    await _secureStorage.delete(key: key);
  }

  static Future<void> clearAllSecure() async {
    await _secureStorage.deleteAll();
  }

  // SharedPreferences (Non-encrypted) - for settings, preferences, cached data
  static Future<void> write(String key, String value) async {
    await _prefs?.setString(key, value);
  }

  static String? read(String key) {
    return _prefs?.getString(key);
  }

  static Future<void> writeBool(String key, bool value) async {
    await _prefs?.setBool(key, value);
  }

  static bool readBool(String key, {bool defaultValue = false}) {
    return _prefs?.getBool(key) ?? defaultValue;
  }

  static Future<void> writeInt(String key, int value) async {
    await _prefs?.setInt(key, value);
  }

  static int readInt(String key, {int defaultValue = 0}) {
    return _prefs?.getInt(key) ?? defaultValue;
  }

  static Future<void> writeDouble(String key, double value) async {
    await _prefs?.setDouble(key, value);
  }

  static double readDouble(String key, {double defaultValue = 0.0}) {
    return _prefs?.getDouble(key) ?? defaultValue;
  }

  static Future<void> writeStringList(String key, List<String> value) async {
    await _prefs?.setStringList(key, value);
  }

  static List<String>? readStringList(String key) {
    return _prefs?.getStringList(key);
  }

  static Future<void> delete(String key) async {
    await _prefs?.remove(key);
  }

  static Future<void> clearAll() async {
    await _prefs?.clear();
  }

  // Convenience methods for app-specific keys
  static const String _keyTheme = 'theme_mode';
  static const String _keyFontScale = 'font_scale';
  static const String _keyLanguage = 'language';
  static const String _keyLastSync = 'last_sync_timestamp';
  static const String _keyBiometricEnabled = 'biometric_enabled';
  static const String _keyPinCode = 'pin_code';

  static Future<void> setThemeMode(String mode) async => write(_keyTheme, mode);
  static String getThemeMode() => read(_keyTheme) ?? 'dark';

  static Future<void> setFontScale(String scale) async => write(_keyFontScale, scale);
  static String getFontScale() => read(_keyFontScale) ?? 'sm';

  static Future<void> setLanguage(String lang) async => write(_keyLanguage, lang);
  static String getLanguage() => read(_keyLanguage) ?? 'ar';

  static Future<void> setLastSync(DateTime time) async => write(_keyLastSync, time.toIso8601String());
  static DateTime? getLastSync() {
    final str = read(_keyLastSync);
    return str != null ? DateTime.tryParse(str) : null;
  }

  static Future<void> setBiometricEnabled(bool enabled) async => writeBool(_keyBiometricEnabled, enabled);
  static bool getBiometricEnabled() => readBool(_keyBiometricEnabled);

  static Future<void> setPinCode(String pin) async => writeSecure(_keyPinCode, pin);
  static Future<String?> getPinCode() async => readSecure(_keyPinCode);
  static Future<void> clearPinCode() async => deleteSecure(_keyPinCode);
}