import 'package:flutter/material.dart';

import '../widgets/common.dart';
import 'collect_screen.dart';
import 'collector_dashboard.dart';
import 'member_screens.dart';
import 'notifications_screen.dart';
import 'org_picker_screen.dart';
import 'people_screen.dart';
import 'receipts_screen.dart';
import 'settings_screen.dart';

class _Tab {
  const _Tab(this.icon, this.label, this.body);
  final IconData icon;
  final String label;
  final Widget body;
}

/// Bottom navigation; which tabs appear follows the permissions the API returned
/// for this organization. The API re-checks every call, so this is only for a clean UI.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  final _unread = ValueNotifier<int>(0);

  @override
  void initState() {
    super.initState();
    refreshUnread();
  }

  Future<void> refreshUnread() async {
    try {
      final r = await AppScope.read(context).api.get('/notifications/unread-count/');
      _unread.value = (r as Map)['unread'] as int? ?? 0;
    } catch (_) {
      // The badge is best-effort.
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final tabs = <_Tab>[
      if (app.isCollector) ...[
        _Tab(Icons.dashboard_outlined, app.t('home'), const CollectorDashboard()),
        _Tab(Icons.people_outline, app.t('people'), const PeopleScreen()),
        if (app.can('receipts.view')) _Tab(Icons.receipt_long_outlined, app.t('receipts'), const ReceiptsScreen()),
      ] else if (app.isMember) ...[
        _Tab(Icons.home_outlined, app.t('home'), const MemberHome()),
        _Tab(Icons.payments_outlined, app.t('my_payments'), const MemberPayments()),
        _Tab(Icons.receipt_long_outlined, app.t('receipts'), const MemberReceipts()),
      ],
      _Tab(Icons.notifications_outlined, app.t('alerts'), NotificationsScreen(onChanged: refreshUnread)),
      _Tab(Icons.settings_outlined, app.t('settings'), const SettingsScreen()),
    ];
    if (_index >= tabs.length) _index = 0;
    final alertsIndex = tabs.length - 2;

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 12,
        title: InkWell(
          onTap: app.organizations.length > 1 ? () => _switchOrg(context) : null,
          child: Row(children: [
            OrgAvatar(name: app.orgName, logoUrl: app.logoUrl, radius: 16),
            const SizedBox(width: 10),
            Flexible(child: Text(app.orgName, overflow: TextOverflow.ellipsis)),
            if (app.organizations.length > 1) const Icon(Icons.arrow_drop_down),
          ]),
        ),
        actions: [
          const EventSwitcher(),
          ValueListenableBuilder<int>(
            valueListenable: _unread,
            builder: (_, n, _) => IconButton(
              tooltip: app.t('alerts'),
              icon: Badge(isLabelVisible: n > 0, label: Text('$n'), child: const Icon(Icons.notifications_none)),
              onPressed: () => setState(() => _index = alertsIndex),
            ),
          ),
        ],
      ),
      body: KeyedSubtree(key: ValueKey('${app.eventId}-$_index'), child: tabs[_index].body),
      floatingActionButton: app.isCollector && app.eventId != null && _index < 2
          ? FloatingActionButton.extended(
              key: const Key('fab-collect'),
              icon: const Icon(Icons.add),
              label: Text(app.t('collect')),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CollectScreen())),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final t in tabs) NavigationDestination(icon: Icon(t.icon), label: t.label),
        ],
      ),
    );
  }

  Future<void> _switchOrg(BuildContext context) async {
    final app = AppScope.read(context);
    final id = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(shrinkWrap: true, children: [
          ListTile(title: Text(app.t('choose_org'), style: Theme.of(ctx).textTheme.titleMedium)),
          for (final o in app.organizations)
            ListTile(
              leading: OrgAvatar(name: '${o['name']}', logoUrl: o['logo_url'] as String?),
              title: Text('${o['name']}'),
              subtitle: Text('${(o['role'] as Map?)?['name'] ?? ''}'),
              selected: o['id'] == app.orgId,
              onTap: () => Navigator.pop(ctx, o['id'] as String),
            ),
        ]),
      ),
    );
    if (id == null || id == app.orgId) return;
    try {
      await app.selectOrganization(id);
    } catch (e) {
      if (context.mounted) showMessage(context, errorText(context, e), error: true);
    }
  }
}
