import 'package:flutter/material.dart';

import '../util/money.dart';
import '../widgets/common.dart';
import 'receipt_screen.dart';
import 'summary_screen.dart';

class CollectorDashboard extends StatelessWidget {
  const CollectorDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (app.eventId == null) return EmptyState(icon: Icons.event_busy, text: app.t('no_events'));
    return AsyncView<Map<String, dynamic>>(
      reloadKey: app.eventId,
      load: () async => ((await app.api.get('/collectors/me/dashboard/', query: {'event': app.eventId})) as Map)
          .cast<String, dynamic>(),
      builder: (context, d, reload) {
        final byMode = (d['by_mode'] as Map?)?.cast<String, dynamic>() ?? {};
        final recent = (d['recent_receipts'] as List? ?? []).cast<Map>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
          children: [
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.9,
              children: [
                StatCard(label: app.t('today'), amount: d['today']?.toString(), highlight: true),
                StatCard(label: app.t('this_week'), amount: d['this_week']?.toString()),
                StatCard(label: app.t('this_month'), amount: d['this_month']?.toString()),
                StatCard(label: app.t('total'), amount: d['total']?.toString()),
              ],
            ),
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Column(
                  children: [
                    for (final e in byMode.entries)
                      ListTile(
                        dense: true,
                        title: Text(modeLabel(app, e.key)),
                        trailing: Text(formatInr('${e.value}')),
                      ),
                    ListTile(
                      dense: true,
                      title: Text(app.t('assigned_people')),
                      trailing: Text('${d['assigned'] ?? 0}'),
                    ),
                    ListTile(
                      dense: true,
                      title: Text(app.t('paid_this_month')),
                      trailing: Text('${d['paid_this_month'] ?? 0}'),
                    ),
                  ],
                ),
              ),
            ),
            if (app.can('dashboard.view_financial'))
              Card(
                child: ListTile(
                  key: const Key('open-summary'),
                  leading: const Icon(Icons.balance),
                  title: Text(app.t('financial_summary')),
                  subtitle: Text(app.t('summary_hint')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SummaryScreen())),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
              child: Text(app.t('recent_receipts'), style: Theme.of(context).textTheme.titleMedium),
            ),
            if (recent.isEmpty)
              Padding(padding: const EdgeInsets.all(16), child: Text(app.t('no_receipts')))
            else
              for (final r in recent)
                Card(
                  child: ListTile(
                    title: Text('${r['payer_name']}'),
                    subtitle: Text(
                      '${r['receipt_number']} · ${formatStamp((r['paid_at'] ?? r['issued_at'])?.toString())}',
                    ),
                    trailing: Text(formatInr('${r['amount']}'), style: Theme.of(context).textTheme.titleSmall),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${r['id']}')),
                    ).then((_) => reload()),
                  ),
                ),
          ],
        );
      },
    );
  }
}
