import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'receipt_screen.dart';

/// In-app notifications. Titles and bodies arrive already in the user's language.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, this.onChanged});
  final VoidCallback? onChanged;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  int _version = 0;

  Future<void> _markRead(Map<String, dynamic> n) async {
    if (n['read_at'] != null) return;
    try {
      await AppScope.read(context).api.post('/notifications/${n['id']}/read/');
      widget.onChanged?.call();
      setState(() => _version++);
    } catch (_) {}
  }

  void _open(Map<String, dynamic> n) {
    _markRead(n);
    final link = '${n['link'] ?? ''}';
    final m = RegExp(r'^/app/receipts/([0-9a-f-]{36})').firstMatch(link);
    if (m != null) {
      final app = AppScope.read(context);
      Navigator.push(context,
          MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: m.group(1)!, portal: !app.isCollector)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AsyncView<List<Map<String, dynamic>>>(
      reloadKey: _version,
      load: () async => resultsOf(await app.api.get('/notifications/')),
      builder: (context, items, reload) {
        if (items.isEmpty) return EmptyState(icon: Icons.notifications_none, text: app.t('no_alerts'));
        return ListView(children: [
          if (items.any((n) => n['read_at'] == null))
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () async {
                  try {
                    await app.api.post('/notifications/read-all/');
                    widget.onChanged?.call();
                    setState(() => _version++);
                  } catch (e) {
                    if (context.mounted) showMessage(context, errorText(context, e), error: true);
                  }
                },
                child: Text(app.t('mark_all_read')),
              ),
            ),
          for (final n in items)
            ListTile(
              leading: Icon(n['read_at'] == null ? Icons.circle : Icons.circle_outlined,
                  size: 12, color: Theme.of(context).colorScheme.primary),
              title: Text('${n['title'] ?? ''}',
                  style: n['read_at'] == null ? const TextStyle(fontWeight: FontWeight.w600) : null),
              subtitle: Text([
                '${n['body'] ?? ''}',
                [n['organization_name'], formatDate('${n['created_at']}', withTime: true)]
                    .where((x) => x != null && '$x'.isNotEmpty)
                    .join(' · '),
              ].where((x) => x.isNotEmpty).join('\n')),
              isThreeLine: '${n['body'] ?? ''}'.isNotEmpty,
              onTap: () => _open(n),
            ),
        ]);
      },
    );
  }
}
