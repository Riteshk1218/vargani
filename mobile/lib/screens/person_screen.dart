import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'collect_screen.dart';
import 'followups_screen.dart';
import 'receipt_screen.dart';

/// One person: contact details and every pavti they gave, across events and years, newest first.
class PersonScreen extends StatefulWidget {
  const PersonScreen({super.key, required this.person});
  final Map<String, dynamic> person;

  @override
  State<PersonScreen> createState() => _PersonScreenState();
}

class _PersonScreenState extends State<PersonScreen> {
  String? _event; // null: all events
  int _version = 0; // bumped after a collection so the history reloads

  Future<List<Map<String, dynamic>>> _history() async {
    final api = AppScope.read(context).api;
    final found = <Map<String, dynamic>>[];
    for (var page = 1; page <= 20; page++) {
      final data = await api.get(
        '/payments/',
        query: {'payer': '${widget.person['id']}', 'ordering': '-paid_at', 'page': '$page', 'page_size': '100'},
      );
      found.addAll(resultsOf(data));
      if (data is! Map || data['next'] == null) break;
    }
    return found;
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final p = widget.person;
    final address = [
      p['unit'],
      p['building'],
      p['area'],
      p['address_line'],
      p['city'],
    ].where((s) => s != null && '$s'.isNotEmpty).join(', ');
    return Scaffold(
      appBar: AppBar(title: Text('${p['full_name']}')),
      floatingActionButton: app.can('payments.create') && app.eventId != null
          ? FloatingActionButton.extended(
              key: const Key('person-collect'),
              icon: const Icon(Icons.currency_rupee),
              label: Text(t('collect')),
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => CollectScreen(person: p)),
              ).then((_) => setState(() => _version++)),
            )
          : null,
      body: AsyncView<List<Map<String, dynamic>>>(
        reloadKey: _version,
        load: _history,
        builder: (context, all, reload) {
          final events = <String, String>{for (final x in all) '${x['event']}': '${x['event_name']}'};
          final shown = all.where((x) => _event == null || '${x['event']}' == _event).toList();
          final received = shown.where((x) => x['status'] == 'successful').toList();
          int sum(String field) => received.fold(0, (s, x) => s + _paise('${x[field] ?? '0'}'));
          return ListView(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
            children: [
              Card(
                child: ListTile(
                  leading: CircleAvatar(child: Text('${p['full_name']}'.characters.first)),
                  title: Text('${p['full_name']}'),
                  subtitle: Text([p['mobile'], address].where((s) => s != null && '$s'.isNotEmpty).join('\n')),
                ),
              ),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.9,
                children: [
                  StatCard(label: t('total_paid'), amount: _fromPaise(sum('amount')), highlight: true),
                  StatCard(label: t('history_still_owed'), amount: _fromPaise(sum('balance_due'))),
                  _CountCard(label: t('pavtis'), value: '${received.length}'),
                  _CountCard(
                    label: t('last_paid'),
                    value: received.isEmpty ? '—' : formatDate('${received.first['paid_at']}'),
                  ),
                ],
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
                child: Row(
                  children: [
                    Expanded(child: Text(t('history_title'), style: Theme.of(context).textTheme.titleMedium)),
                    if (events.length > 1)
                      DropdownButton<String?>(
                        key: const Key('history-event'),
                        value: _event,
                        items: [
                          DropdownMenuItem(value: null, child: Text(t('all_events'))),
                          for (final e in events.entries) DropdownMenuItem(value: e.key, child: Text(e.value)),
                        ],
                        onChanged: (v) => setState(() => _event = v),
                      ),
                  ],
                ),
              ),
              if (shown.isEmpty)
                Padding(padding: const EdgeInsets.all(16), child: Text(t('no_contributions')))
              else
                for (final x in shown) _HistoryTile(payment: x, onChanged: reload),
            ],
          );
        },
      ),
    );
  }
}

int _paise(String amount) {
  final parts = amount.split('.');
  final whole = int.tryParse(parts[0]) ?? 0;
  final frac = parts.length > 1 ? int.tryParse(parts[1].padRight(2, '0').substring(0, 2)) ?? 0 : 0;
  return whole * 100 + frac;
}

String _fromPaise(int paise) => '${paise ~/ 100}.${(paise % 100).toString().padLeft(2, '0')}';

class _CountCard extends StatelessWidget {
  const _CountCard({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 6),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(value, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.payment, required this.onChanged});
  final Map<String, dynamic> payment;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final p = payment;
    final types = (p['lines'] as List? ?? const [])
        .cast<Map>()
        .map((l) {
          final month = DateTime.tryParse('${l['period_month']}');
          return month == null
              ? '${l['contribution_type_name']}'
              : '${l['contribution_type_name']} (${_monthLabel(month)})';
        })
        .join(', ');
    final receipt = p['receipt'] as Map?;
    final successful = p['status'] == 'successful';
    final owing = successful && p['pavti_status'] != null && p['pavti_status'] != 'paid';
    return Card(
      child: ListTile(
        isThreeLine: true,
        title: Text(types.isEmpty ? t('contribution') : types),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${formatStamp('${p['paid_at']}')} · ${p['event_name']} · ${modeLabel(app, '${p['mode']}')}'),
            Text(
              [
                receipt?['receipt_number'],
                if (p['collector_name'] != null) t('collected_by_name', {'name': '${p['collector_name']}'}),
              ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 4),
            if (owing) PavtiChips(p) else if (!successful) StatusChip('${p['status']}'),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(formatInr('${p['amount']}'), style: Theme.of(context).textTheme.titleSmall),
            if (owing)
              Text(
                '${formatInr('${p['balance_due']}')} ${t('still_owed')}',
                style: TextStyle(color: Colors.amber.shade900, fontSize: 12),
              ),
          ],
        ),
        onTap: owing && app.can('payments.create')
            ? () async {
                final saved = await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(builder: (_) => PavtiVisitScreen(payment: p)),
                );
                if (saved == true) onChanged();
              }
            : receipt != null && app.can('receipts.view')
            ? () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${receipt['id']}')),
              )
            : null,
      ),
    );
  }
}

String _monthLabel(DateTime d) {
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return '${m[d.month - 1]} ${d.year}';
}
