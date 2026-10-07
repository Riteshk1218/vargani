import 'package:flutter/material.dart';

import '../widgets/common.dart';

class OrgPickerScreen extends StatelessWidget {
  const OrgPickerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(app.t('choose_org')),
        actions: [IconButton(icon: const Icon(Icons.logout), tooltip: app.t('logout'), onPressed: app.logout)],
      ),
      body: app.organizations.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(app.t('not_linked'), textAlign: TextAlign.center),
              ),
            )
          : ListView(children: [
              for (final o in app.organizations)
                ListTile(
                  leading: OrgAvatar(name: '${o['name']}', logoUrl: o['logo_url'] as String?),
                  title: Text('${o['name']}'),
                  subtitle: Text('${(o['role'] as Map?)?['name'] ?? ''}'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    try {
                      await app.selectOrganization(o['id'] as String);
                    } catch (e) {
                      if (context.mounted) showMessage(context, errorText(context, e), error: true);
                    }
                  },
                ),
            ]),
    );
  }
}

class OrgAvatar extends StatelessWidget {
  const OrgAvatar({super.key, required this.name, this.logoUrl, this.radius = 20});
  final String name;
  final String? logoUrl;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final initial = name.isEmpty ? '?' : name.characters.first;
    return CircleAvatar(
      radius: radius,
      foregroundImage: logoUrl != null && logoUrl!.isNotEmpty ? NetworkImage(logoUrl!) : null,
      child: Text(initial),
    );
  }
}
