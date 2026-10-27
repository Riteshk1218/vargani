import 'package:flutter/material.dart';

import '../util/money.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'expenses_screen.dart';
import 'followups_screen.dart';
import 'payments_screen.dart';
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
      load: () async {
        final d = ((await app.api.get('/collectors/me/dashboard/', query: {'event': app.eventId})) as Map)
            .cast<String, dynamic>();
        // Pavtis to visit (door-to-door follow-up): overdue and due today.
        if (app.can('payments.view')) {
          try {
            final summary = await app.api.get('/dashboard/summary/', query: {'event': app.eventId});
            d['follow_ups'] = (summary as Map)['follow_ups'];
          } catch (_) {}
        }
        return d;
      },
      builder: (context, d, reload) {
        final byMode = (d['by_mode'] as Map?)?.cast<String, dynamic>() ?? {};
        final recent = (d['recent_receipts'] as List? ?? []).cast<Map>();
        final canList = app.can('payments.view');
        // Each card opens "my payments" for its days.
        final now = DateTime.now();
        final today = isoDay(now);
        VoidCallback? mine(String title, {String? from, Map<String, String> extra = const {}}) => !canList
            ? null
            : () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => PaymentsListScreen(
                    title: title,
                    filters: {
                      if (d['collector'] != null) 'collector': '${d['collector']}',
                      'status': 'successful',
                      ...extra,
                    },
                    dateFrom: from,
                    dateTo: from == null ? null : today,
                  ),
                ),
              ).then((_) => reload());
        return ListView(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
          children: [
            if (d['follow_ups'] is Map) FollowUpCards(followUps: d['follow_ups'] as Map, onReturn: reload),
            DaySummaryCard(onReturn: reload),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.9,
              children: [
                StatCard(
                  key: const Key('card-today'),
                  label: app.t('today'),
                  amount: d['today']?.toString(),
                  highlight: true,
                  onTap: mine(app.t('today'), from: today),
                ),
                StatCard(
                  key: const Key('card-week'),
                  label: app.t('this_week'),
                  amount: d['this_week']?.toString(),
                  onTap: mine(app.t('this_week'), from: isoDay(now.subtract(const Duration(days: 6)))),
                ),
                StatCard(
                  key: const Key('card-month'),
                  label: app.t('this_month'),
                  amount: d['this_month']?.toString(),
                  onTap: mine(app.t('this_month'), from: isoDay(DateTime(now.year, now.month))),
                ),
                StatCard(
                  key: const Key('card-total'),
                  label: app.t('total'),
                  amount: d['total']?.toString(),
                  onTap: mine(app.t('total')),
                ),
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
                        onTap: e.key == 'other' ? null : mine(modeLabel(app, e.key), extra: {'mode': e.key}),
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

/// "Check a day": pick a date (today by default) and see what was collected, how many payments, how many
/// pavtis are fully paid and how much is still owed on that day. Every line opens its list.
class DaySummaryCard extends StatefulWidget {
  const DaySummaryCard({super.key, required this.onReturn});
  final VoidCallback onReturn;

  @override
  State<DaySummaryCard> createState() => _DaySummaryCardState();
}

class _DaySummaryCardState extends State<DaySummaryCard> {
  String _day = todayIso();

  Future<void> _pick() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.tryParse(_day) ?? now,
      firstDate: DateTime(now.year - 5),
      lastDate: DateTime(now.year + 1, 12, 31),
    );
    if (picked != null) setState(() => _day = isoDay(picked));
  }

  void _open(String title, Map<String, String> filters) => Navigator.push(
    context,
    MaterialPageRoute(
      builder: (_) => PaymentsListScreen(title: title, filters: filters, dateFrom: _day, dateTo: _day),
    ),
  ).then((_) => widget.onReturn());

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Card(
      child: AsyncView<Map<String, dynamic>>(
        reloadKey: '${app.eventId}-$_day',
        load: () async => ((await app.api.get(
          '/dashboard/summary/',
          query: {'event': app.eventId, 'date_from': _day, 'date_to': _day},
        )) as Map).cast<String, dynamic>(),
        builder: (context, s, _) {
          final financial = s['financial'] as Map?;
          final followUps = s['follow_ups'] as Map?;
          final canList = app.can('payments.view');
          final title = '${t('day_summary')} · ${formatDate(_day)}';
          Widget line(String key, String label, String value, {Map<String, String>? filters, VoidCallback? onTap}) =>
              ListTile(
                key: Key('day-$key'),
                dense: true,
                title: Text(label),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(value, style: Theme.of(context).textTheme.titleSmall),
                    if (onTap != null || (filters != null && canList)) const Icon(Icons.chevron_right, size: 18),
                  ],
                ),
                onTap:
                    onTap ?? (filters != null && canList ? () => _open('$label · ${formatDate(_day)}', filters) : null),
              );
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                key: const Key('day-pick'),
                leading: const Icon(Icons.calendar_month),
                title: Text(title, style: Theme.of(context).textTheme.titleMedium),
                subtitle: Text(t('day_summary_hint')),
                trailing: const Icon(Icons.edit_calendar),
                onTap: _pick,
              ),
              if (financial != null) ...[
                line(
                  'collected',
                  t('collected'),
                  formatInr('${financial['collected']}'),
                  filters: {'status': 'successful'},
                ),
                line('payments', t('payments'), '${financial['payments']}', filters: {}),
                line(
                  'expenses',
                  t('expenses'),
                  formatInr('${financial['expenses']}'),
                  onTap: app.can('expenses.view')
                      ? () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => Scaffold(
                              appBar: AppBar(title: Text('${t('expenses')} · ${formatDate(_day)}')),
                              body: ExpensesScreen(dateFrom: _day, dateTo: _day, status: 'approved'),
                            ),
                          ),
                        )
                      : null,
                ),
                line('balance', t('balance'), formatInr('${financial['balance']}')),
              ] else if (canList)
                line('payments', t('payments'), '', filters: {}),
              if (followUps != null) ...[
                line('paid', t('fully_paid'), '${followUps['paid'] ?? 0}', filters: {'pavti': 'paid'}),
                line(
                  'owing',
                  t('pavtis_owing'),
                  '${followUps['owing'] ?? 0} · ${formatInr('${followUps['balance'] ?? '0'}')}',
                  filters: {'pavti': 'owing'},
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
