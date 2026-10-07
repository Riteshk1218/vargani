import 'package:flutter/material.dart';

import 'api/api_client.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'screens/org_picker_screen.dart';
import 'state/app_state.dart';
import 'widgets/common.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final state = AppState(api: ApiClient(baseUrl: initialApiBase(), tokens: SecureTokenStore()));
  runApp(VarganiApp(state: state));
  state.load();
}

class VarganiApp extends StatelessWidget {
  const VarganiApp({super.key, required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return AppScope(
      state: state,
      child: Builder(builder: (context) {
        final app = AppScope.of(context);
        return MaterialApp(
          title: app.t('app_name'),
          debugShowCheckedModeBanner: false,
          theme: ThemeData(colorSchemeSeed: const Color(0xFFE65100), useMaterial3: true),
          darkTheme: ThemeData(
              colorSchemeSeed: const Color(0xFFE65100), brightness: Brightness.dark, useMaterial3: true),
          home: const _Root(),
        );
      }),
    );
  }
}

class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (!app.ready) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (!app.loggedIn) return const LoginScreen();
    if (app.orgDetail == null) return const OrgPickerScreen();
    // Key on org so every screen reloads when the organization changes.
    return HomeShell(key: ValueKey(app.orgId));
  }
}
