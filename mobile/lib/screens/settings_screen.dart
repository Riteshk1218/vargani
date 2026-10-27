import 'package:flutter/material.dart';

import '../l10n/strings.dart';
import '../widgets/common.dart';
import 'users_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return ListView(children: [
      ListTile(
        leading: const Icon(Icons.account_circle_outlined),
        title: Text('${app.user?['full_name'] ?? ''}'),
        subtitle: Text(
          [app.user?['username'], app.user?['email'], app.user?['mobile']].where((x) => x != null).join(' · '),
        ),
      ),
      ListTile(
        leading: const Icon(Icons.groups_outlined),
        title: Text(t('organization')),
        subtitle: Text('${app.orgName} · ${(app.orgDetail?['role'] as Map?)?['name'] ?? ''}'),
      ),
      ListTile(
        leading: const Icon(Icons.event_outlined),
        title: Text(t('event')),
        subtitle: Text('${app.event?['name'] ?? t('no_events')}'),
      ),
      if (app.can('members.manage'))
        ListTile(
          key: const Key('manage-users'),
          leading: const Icon(Icons.manage_accounts_outlined),
          title: Text(t('users')),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const UsersScreen())),
        ),
      const Divider(),
      ListTile(leading: const Icon(Icons.translate), title: Text(t('language'))),
      RadioGroup<String>(
        groupValue: app.language,
        onChanged: (v) => v == null ? null : app.setLanguage(v),
        child: Column(children: [
          for (final e in supportedLanguages.entries)
            RadioListTile<String>(key: Key('lang-${e.key}'), value: e.key, title: Text(e.value)),
        ]),
      ),
      const Divider(),
      ListTile(
        leading: const Icon(Icons.dns_outlined),
        title: Text(t('server')),
        subtitle: Text(app.api.baseUrl),
      ),
      ListTile(
        key: const Key('logout'),
        leading: Icon(Icons.logout, color: Theme.of(context).colorScheme.error),
        title: Text(t('logout')),
        onTap: app.logout,
      ),
      ListTile(dense: true, title: Text('${t('version')} 1.0.0')),
    ]);
  }
}
