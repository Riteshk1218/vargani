import 'package:flutter/material.dart';

import '../l10n/strings.dart';
import '../util/theme.dart';
import '../widgets/common.dart';
import 'users_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final scheme = Theme.of(context).colorScheme;
    final name = '${app.user?['full_name'] ?? ''}';
    Future<void> save(Future<void> Function() action) async {
      try {
        await action();
        if (context.mounted) showMessage(context, t('color_saved'));
      } catch (e) {
        if (context.mounted) showMessage(context, errorText(context, e), error: true);
      }
    }

    return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
      Container(
        margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(colors: [scheme.primary, Color.lerp(scheme.primary, Colors.black, 0.3)!]),
          boxShadow: [BoxShadow(color: scheme.primary.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Row(children: [
          CircleAvatar(
            radius: 26,
            backgroundColor: scheme.onPrimary.withValues(alpha: 0.2),
            child: Text(
              name.isEmpty ? '?' : name.characters.first.toUpperCase(),
              style: TextStyle(color: scheme.onPrimary, fontSize: 22, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, style: TextStyle(color: scheme.onPrimary, fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(
                [app.user?['username'], app.user?['email'], app.user?['mobile']].where((x) => x != null).join(' · '),
                style: TextStyle(color: scheme.onPrimary.withValues(alpha: 0.85)),
              ),
            ]),
          ),
        ]),
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
        leading: const Icon(Icons.palette_outlined),
        title: Text(t('my_color')),
        subtitle: Text(t('my_color_help')),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        child: ThemeSwatches(
          value: app.userThemeColor,
          orgColor: app.orgThemeColor,
          orgLabel: t('color_org'),
          label: (c) => t('color_$c'),
          onChanged: (c) => save(() => app.setThemeColor(c)),
        ),
      ),
      if (app.can('organization.manage')) ...[
        ListTile(
          leading: const Icon(Icons.format_paint_outlined),
          title: Text(t('org_color')),
          subtitle: Text(t('org_color_help')),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
          child: ThemeSwatches(
            key: const Key('org-theme'),
            value: app.orgThemeColor,
            label: (c) => t('color_$c'),
            onChanged: (c) => save(() => app.setOrgThemeColor(c)),
          ),
        ),
      ],
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
